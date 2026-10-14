"""Brennan Opticians appointment reminders (standard library only).

Public entry point: plan_reminders(appointments, now). It is pure and
deterministic and never reads the clock. The caller must deduplicate
reminders that were already sent, because the "send now" reminder (send_at
== now) is re-planned on every run.

Business time is Europe/Dublin via zoneinfo, never host local time.

Logging: one INFO line per planned reminder with appointment id, channel and
reminder number. Deliberately NOT logged: email, phone, name (R10 overrides
the "contact" part of the house rule). Support can look the contact up by
appointment id.

NOTE: this module was written without the ability to execute code, so the
embedded unittest suite (python -m unittest brennan_reminders) has NOT been
run yet.

Open assumptions (not confirmed with client):
- Missing/None optout_sms_v2 means opted out (email fallback).
- Opt-out blocks SMS only, not email.
- Date format is "14 Oct 2026" (day-first, English month abbreviation).
- PL customers get Dublin time and English text.
- The 160 limit is len() of the string; accented signature characters are
  outside GSM-7, so an SMS may still be sent as multiple parts.
- Deduplication of already-sent reminders is the caller's job.
- Two reminders can end up with the same send_at after quiet-hour deferral.
"""
import logging
import unicodedata
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Dublin")
SMS_MAX_LEN = 160
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
QUIET_FALLBACK_HOUR = 20
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

log = logging.getLogger("brennan.reminders")


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _present(v):
    return isinstance(v, str) and bool(v.strip())


def _quiet(local):
    return local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR


def _shift_back(t):
    local = t.astimezone(TZ)
    if not _quiet(local):
        return t
    day = local.date() if local.hour >= QUIET_START_HOUR else local.date() - timedelta(days=1)
    return datetime.combine(day, dtime(QUIET_FALLBACK_HOUR), tzinfo=TZ)


def _next_open(now):
    local = now.astimezone(TZ)
    day = local.date() if local.hour < QUIET_END_HOUR else local.date() + timedelta(days=1)
    return datetime.combine(day, dtime(QUIET_END_HOUR), tzinfo=TZ)


def _adjust(t, now, starts):
    """Apply quiet-hours rules (R8) after the R4 calculation. None = drop."""
    shifted = _shift_back(t)
    if shifted >= now:
        return shifted
    if not _quiet(now.astimezone(TZ)):
        return now
    nxt = _next_open(now)
    return nxt if nxt < starts else None


def _text(name, starts_local, signature, limit):
    date = f"{starts_local.day} {MONTHS[starts_local.month - 1]} {starts_local.year}"
    hhmm = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    full = " ".join(name.split()) if isinstance(name, str) else ""
    parts = full.split()
    ladder = [full]
    if parts:
        ladder += [parts[0], parts[0][0]]
    ladder.append("")
    body = f"your Brennan Opticians appointment is on {date} at {hhmm}. {signature}"
    candidate = ""
    for n in ladder:
        candidate = f"Hi {n}, {body}" if n else f"Hello, {body}"
        candidate = unicodedata.normalize("NFC", candidate)
        if limit is None or len(candidate) <= limit:
            break
    return candidate


def _plan_one(appt, now):
    aid = appt.get("id")
    if aid is None or (isinstance(aid, str) and not aid.strip()):
        log.warning("skipped appointment_id=unknown reason=missing_id")
        return []
    starts = appt.get("starts_at")
    if not _aware(starts):
        log.warning("skipped appointment_id=%s reason=bad_starts_at", aid)
        return []
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() in ("cancelled", "canceled"):
        log.info("skipped appointment_id=%s reason=cancelled", aid)
        return []
    if starts <= now:
        log.info("skipped appointment_id=%s reason=already_started", aid)
        return []

    if _present(appt.get("phone")) and appt.get("optout_sms_v2") is False:
        channel = "sms"
    elif _present(appt.get("email")):
        channel = "email"
    else:
        log.warning("skipped appointment_id=%s reason=no_contact", aid)
        return []

    r1, r2 = starts - timedelta(hours=48), starts - timedelta(hours=2)
    if r2 < now:
        points = [(1, now)]  # order 1 = the 2h reminder
    else:
        points = [(0, max(r1, now)), (1, r2)]

    country = appt.get("country")
    pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = unicodedata.normalize("NFC", SIGNATURE_PL if pl else SIGNATURE)
    starts_local = starts.astimezone(TZ)
    text = _text(appt.get("customer_name"), starts_local, sig,
                 SMS_MAX_LEN if channel == "sms" else None)

    out = []
    for order, t in points:
        send_at = _adjust(t, now, starts)
        if send_at is None:
            log.info("dropped appointment_id=%s reminder=%d reason=quiet_hours_no_slot", aid, order + 1)
            continue
        log.info("planned appointment_id=%s channel=%s reminder=%d", aid, channel, order + 1)
        out.append((send_at.astimezone(TZ), str(aid), order,
                    {"appointment_id": aid, "channel": channel,
                     "send_at": send_at.astimezone(TZ), "text": text}))
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    planned = []
    for appt in appointments or []:
        try:
            if not isinstance(appt, dict):
                log.warning("skipped appointment_id=unknown reason=invalid_record")
                continue
            planned.extend(_plan_one(appt, now))
        except Exception:  # never include exception text (could hold PII)
            log.warning("skipped appointment_id=%s reason=unexpected_error",
                        appt.get("id") if isinstance(appt, dict) else "unknown")
    planned.sort(key=lambda x: (x[0], x[1], x[2]))
    return [p[3] for p in planned]


# ---------------------------------------------------------------- tests
import copy
import os
import time as _time
import unittest
from datetime import timezone

UTC = timezone.utc
EMAIL = "secret.person@example.com"


def _appt(**kw):
    a = {"id": "A1", "customer_name": "Mary Murphy", "email": EMAIL,
         "phone": "+353851234567", "country": "IE", "status": "booked",
         "starts_at": datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
         "optout_sms_v2": False}
    a.update(kw)
    return a


NOW = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class ReminderTests(unittest.TestCase):
    def test_empty_and_naive_now(self):
        self.assertEqual(plan_reminders([], NOW), [])
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 1, 1))

    def test_keys_and_no_mutation(self):
        a = _appt()
        before = copy.deepcopy(a)
        res = plan_reminders([a], NOW)
        self.assertEqual(a, before)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})

    def test_optout_field_only(self):
        r = plan_reminders([_appt(opt_out=True, optout_sms_v2=False)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"sms"})
        r = plan_reminders([_appt(opt_out=False, optout_sms_v2=True)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})
        a = _appt()
        del a["optout_sms_v2"]
        self.assertEqual({x["channel"] for x in plan_reminders([a], NOW)}, {"email"})

    def test_no_contact_and_blank(self):
        self.assertEqual(plan_reminders([_appt(phone=" ", email="  ")], NOW), [])
        r = plan_reminders([_appt(phone="  ")], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_two_hour_only_when_close(self):
        starts = NOW + timedelta(hours=1)
        r = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], NOW)

    def test_48h_clamped_to_now(self):
        starts = NOW + timedelta(hours=10)
        r = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["send_at"], NOW)
        self.assertEqual(r[1]["send_at"], starts - timedelta(hours=2))
        self.assertTrue(all(x["send_at"] >= NOW for x in r))

    def test_started_or_cancelled(self):
        self.assertEqual(plan_reminders([_appt(starts_at=NOW)], NOW), [])
        for s in (" Cancelled ", "CANCELED"):
            self.assertEqual(plan_reminders([_appt(status=s)], NOW), [])

    def test_quiet_shift_table(self):
        d = lambda h, m, day=14: datetime(2026, 10, day, h, m, tzinfo=TZ)
        self.assertEqual(_shift_back(d(21, 0)), d(20, 0))
        self.assertEqual(_shift_back(d(20, 59)), d(20, 59))
        self.assertEqual(_shift_back(d(7, 59)), d(20, 0, 13))
        self.assertEqual(_shift_back(d(8, 0)), d(8, 0))
        self.assertEqual(_shift_back(d(0, 0)), d(20, 0, 13))

    def test_quiet_in_plan(self):
        starts = datetime(2026, 10, 15, 9, 0, tzinfo=TZ)
        r = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertEqual(r[-1]["send_at"], datetime(2026, 10, 14, 19, 0, tzinfo=UTC))

    def test_quiet_defer_and_drop(self):
        now = datetime(2026, 10, 14, 22, 0, tzinfo=TZ)
        starts = datetime(2026, 10, 15, 9, 0, tzinfo=TZ)
        r = plan_reminders([_appt(starts_at=starts)], now)
        self.assertTrue(r)
        self.assertTrue(all(x["send_at"] == datetime(2026, 10, 15, 8, 0, tzinfo=TZ) for x in r))
        starts = datetime(2026, 10, 14, 23, 0, tzinfo=TZ)
        self.assertEqual(plan_reminders([_appt(starts_at=starts)], now), [])

    def test_sms_length_and_pl(self):
        name = "A" * 100 + " " + "B" * 99
        for country, sig in (("IE", SIGNATURE), (" pl ", SIGNATURE_PL)):
            r = plan_reminders([_appt(customer_name=name, country=country)], NOW)
            for x in r:
                self.assertLessEqual(len(x["text"]), SMS_MAX_LEN)
                self.assertTrue(x["text"].endswith(sig))
                self.assertIn("20 Oct 2026 at 13:00", x["text"])
                self.assertEqual(x["text"], x["text"].rstrip())
                self.assertTrue(unicodedata.is_normalized("NFC", x["text"]))

    def test_name_ladder_and_email_unlimited(self):
        r = plan_reminders([_appt(customer_name="Mary " + "B" * 120)], NOW)
        self.assertTrue(r[0]["text"].startswith("Hi Mary,"))
        r = plan_reminders([_appt(phone="", customer_name="A" * 300)], NOW)
        self.assertIn("A" * 300, r[0]["text"])

    def test_dst(self):
        starts = datetime(2026, 3, 30, 9, 0, tzinfo=TZ)
        r = plan_reminders([_appt(starts_at=starts)], datetime(2026, 3, 20, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"], datetime(2026, 3, 28, 8, 0, tzinfo=UTC))
        starts = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
        r = plan_reminders([_appt(starts_at=starts)], datetime(2026, 10, 20, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"].hour, 13)
        self.assertEqual(r[0]["send_at"].tzinfo, TZ)

    def test_host_tz_independent(self):
        old = os.environ.get("TZ")
        try:
            results = []
            for tz in ("UTC", "Asia/Tokyo"):
                os.environ["TZ"] = tz
                _time.tzset()
                results.append(plan_reminders([_appt()], NOW))
            self.assertEqual(results[0], results[1])
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            _time.tzset()

    def test_sort_and_duplicates(self):
        res = plan_reminders([_appt(id="B"), _appt(id="A"), _appt(id="A")], NOW)
        self.assertEqual(len(res), 6)
        keys = [x["send_at"] for x in res]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([x["appointment_id"] for x in res[:3]], ["A", "A", "B"])

    def test_bad_records_skipped(self):
        bad = [_appt(starts_at=datetime(2026, 11, 1)), _appt(starts_at=None),
               _appt(id=None), "junk"]
        self.assertEqual(len(plan_reminders(bad + [_appt(id="OK")], NOW)), 2)

    def test_email_never_logged(self):
        h = _Capture()
        log.addHandler(h)
        old = log.level
        log.setLevel(logging.DEBUG)
        try:
            starts = datetime(2026, 10, 14, 23, 0, tzinfo=TZ)
            now = datetime(2026, 10, 14, 22, 0, tzinfo=TZ)
            plan_reminders([
                _appt(starts_at=datetime(2026, 11, 1)), _appt(id=None),
                _appt(id="C", status="cancelled"), _appt(id="N", phone="", email=""),
                _appt(id="D", starts_at=starts), _appt(id="S", starts_at=now),
                _appt(id="X", customer_name=5, starts_at="bad"), "junk", _appt(id="OK"),
            ], now)
            try:
                plan_reminders([_appt()], datetime(2026, 1, 1))
            except ValueError as e:
                self.assertNotIn(EMAIL, str(e))
        finally:
            log.removeHandler(h)
            log.setLevel(old)
        self.assertTrue(h.lines)
        for line in h.lines:
            self.assertNotIn(EMAIL, line)
            self.assertNotIn("+353851234567", line)


if __name__ == "__main__":
    unittest.main()