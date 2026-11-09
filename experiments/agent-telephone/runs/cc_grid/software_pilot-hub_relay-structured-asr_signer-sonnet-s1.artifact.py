"""Brennan Opticians appointment reminder planner (stdlib only, Python 3.9+).

Entry point: plan_reminders(appointments, now) -> list of dicts with exactly the
keys appointment_id, channel ("sms" / "email"), send_at, text.

The function is pure and stateless: it reads no clock, does not mutate its
inputs, and remembers nothing between calls. The CALLER MUST DE-DUPLICATE
(e.g. do not re-send a reminder that was already sent on a previous run).
There is deliberately no "kind" field in the output.

Appointment fields (mappings): id, customer_name, email, phone, country,
status, starts_at (tz-aware), optout_sms_v2. Only optout_sms_v2 is read for
SMS opt-out; the legacy "opt_out" key is never read.

Planning rules, per active appointment and slot (2h is built first, then 48h):
  1. starts_at <= now: no reminders.
  2. t = starts_at - offset (UTC arithmetic); if t < now, t = now.
  3. If t is in quiet hours (21:00:00 to 07:59:59 local), move back to the
     preceding 20:00 local.
  4. If that is < now, move FORWARD to the next 08:00 local instead.
  5. If the final send_at >= starts_at, drop it.
  6. If the 48h send_at >= the 2h send_at, drop the 48h one.
Known loss: an appointment at 07:00 booked the evening before may lose its 2h
reminder (and the 48h one if it too would land after the start).
Output is sorted by send_at, then appointment_id (as str), then 48h before 2h.

Channel: SMS if phone is non-blank and optout_sms_v2 is exactly False;
otherwise email if email is non-blank; otherwise no reminder (logged by id and
reason code). Never both channels for one reminder. Opt-out never blocks email.

Text: "Hi <name>, your Brennan Opticians appointment is on Thu 15 Oct 2026 at
14:30. <signature>". Signature is "Chevonne Nee Divver", or "Grzegorz
Szczepański" when country is PL. SMS is capped at 160 characters including the
signature; the name is shortened (full, first, truncated first with ".",
initial, none), never the date/time. Email is never shortened. Note: the "ń"
in the PL signature makes an SMS Unicode (UCS-2), so carriers bill it in 70
character segments rather than 160; the 160 limit here counts characters as
specified.

Logging: one INFO line per planned reminder with appointment_id, slot, channel
and contact_field ("phone" or "email"). Deviation from the house rule, which
asks for the contact: customer requirement R10 forbids logging email, phone or
name, so the contact VALUE is never logged; support can trace it by
appointment_id. Skips log only appointment_id (or index) and a reason code.

[CONFIRM] defaults (all module constants, easy to change):
  OUTPUT_TZ_NAME = "Europe/Dublin"   send_at is expressed in this zone
  DEFAULT_TZ_NAME = "Europe/Dublin"  business-rule zone for everyone
  COUNTRY_TZ = {}                    per-country override, e.g. {"PL": "Europe/Warsaw"}
  Missing/None optout_sms_v2 is treated as opted out (no SMS).
  Quiet hours 21:00-08:00, back-off to 20:00, forward to 08:00.
  Date format "Thu 15 Oct 2026" in English for all; day not zero-padded.
  Step 4 moves forward to 08:00 when the back-off would be in the past.

Run tests: python -m unittest <this_file>
"""
import logging
import unicodedata
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("brennan.reminders")

OUTPUT_TZ_NAME = "Europe/Dublin"
DEFAULT_TZ_NAME = "Europe/Dublin"
COUNTRY_TZ = {}
OPTOUT_FIELD = "optout_sms_v2"
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
QUIET_BACKOFF_HOUR = 20
SMS_LIMIT = 160
SLOTS = (("2h", timedelta(hours=2)), ("48h", timedelta(hours=48)))  # 2h first
SLOT_ORDER = {"48h": 0, "2h": 1}
DEFAULT_SIGNATURE = "Chevonne Nee Divver"
SIGNATURES = {"PL": "Grzegorz Szczepański"}
CANCELLED = "cancelled"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
UTC = timezone.utc


def _country(a):
    c = a.get("country")
    return c.strip().upper() if isinstance(c, str) else ""


def _tz_for(country):
    return ZoneInfo(COUNTRY_TZ.get(country, DEFAULT_TZ_NAME))


def _at(tz, day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=tz).astimezone(UTC)


def _adjust(t, now, tz):
    """Steps 3 and 4: quiet-hours handling (all datetimes aware)."""
    loc = t.astimezone(tz)
    if QUIET_END_HOUR <= loc.hour < QUIET_START_HOUR:
        return t
    d = loc.date()
    one = timedelta(days=1)
    if loc.hour >= QUIET_START_HOUR:
        back, fwd = _at(tz, d, QUIET_BACKOFF_HOUR), _at(tz, d + one, QUIET_END_HOUR)
    else:
        back, fwd = _at(tz, d - one, QUIET_BACKOFF_HOUR), _at(tz, d, QUIET_END_HOUR)
    return back if back >= now else fwd


def _clean_name(v):
    if not isinstance(v, str):
        return ""
    return unicodedata.normalize("NFC", " ".join(v.split()))


def _compose(name, when, sig):
    date = "%s %d %s %d" % (WEEKDAYS[when.weekday()], when.day,
                            MONTHS[when.month - 1], when.year)
    greet = "Hi %s, your" % name if name else "Your"
    return "%s Brennan Opticians appointment is on %s at %02d:%02d. %s" % (
        greet, date, when.hour, when.minute, sig)


def _name_ladder(name):
    if not name:
        return
    yield name
    first = name.split(" ")[0]
    yield first
    for k in range(len(first) - 1, 1, -1):
        yield first[:k] + "."
    yield first[0] + "."


def _build_text(channel, name, when, sig):
    name = _clean_name(name)
    if channel == "email":
        return _compose(name, when, sig).rstrip()
    for cand in _name_ladder(name):
        text = _compose(cand, when, sig).rstrip()
        if len(text) <= SMS_LIMIT:
            return text
    return _compose("", when, sig).rstrip()


def _ref(a, index):
    if isinstance(a, Mapping):
        i = a.get("id")
        if i is not None and i != "":
            return "appointment_id=%s" % (i,)
    return "index=%d" % index


def _nonblank(v):
    return isinstance(v, str) and bool(v.strip())


def _plan_one(a, index, now):
    ref = _ref(a, index)
    if not isinstance(a, Mapping) or a.get("id") in (None, ""):
        logger.warning("skipped %s reason=malformed_missing_id", ref)
        return []
    starts = a.get("starts_at")
    if (not isinstance(starts, datetime) or starts.tzinfo is None
            or starts.utcoffset() is None):
        logger.warning("skipped %s reason=malformed_starts_at", ref)
        return []
    status = a.get("status")
    if status is not None and str(status).strip().casefold() == CANCELLED:
        logger.info("skipped %s reason=cancelled", ref)
        return []
    starts_utc = starts.astimezone(UTC)
    if starts_utc <= now:
        logger.info("skipped %s reason=already_started", ref)
        return []
    if _nonblank(a.get("phone")) and a.get(OPTOUT_FIELD) is False:
        channel, field = "sms", "phone"
    elif _nonblank(a.get("email")):
        channel, field = "email", "email"
    else:
        logger.info("skipped %s reason=no_channel", ref)
        return []
    country = _country(a)
    tz = _tz_for(country)
    sig = SIGNATURES.get(country, DEFAULT_SIGNATURE)
    text = _build_text(channel, a.get("customer_name"), starts_utc.astimezone(tz), sig)

    sends = {}
    for slot, offset in SLOTS:
        t = max(starts_utc - offset, now)
        t = _adjust(t, now, tz)
        if t < starts_utc:
            sends[slot] = t
    if "48h" in sends and "2h" in sends and sends["48h"] >= sends["2h"]:
        del sends["48h"]
    if not sends:
        logger.info("skipped %s reason=no_valid_send_time", ref)
    return [(t, str(a["id"]), SLOT_ORDER[s], a["id"], s, channel, field, text)
            for s, t in sends.items()]


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for index, a in enumerate(appointments or ()):
        try:
            planned.extend(_plan_one(a, index, now_utc))
        except Exception:  # never fail the batch; no details (may hold PII)
            logger.warning("skipped %s reason=unexpected_error", _ref(a, index))
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    out_tz = ZoneInfo(OUTPUT_TZ_NAME)
    result = []
    for t, _, _, appt_id, slot, channel, field, text in planned:
        send_at = t.astimezone(out_tz)
        logger.info("reminder planned appointment_id=%s slot=%s channel=%s "
                    "contact_field=%s send_at=%s",
                    appt_id, slot, channel, field, send_at.isoformat())
        result.append({"appointment_id": appt_id, "channel": channel,
                       "send_at": send_at, "text": text})
    return result


# ----------------------------------------------------------------- tests ---
import copy
import unittest
from unittest import mock

DUB = ZoneInfo("Europe/Dublin")


def _ap(**kw):
    base = dict(id="a1", customer_name="Mary Murphy", email="mary@example.com",
                phone="+353851234567", country="IE", status="confirmed",
                starts_at=datetime(2026, 10, 15, 14, 30, tzinfo=DUB),
                optout_sms_v2=False)
    base.update(kw)
    return base


class _NoLegacy(dict):
    def get(self, k, d=None):
        assert k != "opt_out", "legacy opt_out must never be read"
        return super().get(k, d)

    def __getitem__(self, k):
        assert k != "opt_out"
        return super().__getitem__(k)


class PlannerTests(unittest.TestCase):
    NOW = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    def test_two_hour_reminder_and_text(self):
        r = plan_reminders([_ap()], self.NOW)
        s = _ap()["starts_at"]
        self.assertEqual(len(r), 2)
        self.assertEqual(set(r[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertEqual(r[1]["send_at"], s - timedelta(hours=2))
        self.assertEqual(r[0]["send_at"], s.astimezone(UTC) - timedelta(hours=48))
        self.assertEqual(r[1]["text"],
                         "Hi Mary Murphy, your Brennan Opticians appointment is on "
                         "Thu 15 Oct 2026 at 14:30. Chevonne Nee Divver")
        self.assertEqual(r[1]["send_at"].tzinfo, DUB)

    def test_naive_now(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 1, 1))

    def test_no_mutation(self):
        a = [_ap()]
        b = copy.deepcopy(a)
        plan_reminders(a, self.NOW)
        self.assertEqual(a, b)

    def test_malformed_skipped_batch_continues(self):
        bad = [_ap(id=None), _ap(starts_at=None), _ap(starts_at=datetime(2026, 10, 15, 14)),
               "junk", _ap(id="ok")]
        r = plan_reminders(bad, self.NOW)
        self.assertEqual({x["appointment_id"] for x in r}, {"ok"})

    def test_optout_both_directions(self):
        self.assertEqual(plan_reminders([_NoLegacy(_ap(optout_sms_v2=False, opt_out=True))],
                                        self.NOW)[0]["channel"], "sms")
        for v in (True, None):
            self.assertEqual(plan_reminders([_ap(optout_sms_v2=v)], self.NOW)[0]["channel"], "email")
        a = _ap(opt_out=False)
        del a["optout_sms_v2"]
        self.assertEqual(plan_reminders([a], self.NOW)[0]["channel"], "email")

    def test_channel_table(self):
        self.assertEqual(plan_reminders([_ap(optout_sms_v2=True)], self.NOW)[0]["channel"], "email")
        self.assertEqual(plan_reminders([_ap(phone="  ")], self.NOW)[0]["channel"], "email")
        self.assertEqual(plan_reminders([_ap(phone=None, optout_sms_v2=None, email=None)], self.NOW), [])
        self.assertEqual(plan_reminders([_ap(optout_sms_v2=True, email=" ")], self.NOW), [])

    def test_cancelled(self):
        self.assertEqual(plan_reminders([_ap(status="  CancelLed ")], self.NOW), [])
        self.assertTrue(plan_reminders([_ap(status="rescheduled")], self.NOW))

    def test_started_appointment(self):
        s = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
        self.assertEqual(plan_reminders([_ap(starts_at=s)], self.NOW), [])
        self.assertEqual(plan_reminders([_ap(starts_at=self.NOW)], self.NOW), [])

    def test_30h_away(self):
        now = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)
        s = now + timedelta(hours=30)
        r = plan_reminders([_ap(starts_at=s)], now)
        self.assertEqual([x["send_at"] for x in r], [now, s - timedelta(hours=2)])

    def test_one_hour_away_single(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
        r = plan_reminders([_ap(starts_at=now + timedelta(hours=1))], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], now)

    def test_evening_now_forward_to_morning(self):
        now = datetime(2026, 10, 13, 22, 0, tzinfo=UTC)  # 23:00 Dublin
        s = datetime(2026, 10, 14, 15, 0, tzinfo=DUB)
        r = plan_reminders([_ap(starts_at=s)], now)
        self.assertEqual([x["send_at"].hour for x in r], [8, 13])

    def test_early_appointment_loses_2h(self):
        s = datetime(2026, 10, 14, 7, 0, tzinfo=DUB)
        now = datetime(2026, 10, 13, 19, 30, tzinfo=UTC)  # 20:30 Dublin
        r = plan_reminders([_ap(starts_at=s)], now)
        self.assertEqual([x["send_at"] for x in r], [now])
        now2 = datetime(2026, 10, 13, 21, 0, tzinfo=UTC)  # 22:00 Dublin
        self.assertEqual(plan_reminders([_ap(starts_at=s)], now2), [])

    def test_quiet_boundaries(self):
        now = datetime(2026, 12, 1, tzinfo=UTC)
        f = lambda h, m=0, s=0, d=10: _adjust(datetime(2026, 12, d, h, m, s, tzinfo=UTC), now, DUB)
        self.assertEqual(f(21), datetime(2026, 12, 10, 20, tzinfo=UTC))
        self.assertEqual(f(20, 59, 59), datetime(2026, 12, 10, 20, 59, 59, tzinfo=UTC))
        self.assertEqual(f(8), datetime(2026, 12, 10, 8, tzinfo=UTC))
        self.assertEqual(f(7, 59), datetime(2026, 12, 9, 20, tzinfo=UTC))
        self.assertEqual(f(0), datetime(2026, 12, 9, 20, tzinfo=UTC))

    def test_appointment_time_in_or_out_of_quiet_hours(self):
        now = datetime(2026, 12, 1, tzinfo=UTC)
        r = plan_reminders([_ap(starts_at=datetime(2026, 12, 10, 22, tzinfo=DUB))], now)
        self.assertEqual([x["send_at"] for x in r],
                         [datetime(2026, 12, 8, 20, tzinfo=UTC), datetime(2026, 12, 10, 20, tzinfo=UTC)])
        r = plan_reminders([_ap(starts_at=datetime(2026, 12, 10, 3, tzinfo=DUB))], now)
        self.assertEqual([x["send_at"] for x in r],
                         [datetime(2026, 12, 7, 20, tzinfo=UTC), datetime(2026, 12, 9, 20, tzinfo=UTC)])
        r = plan_reminders([_ap(starts_at=datetime(2026, 12, 10, 9, tzinfo=DUB))], now)
        self.assertEqual(r[0]["send_at"], datetime(2026, 12, 8, 9, tzinfo=UTC))

    def test_dst_spring(self):
        s = datetime(2026, 3, 30, 15, 0, tzinfo=DUB)
        r = plan_reminders([_ap(starts_at=s)], datetime(2026, 3, 1, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"], s - timedelta(hours=48))
        self.assertEqual(r[0]["send_at"].utcoffset(), timedelta(0))
        self.assertEqual(r[1]["send_at"].utcoffset(), timedelta(hours=1))
        self.assertEqual(r[0]["send_at"].hour, 14)

    def test_dst_autumn(self):
        s = datetime(2026, 10, 26, 15, 0, tzinfo=DUB)
        r = plan_reminders([_ap(starts_at=s)], datetime(2026, 10, 1, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"], s.astimezone(UTC) - timedelta(hours=48))
        self.assertEqual(r[0]["send_at"].utcoffset(), timedelta(hours=1))
        self.assertEqual(r[0]["send_at"].hour, 16)
        self.assertIn("at 15:00.", r[0]["text"])

    def test_never_before_now(self):
        for h in range(0, 24):
            now = datetime(2026, 10, 13, h, 17, tzinfo=UTC)
            for x in plan_reminders([_ap()], now):
                self.assertGreaterEqual(x["send_at"], now)

    def test_sort_and_ties(self):
        s = datetime(2026, 10, 15, 14, 30, tzinfo=DUB)
        r = plan_reminders([_ap(id="b", starts_at=s), _ap(id="a", starts_at=s)], self.NOW)
        self.assertEqual([x["appointment_id"] for x in r], ["a", "b", "a", "b"])

    def test_sms_length_and_name_ladder(self):
        long_name = "A" * 100 + " Surname"
        t = plan_reminders([_ap(customer_name=long_name)], self.NOW)[0]["text"]
        self.assertLessEqual(len(t), SMS_LIMIT)
        self.assertTrue(t.startswith("Hi AAA"))
        self.assertTrue(t.endswith("Chevonne Nee Divver"))
        self.assertIn("14:30", t)
        e = plan_reminders([_ap(customer_name=long_name, optout_sms_v2=True)], self.NOW)[0]["text"]
        self.assertIn(long_name, e)
        n = plan_reminders([_ap(customer_name=None)], self.NOW)[0]["text"]
        self.assertTrue(n.startswith("Your Brennan"))
        self.assertLessEqual(len(_compose("", datetime(2026, 1, 1, 8, 0), SIGNATURES["PL"])), SMS_LIMIT)

    def test_polish_signature(self):
        for c in ("PL", " pl "):
            for ap in (_ap(country=c), _ap(country=c, optout_sms_v2=True)):
                t = plan_reminders([ap], self.NOW)[0]["text"]
                self.assertTrue(t.endswith("Grzegorz Szczepański"))
                self.assertEqual(t, t.rstrip())
                self.assertLessEqual(len(t), SMS_LIMIT) if ap["optout_sms_v2"] is False else None

    def test_country_timezone_config(self):
        s = datetime(2026, 12, 10, 14, 30, tzinfo=UTC)
        with mock.patch.dict(COUNTRY_TZ, {"PL": "Europe/Warsaw"}):
            t = plan_reminders([_ap(country="PL", starts_at=s)], datetime(2026, 12, 1, tzinfo=UTC))[0]["text"]
        self.assertIn("at 15:30.", t)
        t = plan_reminders([_ap(country="PL", starts_at=s)], datetime(2026, 12, 1, tzinfo=UTC))[0]["text"]
        self.assertIn("at 14:30.", t)

    def test_logs_have_no_pii(self):
        records = []

        class H(logging.Handler):
            def emit(self, rec):
                records.append(rec.getMessage())

        h = H()
        root = logging.getLogger()
        old = root.level
        root.addHandler(h)
        root.setLevel(logging.DEBUG)
        try:
            plan_reminders([_ap(), _ap(id="e", optout_sms_v2=True, customer_name="Zed Zorro",
                                       email="zed@secret.example"),
                            _ap(id=None, starts_at=None), _ap(id="n", phone=None, email=None),
                            _ap(id="c", status="cancelled")], self.NOW)
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        blob = "\n".join(records)
        self.assertIn("appointment_id=a1", blob)
        self.assertIn("index=2", blob)
        self.assertIn("reason=no_channel", blob)
        for secret in ("mary@example.com", "zed@secret.example", "+353851234567",
                       "Mary", "Murphy", "Zorro"):
            self.assertNotIn(secret, blob)


if __name__ == "__main__":
    unittest.main()