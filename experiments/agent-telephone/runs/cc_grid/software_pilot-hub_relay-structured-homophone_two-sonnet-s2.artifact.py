"""Brennan Opticians appointment reminder planner (stdlib only, Python 3.12).

Run tests: python3 brennan_reminders.py   (or python3 -m unittest brennan_reminders)

Deployment: zoneinfo needs IANA data. Where the OS lacks it (slim containers,
Windows), install the `tzdata` package.

Assumptions (named constants / single-place config):
  A1 (R3)  optout_sms_v2 missing/None/non-bool => treated as opted out (no SMS); logged by id only.
  A2 (R4)  Date rendered DD/MM/YYYY, time HH:MM (24h), Europe/Dublin.
  A3 (R5)  Second reminder is SECOND_OFFSET = 2 hours before start (client message garbled).
  A4 (R9)  If moving back out of quiet hours would land before now, move forward to
           08:00 only if strictly before starts_at, else drop that reminder.
  A5 (R14) Dublin time is used for Polish customers as well.
  A6 (R19) Malformed appointments are skipped and logged by id (or position); duplicates
           ids are processed independently.
  A7 (R20) English template defined once below; same for both reminders; empty name
           => generic greeting.
  House rule vs R11: the per-reminder INFO line records appointment id, reminder kind,
  channel and the contact *kind* (phone_on_file / email_on_file), never the address,
  phone number, name or text, because R11 forbids logging customer contact data.
"""
import logging
import unicodedata
import unittest
from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)          # ASSUMPTION A3
QUIET_START_HOUR = 21                       # quiet window [21:00, 08:00)
QUIET_END_HOUR = 8
SEND_HOUR = 20                              # fallback send time
SMS_LIMIT = 160
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
DATE_FMT = "%d/%m/%Y"                       # ASSUMPTION A2
TIME_FMT = "%H:%M"
GREETING_NAMED = "Hi {name},"               # ASSUMPTION A7
GREETING_GENERIC = "Hello,"
TEMPLATE = "{greeting} a reminder of your Brennan Opticians appointment on {date} at {time}. {signature}"


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _text_ok(v):
    return isinstance(v, str) and v.strip() != ""


def _signature(country):
    pl = isinstance(country, str) and country.strip().upper() == "PL"
    return _nfc(SIGNATURE_PL if pl else SIGNATURE)


def _render(greeting, local_start, sig):
    return _nfc(TEMPLATE.format(greeting=greeting, date=local_start.strftime(DATE_FMT),
                                time=local_start.strftime(TIME_FMT), signature=sig)).rstrip()


# Template plus longest signature must fit in an SMS with no name.
assert len(TEMPLATE.format(greeting=GREETING_GENERIC, date="00/00/0000", time="00:00",
                           signature=max(_nfc(SIGNATURE), _nfc(SIGNATURE_PL), key=len))) <= SMS_LIMIT


def _build_text(channel, name, starts_utc, country):
    local = starts_utc.astimezone(DUBLIN)
    sig = _signature(country)
    full = _nfc(" ".join(name.split())) if isinstance(name, str) else ""
    if not full:
        return _render(GREETING_GENERIC, local, sig)
    candidates = [full, full.split(" ")[0], full[0]]
    if channel == "email":
        return _render(GREETING_NAMED.format(name=full), local, sig)
    for c in candidates:
        t = _render(GREETING_NAMED.format(name=c), local, sig)
        if len(t) <= SMS_LIMIT:
            return t
    return _render(GREETING_GENERIC, local, sig)


def _in_quiet(local):
    return local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR


def _adjust(t_utc, now_utc, starts_utc):
    """Apply quiet hours. Inputs/outputs are UTC datetimes; None means drop."""
    local = t_utc.astimezone(DUBLIN)
    if not _in_quiet(local):
        return t_utc
    day = timedelta(days=1)
    if local.hour >= QUIET_START_HOUR:
        back_day, fwd_day = local.date(), local.date() + day
    else:
        back_day, fwd_day = local.date() - day, local.date()
    back = datetime.combine(back_day, time(SEND_HOUR), tzinfo=DUBLIN).astimezone(UTC)
    if back >= now_utc:
        return back
    fwd = datetime.combine(fwd_day, time(QUIET_END_HOUR), tzinfo=DUBLIN).astimezone(UTC)
    return fwd if fwd < starts_utc else None


def _second_time(starts, now):          # 2h reminder (highest priority)
    p = starts - SECOND_OFFSET
    if p < now:
        return None
    return _adjust(p, now, starts)


def _first_time(starts, now):           # 48h reminder
    p = max(starts - FIRST_OFFSET, now)
    return _adjust(p, now, starts)


def _route(appt, aid):
    phone, email = appt.get("phone"), appt.get("email")
    optout = appt.get("optout_sms_v2")
    if not isinstance(optout, bool):
        log.info("appointment=%s note=optout_sms_v2_unusable treated_as_opted_out", aid)
        optout = True
    if _text_ok(phone) and optout is False:
        return "sms", "phone_on_file"
    if _text_ok(email):
        return "email", "email_on_file"
    return None, None


def _plan_one(appt, pos, now):
    aid = appt.get("id") if isinstance(appt, Mapping) else None
    label = aid if aid is not None and str(aid).strip() else f"position {pos}"
    if not isinstance(appt, Mapping):
        log.warning("skipped appointment=%s reason=malformed", label)
        return []
    starts, status = appt.get("starts_at"), appt.get("status")
    if (label != aid or not isinstance(starts, datetime) or starts.utcoffset() is None
            or not isinstance(status, str)):
        log.warning("skipped appointment=%s reason=malformed", label)
        return []
    if status.strip().lower() == "cancelled":
        log.info("skipped appointment=%s reason=cancelled", aid)
        return []
    starts = starts.astimezone(UTC)
    if now >= starts:
        log.info("skipped appointment=%s reason=already_started", aid)
        return []
    channel, contact = _route(appt, aid)
    if channel is None:
        log.info("skipped appointment=%s reason=no_usable_route", aid)
        return []
    second = _second_time(starts, now)
    first = _first_time(starts, now)
    if first is not None and first == second:
        first = None                                    # R21: 2h one wins
    text = _build_text(channel, appt.get("customer_name"), starts, appt.get("country"))
    res = []
    for kind, t in (("first", first), ("second", second)):
        if t is not None:
            log.info("planned reminder appointment=%s which=%s channel=%s contact=%s send_at=%s",
                     aid, kind, channel, contact, t.astimezone(DUBLIN).isoformat())
            res.append((t, aid, channel, text))
    return res


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for pos, appt in enumerate(appointments):
        try:
            planned.extend(_plan_one(appt, pos, now_utc))
        except Exception as exc:    # never include values or tracebacks (may hold PII)
            log.error("skipped appointment=position %s reason=error type=%s", pos, type(exc).__name__)
    planned.sort(key=lambda p: p[0])                    # stable, by instant
    return [{"appointment_id": aid, "channel": ch, "send_at": t.astimezone(DUBLIN), "text": tx}
            for t, aid, ch, tx in planned]


# ----------------------------------------------------------------- tests
def D(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=DUBLIN)


def appt(**kw):
    base = dict(id="a1", customer_name="Jane Doe", email="jane@example.com", phone="0851234567",
                country="IE", status="booked", starts_at=D(2026, 10, 20, 14, 30), optout_sms_v2=False)
    base.update(kw)
    return base


def utc(dt):
    return dt.astimezone(UTC)


class Tests(unittest.TestCase):
    def times(self, res):
        return [utc(r["send_at"]) for r in res]

    def test_basics(self):
        self.assertEqual(plan_reminders([], D(2026, 1, 1)), [])
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 1, 1))
        a = appt()
        before = repr(a)
        plan_reminders([a], D(2026, 10, 19, 10))
        self.assertEqual(repr(a), before)

    def test_second_reminder_path(self):
        res = plan_reminders([appt()], D(2026, 10, 20, 13, 30))
        self.assertEqual(self.times(res), [utc(D(2026, 10, 20, 13, 30))])

    def test_r6_example(self):
        res = plan_reminders([appt()], D(2026, 10, 19, 10))
        self.assertEqual(self.times(res), [utc(D(2026, 10, 19, 10)), utc(D(2026, 10, 20, 12, 30))])
        self.assertEqual(set(res[0]), {"appointment_id", "channel", "send_at", "text"})

    def test_r9_examples(self):
        a = appt(starts_at=D(2026, 10, 20, 9, 30))
        res = plan_reminders([a], D(2026, 10, 15, 10))
        self.assertIn(utc(D(2026, 10, 19, 20)), self.times(res))
        res = plan_reminders([a], D(2026, 10, 19, 22))
        self.assertEqual(self.times(res), [utc(D(2026, 10, 20, 8))])
        a = appt(starts_at=D(2026, 10, 20, 8))
        self.assertEqual(plan_reminders([a], D(2026, 10, 19, 22)), [])

    def test_quiet_boundaries(self):
        far, near = D(2026, 10, 1), D(2026, 11, 1)
        for (d, h, m), exp in {(10, 20, 59): D(2026, 10, 10, 20, 59), (10, 21, 0): D(2026, 10, 10, 20),
                               (11, 7, 59): D(2026, 10, 10, 20), (11, 8, 0): D(2026, 10, 11, 8)}.items():
            r = _adjust(utc(D(2026, 10, d, h, m)), utc(far), utc(near))
            self.assertEqual(r, utc(exp))

    def test_dst(self):
        res = plan_reminders([appt(starts_at=D(2026, 10, 26, 10))], D(2026, 10, 1))
        self.assertEqual(utc(res[0]["send_at"]), datetime(2026, 10, 24, 10, tzinfo=UTC))
        self.assertEqual(res[0]["send_at"].hour, 11)
        self.assertIn("10:00", res[0]["text"])
        res = plan_reminders([appt(starts_at=D(2027, 3, 28, 12))], D(2027, 3, 1))
        self.assertEqual(utc(res[0]["send_at"]), datetime(2027, 3, 26, 11, tzinfo=UTC))
        self.assertIn("12:00", res[0]["text"])

    def test_text_date_time(self):
        a = appt(starts_at=datetime(2026, 7, 1, 8, tzinfo=UTC))
        t = plan_reminders([a], D(2026, 6, 1))[0]["text"]
        self.assertIn("01/07/2026", t)
        self.assertIn("09:00", t)

    def test_channels(self):
        now = D(2026, 10, 19, 10)
        cases = [(appt(), "sms"), (appt(optout_sms_v2=True), "email"), (appt(phone="  "), "email"),
                 (appt(optout_sms_v2=None), "email"), (appt(optout_sms_v2="false"), "email"),
                 (appt(opt_out=True), "sms")]
        for a, ch in cases:
            self.assertEqual({r["channel"] for r in plan_reminders([a], now)}, {ch})
        self.assertEqual(plan_reminders([appt(optout_sms_v2=True, email=" ")], now), [])
        self.assertEqual(plan_reminders([appt(phone=None, email=None)], now), [])

    def test_status_and_past(self):
        now = D(2026, 10, 19, 10)
        self.assertEqual(plan_reminders([appt(status=" Cancelled ")], now), [])
        self.assertEqual(plan_reminders([appt()], D(2026, 10, 20, 14, 30)), [])

    def test_signature_and_length(self):
        now = D(2026, 10, 19, 10)
        self.assertTrue(plan_reminders([appt()], now)[0]["text"].endswith("Siobhán Ní Dhuibhir"))
        t = plan_reminders([appt(country=" pl ")], now)[0]["text"]
        self.assertTrue(t.endswith("Grzegorz Szczepański"))
        self.assertEqual(t, unicodedata.normalize("NFC", t))
        long_name = "Alexandria " + "Z" * 200
        t = plan_reminders([appt(customer_name=long_name)], now)[0]["text"]
        self.assertLessEqual(len(t), 160)
        self.assertIn("Hi Alexandria,", t)
        t = plan_reminders([appt(customer_name="A" * 300 + " B", country="PL")], now)[0]["text"]
        self.assertLessEqual(len(t), 160)
        self.assertTrue(t.startswith("Hello,"))
        t = plan_reminders([appt(customer_name="  Jane \n  Doe ")], now)[0]["text"]
        self.assertIn("Hi Jane Doe,", t)
        t = plan_reminders([appt(customer_name=None, phone=None)], now)[0]["text"]
        self.assertTrue(t.startswith("Hello,"))
        t = plan_reminders([appt(customer_name="A" * 300, phone=None)], now)[0]["text"]
        self.assertGreater(len(t), 160)

    def test_order_and_duplicates(self):
        now = D(2026, 10, 19, 10)
        a = appt(id="z", starts_at=D(2026, 10, 20, 14, 30))
        b = appt(id="a", starts_at=D(2026, 10, 20, 11, 30))
        res = plan_reminders([a, b, dict(a)], now)
        ts = self.times(res)
        self.assertEqual(ts, sorted(ts))
        self.assertEqual([r["appointment_id"] for r in res][:3], ["z", "a", "z"])
        self.assertEqual(len(res), 6)

    def test_malformed_skipped(self):
        bad = [{"status": "booked", "starts_at": D(2026, 10, 20, 14)}, appt(id="n", starts_at=datetime(2026, 10, 20, 14)),
               appt(id="s", status=None), "junk", appt(id="ok")]
        res = plan_reminders(bad, D(2026, 10, 19, 10))
        self.assertEqual({r["appointment_id"] for r in res}, {"ok"})

    def test_no_email_in_logs(self):
        s = "sentinel-xyz@secret.example"
        now = D(2026, 10, 19, 10)
        batch = [appt(id="1", email=s, optout_sms_v2=True), appt(id="2", email=s, status="cancelled"),
                 appt(id="3", email=s, starts_at=datetime(2026, 10, 20, 14)),
                 appt(id="4", email=s, customer_name=object()), appt(id="5", email=s, phone=None, optout_sms_v2=None),
                 appt(id="6", email=s, starts_at=D(2026, 10, 1))]
        with self.assertLogs(level="DEBUG") as cm:
            res = plan_reminders(batch, now)
        blob = "\n".join(r.getMessage() + str(r.exc_text) + str(r.args) for r in cm.records)
        self.assertNotIn(s, blob)
        self.assertNotIn(s, repr(res))
        self.assertIn("channel=email", blob)

    def test_properties(self):
        step = timedelta(minutes=90)
        for pl in (False, True):
            for i in range(60):
                starts = D(2026, 10, 24, 0) + i * step
                for j in range(0, 130, 3):
                    now = starts - timedelta(minutes=97 * j + 5) + timedelta(minutes=17)
                    now = now.astimezone(UTC)
                    res = plan_reminders([appt(starts_at=starts, country="PL" if pl else "IE")], now)
                    self.assertLessEqual(len(res), 2)
                    for r in res:
                        t = utc(r["send_at"])
                        self.assertGreaterEqual(t, now)
                        self.assertLess(t, utc(starts))
                        self.assertFalse(_in_quiet(t.astimezone(DUBLIN)))
                        self.assertIn(r["channel"], ("sms", "email"))
                        self.assertIn(starts.astimezone(DUBLIN).strftime("%d/%m/%Y"), r["text"])
                        self.assertIn(starts.astimezone(DUBLIN).strftime("%H:%M"), r["text"])
                        self.assertTrue(r["text"].endswith("Grzegorz Szczepański" if pl else "Siobhán Ní Dhuibhir"))
                        self.assertLessEqual(len(r["text"]), 160)
                    self.assertEqual(len({utc(r["send_at"]) for r in res}), len(res))
                self.assertEqual(plan_reminders([appt(starts_at=starts)], starts), [])


if __name__ == "__main__":
    unittest.main()