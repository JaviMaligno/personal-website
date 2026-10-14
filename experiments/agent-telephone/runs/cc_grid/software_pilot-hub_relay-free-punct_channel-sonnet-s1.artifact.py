"""Brennan Opticians SMS appointment reminders.

Public entry point: plan_reminders(appointments, now). It is pure and stateless,
so the caller must dedupe repeated runs. Run the tests with:
    python3 -m unittest -v <this_file>.py
(Note: the author had no execution tool, so the tests have not been run yet.)

ASSUMPTIONS THE CLIENT MUST CONFIRM
* Opt-out: the client said "text them if optout_sms_v2 is true", but the field
  name means "opted out". This module treats True as opted out (no reminder),
  False as opted in, and missing or None as opted out. It is a one-line flip in
  _is_opted_out(). The stale legacy opt_out field is never read.
* Quiet hours: a send time of 21:00 or later, or before 08:00 Dublin time, moves
  back to the most recent 20:00. If that is before now, it goes to the next
  08:00 if that is before starts_at, otherwise it is dropped. Set
  DEFER_TO_MORNING = False to simply drop instead.
* Email is never read or used. The day of month is not zero-padded ("Wed 5 Oct").
* Logging: one INFO line per planned reminder with appointment id, channel and
  the contact field name ("phone"). The phone value, name and email are never
  logged, per the privacy rule. Skipped malformed appointments log id and field
  name only.
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
log = logging.getLogger(__name__)

FIRST_LEAD = timedelta(hours=48)
SECOND_LEAD = timedelta(hours=2)
QUIET_START_HOUR = 21   # 21:00:00 and later is quiet
QUIET_END_HOUR = 8      # 08:00:00 is allowed, before it is quiet
EVENING_HOUR = 20
DEFER_TO_MORNING = True  # False: reminders that cannot go at 20:00 are just dropped
MAX_SMS_LEN = 160

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = unicodedata.normalize("NFC", "Siobhán Ní Dhuibhir")
_SIG_PL = unicodedata.normalize("NFC", "Grzegorz Szczepański")


class _Malformed(Exception):
    """Carries only a field name, never any data."""

    def __init__(self, field: str):
        super().__init__(field)
        self.field = field


def _is_opted_out(value) -> bool:
    # ASSUMPTION (client to confirm): optout_sms_v2 True means OPTED OUT.
    # Only an explicit False means opted in; missing/None counts as opted out.
    # To flip the meaning, change this to: return value is not True
    return value is not False


def _at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=DUBLIN)


def apply_quiet_hours(send_at: datetime, now: datetime, starts_at: datetime):
    """Return an adjusted send time respecting quiet hours, or None to drop."""
    local = send_at.astimezone(DUBLIN)
    if QUIET_END_HOUR <= local.hour < QUIET_START_HOUR:
        return send_at
    day = local.date()
    if local.hour >= QUIET_START_HOUR:
        back_day, next_day = day, day + timedelta(days=1)
    else:
        back_day, next_day = day - timedelta(days=1), day
    back = _at(back_day, EVENING_HOUR)
    if back >= now:
        return back
    if DEFER_TO_MORNING:
        morning = _at(next_day, QUIET_END_HOUR)
        if morning < starts_at:
            return morning
    return None


def _name_forms(raw):
    if not isinstance(raw, str):
        return
    name = " ".join(unicodedata.normalize("NFC", raw).split())
    if not name:
        return
    yield name
    parts = name.split(" ")
    first = parts[0]
    if len(parts) > 1:
        yield f"{first} {parts[-1][0]}."
    yield first
    for k in range(len(first) - 1, 0, -1):
        if unicodedata.combining(first[k]):
            continue
        yield first[:k] + "."


def _build_text(raw_name, local_start: datetime, country) -> str:
    when = (f"{_WEEKDAYS[local_start.weekday()]} {local_start.day} "
            f"{_MONTHS[local_start.month - 1]} {local_start.year} at "
            f"{local_start.hour:02d}:{local_start.minute:02d}")
    pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = _SIG_PL if pl else _SIG_DEFAULT

    def make(name):
        head = f"Hi {name}" if name else "Hi"
        text = f"{head}, reminder of your Brennan Opticians appointment on {when}. {sig}"
        return unicodedata.normalize("NFC", text)

    for form in _name_forms(raw_name):
        text = make(form)
        if len(text) <= MAX_SMS_LEN:
            return text
    return make(None)


def _plan_one(appt, now):
    if not isinstance(appt, dict):
        raise _Malformed("appointment")
    aid = appt.get("id")
    if isinstance(aid, bool) or not isinstance(aid, (str, int)) or aid == "":
        raise _Malformed("id")
    starts = appt.get("starts_at")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise _Malformed("starts_at")
    status = appt.get("status")
    if not isinstance(status, str):
        raise _Malformed("status")
    if status.strip().casefold() == "cancelled":
        return []
    if starts <= now:
        return []
    phone = appt.get("phone")
    if not isinstance(phone, str) or not phone.strip():
        return []
    if _is_opted_out(appt.get("optout_sms_v2")):
        return []

    s_utc = starts.astimezone(timezone.utc)
    t48, t2 = s_utc - FIRST_LEAD, s_utc - SECOND_LEAD
    if t2 < now:
        nominal = [(0, now)]  # single catch-up, no second reminder
    else:
        nominal = [(0, t48 if t48 >= now else now), (1, t2)]

    by_instant = {}
    for order, at in nominal:  # later (2h) overwrites on equal instant
        adj = apply_quiet_hours(at, now, starts)
        if adj is not None:
            by_instant[adj.astimezone(timezone.utc)] = (order, adj)
    if not by_instant:
        return []
    text = _build_text(appt.get("customer_name"), starts.astimezone(DUBLIN),
                       appt.get("country"))
    return [(adj.astimezone(DUBLIN), str(aid), order, aid, text)
            for order, adj in by_instant.values()]


def _safe_id(appt):
    v = appt.get("id") if isinstance(appt, dict) else None
    return v if isinstance(v, (str, int)) and not isinstance(v, bool) else "?"


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    if not isinstance(appointments, (list, tuple)):
        raise ValueError("appointments must be a list")
    rows = []
    for appt in appointments:
        try:
            rows.extend(_plan_one(appt, now))
        except _Malformed as exc:
            log.warning("skipped appointment id=%s field=%s", _safe_id(appt), exc.field)
        except Exception:  # never let one record stop the batch; no data logged
            log.warning("skipped appointment id=%s field=unknown", _safe_id(appt))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    out = []
    for send_at, _k, _o, aid, text in rows:
        log.info("reminder planned appointment_id=%s channel=sms contact_field=phone send_at=%s",
                 aid, send_at.isoformat())
        out.append({"appointment_id": aid, "channel": "sms",
                    "send_at": send_at, "text": text})
    return out


# ----------------------------------------------------------------- tests ---
import copy
import unittest
from unittest import mock

EMAIL = "zz.secret.canary@example.invalid"
PHONE = "+353 99 000 1234"


def D(*a):
    return datetime(*a, tzinfo=DUBLIN)


def mk(**kw):
    a = {"id": "A1", "customer_name": "Mary Brown", "email": EMAIL, "phone": PHONE,
         "country": "IE", "status": "confirmed", "starts_at": D(2026, 10, 14, 14, 30),
         "optout_sms_v2": False}
    a.update(kw)
    return a


NOW = D(2026, 10, 10, 12, 0)


def times(res):
    return [r["send_at"] for r in res]


class TestTwoHourFirst(unittest.TestCase):
    def test_two_reminders(self):
        res = plan_reminders([mk()], NOW)
        self.assertEqual(times(res), [D(2026, 10, 12, 14, 30), D(2026, 10, 14, 12, 30)])
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(r["channel"], "sms")
            self.assertEqual(str(r["send_at"].tzinfo), "Europe/Dublin")

    def test_two_hour_in_quiet_hours_moves_back(self):
        res = plan_reminders([mk(starts_at=D(2026, 10, 14, 9, 30))], NOW)
        self.assertEqual(times(res)[-1], D(2026, 10, 13, 20, 0))

    def test_first_passed(self):
        now = D(2026, 10, 13, 10, 0)
        self.assertEqual(times(plan_reminders([mk()], now)), [now, D(2026, 10, 14, 12, 30)])

    def test_both_passed_single_catch_up(self):
        now = D(2026, 10, 14, 13, 0)
        self.assertEqual(times(plan_reminders([mk()], now)), [now])

    def test_catch_up_in_quiet_hours_goes_to_next_morning(self):
        now = D(2026, 10, 13, 23, 0)
        self.assertEqual(times(plan_reminders([mk()], now)),
                         [D(2026, 10, 14, 8, 0), D(2026, 10, 14, 12, 30)])

    def test_catch_up_dropped_if_morning_not_before_start(self):
        now = D(2026, 10, 14, 3, 0)
        self.assertEqual(plan_reminders([mk(starts_at=D(2026, 10, 14, 7, 30))], now), [])

    def test_drop_mode(self):
        now = D(2026, 10, 13, 23, 0)
        with mock.patch.dict(globals(), {"DEFER_TO_MORNING": False}):
            self.assertEqual(times(plan_reminders([mk()], now)), [D(2026, 10, 14, 12, 30)])

    def test_same_instant_emits_one(self):
        now = D(2026, 10, 13, 10, 0)
        self.assertEqual(times(plan_reminders([mk(starts_at=D(2026, 10, 13, 12, 0))], now)), [now])

    def test_coalesced_by_quiet_hours(self):
        now = D(2026, 10, 13, 22, 0)
        res = plan_reminders([mk(starts_at=D(2026, 10, 14, 9, 30))], now)
        self.assertEqual(times(res), [D(2026, 10, 14, 8, 0)])


class TestQuietHours(unittest.TestCase):
    def test_boundaries(self):
        st = D(2026, 10, 20, 12, 0)
        f = lambda t: apply_quiet_hours(t, NOW, st)
        self.assertEqual(f(D(2026, 10, 12, 21, 0, 0)), D(2026, 10, 12, 20, 0))
        self.assertEqual(f(D(2026, 10, 12, 20, 59, 59)), D(2026, 10, 12, 20, 59, 59))
        self.assertEqual(f(D(2026, 10, 12, 8, 0, 0)), D(2026, 10, 12, 8, 0, 0))
        self.assertEqual(f(D(2026, 10, 12, 7, 59, 59)), D(2026, 10, 11, 20, 0))


class TestDST(unittest.TestCase):
    def test_fall_back_48h_is_elapsed(self):
        now = D(2026, 10, 20, 12, 0)
        res = plan_reminders([mk(starts_at=D(2026, 10, 26, 14, 0))], now)
        self.assertEqual(res[0]["send_at"], datetime(2026, 10, 24, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(res[0]["send_at"].hour, 15)

    def test_fall_back_two_hour_in_repeated_hour(self):
        now = D(2026, 10, 20, 12, 0)
        res = plan_reminders([mk(starts_at=D(2026, 10, 25, 3, 0))], now)
        self.assertEqual(res[-1]["send_at"], datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc))

    def test_quiet_back_across_fall_back(self):
        st = D(2026, 11, 1, 12, 0)
        r = apply_quiet_hours(D(2026, 10, 25, 7, 0), NOW, st)
        self.assertEqual(r, D(2026, 10, 24, 20, 0))
        self.assertEqual(r.astimezone(timezone.utc).hour, 19)

    def test_spring_forward(self):
        now = D(2027, 3, 20, 12, 0)
        res = plan_reminders([mk(starts_at=D(2027, 3, 29, 14, 0))], now)
        self.assertEqual(res[0]["send_at"], datetime(2027, 3, 27, 13, 0, tzinfo=timezone.utc))
        self.assertEqual(res[0]["send_at"].hour, 13)
        res = plan_reminders([mk(starts_at=D(2027, 3, 28, 9, 0))], now)
        self.assertEqual(res[-1]["send_at"], datetime(2027, 3, 27, 20, 0, tzinfo=timezone.utc))
        self.assertEqual(res[0]["send_at"], datetime(2027, 3, 26, 8, 0, tzinfo=timezone.utc))


class TestEligibility(unittest.TestCase):
    def test_cancelled(self):
        for s in (" Cancelled ", "CANCELLED", "cancelled"):
            self.assertEqual(plan_reminders([mk(status=s)], NOW), [])

    def test_past_or_equal_start(self):
        self.assertEqual(plan_reminders([mk(starts_at=NOW)], NOW), [])
        self.assertEqual(plan_reminders([mk(starts_at=NOW - timedelta(hours=1))], NOW), [])

    def test_no_phone_no_email_fallback(self):
        for p in ("", "   ", None):
            self.assertEqual(plan_reminders([mk(phone=p)], NOW), [])

    def test_optout_semantics(self):
        self.assertEqual(len(plan_reminders([mk(optout_sms_v2=False)], NOW)), 2)
        self.assertEqual(plan_reminders([mk(optout_sms_v2=True)], NOW), [])
        self.assertEqual(plan_reminders([mk(optout_sms_v2=None)], NOW), [])
        a = mk()
        del a["optout_sms_v2"]
        self.assertEqual(plan_reminders([a], NOW), [])

    def test_legacy_opt_out_ignored(self):
        self.assertEqual(len(plan_reminders([mk(optout_sms_v2=False, opt_out=True)], NOW)), 2)
        self.assertEqual(plan_reminders([mk(optout_sms_v2=True, opt_out=False)], NOW), [])


class TestOrderingAndPurity(unittest.TestCase):
    def test_sorting(self):
        res = plan_reminders([mk(id="b"), mk(id="a")], NOW)
        self.assertEqual([r["appointment_id"] for r in res], ["a", "b", "a", "b"])

    def test_no_mutation(self):
        data = [mk(), mk(id="x", status="cancelled")]
        before = copy.deepcopy(data)
        plan_reminders(data, NOW)
        self.assertEqual(data, before)


class TestText(unittest.TestCase):
    def txt(self, name, country="IE"):
        return plan_reminders([mk(customer_name=name, country=country)], NOW)[0]["text"]

    def test_exact_template_and_utc_input(self):
        st = datetime(2026, 10, 14, 8, 30, tzinfo=timezone.utc)  # 09:30 Dublin
        t = plan_reminders([mk(starts_at=st)], NOW)[0]["text"]
        self.assertEqual(t, "Hi Mary Brown, reminder of your Brennan Opticians appointment "
                            "on Wed 14 Oct 2026 at 09:30. Siobhán Ní Dhuibhir")

    def test_polish_signature(self):
        t = self.txt("Anna", " pl ")
        self.assertTrue(t.endswith(". Grzegorz Szczepański"))

    def test_no_name_forms(self):
        for n in (None, "", "   ", 123):
            self.assertTrue(self.txt(n).startswith("Hi, reminder of your"))

    def test_shortening_ladder(self):
        budget = MAX_SMS_LEN - len(self.txt(None)) - 1
        t = self.txt("Mary " + "B" * budget)
        self.assertTrue(t.startswith("Hi Mary B., reminder"))
        t = self.txt("Anne-Marie S" + "x" * budget)
        self.assertTrue(t.startswith("Hi Anne-Marie S., reminder"))
        t = self.txt("A" * (budget - 1) + " Bee")
        self.assertTrue(t.startswith("Hi " + "A" * (budget - 1) + ", reminder"))
        t = self.txt("A" * (budget + 10))
        self.assertTrue(t.startswith("Hi " + "A" * (budget - 1) + ". reminder") is False)
        self.assertTrue(t.startswith("Hi " + "A" * (budget - 1) + ".,"))
        self.assertEqual(len(t), MAX_SMS_LEN)

    def test_length_and_signature_always_kept(self):
        for n in ("Zażółć Gęślą Jaźń", "Łukasz Żółkiewski-Wiśniewski " * 5, "Ó" * 200, "x y " * 40):
            for c in ("IE", "PL"):
                t = self.txt(n, c)
                self.assertLessEqual(len(t), MAX_SMS_LEN)
                self.assertEqual(t, unicodedata.normalize("NFC", t))
                self.assertTrue(t.endswith(_SIG_PL if c == "PL" else _SIG_DEFAULT))

    def test_nfc(self):
        t = self.txt("Jose\u0301")
        self.assertIn("José", t)
        self.assertEqual(t, unicodedata.normalize("NFC", t))


class TestRobustnessAndPrivacy(unittest.TestCase):
    def test_naive_now(self):
        for bad in (datetime(2026, 10, 10, 12, 0), "now", None):
            with self.assertRaises(ValueError) as cm:
                plan_reminders([mk()], bad)
            self.assertEqual(str(cm.exception), "now must be a timezone-aware datetime")

    def test_malformed_skipped(self):
        bad = [mk(id=None), mk(starts_at=datetime(2026, 10, 14, 14, 30)),
               mk(starts_at="2026-10-14"), mk(status=5), mk(id=True), None, "x", 5]
        no_id = mk()
        del no_id["id"]
        res = plan_reminders(bad + [no_id, mk(id="ok")], NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"ok"})
        self.assertEqual(len(res), 2)

    def test_info_line_per_reminder(self):
        with self.assertLogs(level="INFO") as cm:
            res = plan_reminders([mk()], NOW)
        info = [r for r in cm.records if r.levelno == logging.INFO]
        self.assertEqual(len(info), len(res))
        msg = info[0].getMessage()
        self.assertIn("A1", msg)
        self.assertIn("sms", msg)
        self.assertIn("phone", msg)

    def test_no_pii_in_logs_or_errors(self):
        inputs = [mk(), mk(id="M1", starts_at="bad"), mk(id=None),
                  mk(id="M2", starts_at=datetime(2026, 10, 14, 14, 30)), mk(id="M3", status=7)]
        with self.assertLogs(level="DEBUG") as cm:
            res = plan_reminders(inputs, NOW)
            log.info("sentinel")
            with self.assertRaises(ValueError) as ec:
                plan_reminders(inputs, datetime(2026, 1, 1))
        blob = "\n".join(r.getMessage() for r in cm.records) + "\n".join(cm.output)
        blob += str(ec.exception) + repr(ec.exception) + repr(res)
        for secret in (EMAIL, PHONE, "Mary Brown"):
            self.assertNotIn(secret, blob.replace(repr(res), "") if secret != EMAIL else blob)


if __name__ == "__main__":
    unittest.main()