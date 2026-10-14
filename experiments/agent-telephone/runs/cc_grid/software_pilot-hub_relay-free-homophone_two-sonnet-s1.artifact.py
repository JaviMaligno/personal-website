"""Brennan Opticians appointment reminder planner (standard library only, Python 3.12).

Public entry point: plan_reminders(appointments, now). The planner is pure, uses no system clock and is independent of the host timezone.
The tests are in this same file. Run them with:
    python3 -m unittest -v <this_file_name>      (or: python3 <this_file_name>)
I had no tools, so the tests have NOT been executed. Run them before relying on this.

Assumptions for the client to confirm:
- The 2h interval was inferred from a garbled brief (SECOND_REMINDER_OFFSET). The 48h value is FIRST_REMINDER_OFFSET.
- The quiet-hours forward fallback (08:00 Dublin next morning, only if strictly before the start).
- The late catch-up for appointments under 2h away (sent at now, subject to quiet hours).
- 48h means elapsed hours on absolute instants, not wall-clock hours across a DST change.
- Dublin time is used for all appointments, including PL customers.
- 160 characters is counted in code points. Names in signatures contain accents, so the real
  SMS segments are Unicode (UCS-2) and may be about 70 characters each.
- The full list of statuses: only "cancelled" suppresses reminders, all others stay eligible.
- The wording, and that no email subject is produced (output has only the four agreed keys).
- Deduplication of repeated runs is the caller's job.
- House rule vs privacy: the INFO line per planned reminder carries the appointment id and the channel
  but deliberately NOT the phone or email, because of the Data Protection Commission audit finding.
  Support can look the contact up by appointment id.
"""
from __future__ import annotations

import copy
import logging
import os
import time as _time
import unicodedata
import unittest
from collections.abc import Mapping
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

FIRST_REMINDER_OFFSET = timedelta(hours=48)
SECOND_REMINDER_OFFSET = timedelta(hours=2)  # inferred from a garbled brief; confirm with client
SMS_MAX_LEN = 160
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SEND_EVENING_HOUR = 20

SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _aware(dt) -> bool:
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _adjust_quiet(t: datetime, now: datetime, starts: datetime):
    """Apply quiet hours to UTC instant t. Return adjusted UTC instant, or None to drop."""
    loc = t.astimezone(DUBLIN)
    if QUIET_END_HOUR <= loc.hour < QUIET_START_HOUR:
        return t
    evening = loc.hour >= QUIET_START_HOUR
    day = loc.date() if evening else loc.date() - timedelta(days=1)
    back = datetime.combine(day, time(SEND_EVENING_HOUR), DUBLIN).astimezone(UTC)
    if back >= now:
        return back
    day = loc.date() + timedelta(days=1) if evening else loc.date()
    fwd = datetime.combine(day, time(QUIET_END_HOUR), DUBLIN).astimezone(UTC)
    return fwd if fwd < starts else None


def _build_text(name, starts: datetime, country, sms: bool) -> str:
    country_s = country.strip().casefold() if isinstance(country, str) else ""
    sig = SIGNATURE_PL if country_s == "pl" else SIGNATURE_DEFAULT
    loc = starts.astimezone(DUBLIN)
    when = f"{loc.day} {_MONTHS[loc.month - 1]} {loc.year} at {loc:%H:%M}"

    def make(n: str) -> str:
        greeting = f"Hi {n}" if n else "Hi there"
        return _nfc(f"{greeting}, a reminder of your appointment at Brennan Opticians on {when}. {sig}")

    clean = " ".join(_nfc(name).split()) if isinstance(name, str) else ""
    if not sms:
        return make(clean)
    parts = clean.split()
    candidates = [clean]
    if parts:
        first = parts[0]
        if len(parts) > 1:
            candidates.append(f"{first} {parts[-1][0]}.")
        candidates.append(first)
        candidates.extend(first[:k] + "." for k in range(len(first) - 1, 0, -1))
    candidates.append("")
    for c in candidates:
        text = make(c)
        if len(text) <= SMS_MAX_LEN:
            return text
    return make("")


def _channel(a: Mapping, aid):
    optout = a.get("optout_sms_v2")
    if not isinstance(optout, bool):
        logger.warning("optout_sms_v2 missing or invalid, treating as opted out: appointment_id=%s", aid)
        optout = True
    phone = a.get("phone")
    if isinstance(phone, str) and phone.strip() and not optout:
        return "sms"
    email = a.get("email")
    if isinstance(email, str) and email.strip():
        return "email"
    return None


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_u = now.astimezone(UTC)
    planned = []
    for a in appointments:
        if not isinstance(a, Mapping):
            logger.warning("skipping malformed appointment (not a mapping)")
            continue
        aid = a.get("id")
        if aid is None:
            logger.warning("skipping malformed appointment (missing id)")
            continue
        starts = a.get("starts_at")
        if not _aware(starts):
            logger.warning("skipping malformed appointment (bad starts_at): appointment_id=%s", aid)
            continue
        status = a.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            logger.info("appointment cancelled, no reminders: appointment_id=%s", aid)
            continue
        starts_u = starts.astimezone(UTC)
        if starts_u <= now_u:
            continue
        channel = _channel(a, aid)
        if channel is None:
            logger.info("no usable contact channel, no reminders: appointment_id=%s", aid)
            continue

        first = _adjust_quiet(max(starts_u - FIRST_REMINDER_OFFSET, now_u), now_u, starts_u)
        t2 = starts_u - SECOND_REMINDER_OFFSET
        second = _adjust_quiet(t2, now_u, starts_u) if t2 >= now_u else None
        if first is not None and first == second:
            first = None
        text = _build_text(a.get("customer_name"), starts_u, a.get("country"), channel == "sms")
        for send_at in (first, second):
            if send_at is not None:
                planned.append({"appointment_id": aid, "channel": channel,
                                "send_at": send_at.astimezone(UTC), "text": text})
    planned.sort(key=lambda r: r["send_at"])  # stable: ties keep input order
    for r in planned:
        logger.info("planned reminder: appointment_id=%s channel=%s send_at=%s",
                    r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return planned


# ----------------------------------------------------------------------------- tests

def U(*a):
    return datetime(*a, tzinfo=UTC)


def dub(*a):
    return datetime(*a, tzinfo=DUBLIN).astimezone(UTC)


NOW = U(2026, 10, 13, 12, 0)
EMAIL = "jane.secret@example.com"
PHONE = "+353851112222"


def appt(**kw):
    d = dict(id="A1", customer_name="Mary Murphy", email="mary.secret@example.com",
             phone="+353871234567", country="IE", status="booked",
             starts_at=U(2026, 10, 20, 14, 0), optout_sms_v2=False)
    d.update(kw)
    return d


def two_h_send(local_utc):
    res = plan_reminders([appt(starts_at=local_utc + timedelta(hours=2))], NOW)
    return res[-1]["send_at"]


class TestPlanner(unittest.TestCase):
    def test_cancelled(self):
        for s in ("cancelled", " Cancelled ", "CANCELLED"):
            self.assertEqual(plan_reminders([appt(status=s)], NOW), [])
        self.assertEqual(len(plan_reminders([appt(status="Booked")], NOW)), 2)

    def test_naive_now(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 12, 0))

    def test_two_sms_with_quiet_adjustment(self):
        res = plan_reminders([appt(starts_at=U(2026, 10, 20, 22, 0))], NOW)
        self.assertEqual([r["send_at"] for r in res], [U(2026, 10, 18, 19, 0), U(2026, 10, 20, 19, 0)])
        self.assertTrue(all(r["channel"] == "sms" for r in res))
        self.assertIn("20 Oct 2026 at 23:00", res[0]["text"])
        self.assertEqual(res[0]["send_at"].tzinfo, UTC)

    def test_plain_times(self):
        res = plan_reminders([appt()], NOW)
        self.assertEqual([r["send_at"] for r in res], [U(2026, 10, 18, 14), U(2026, 10, 20, 12)])

    def test_catch_up(self):
        res = plan_reminders([appt(starts_at=U(2026, 10, 14, 14))], NOW)
        self.assertEqual([r["send_at"] for r in res], [NOW, U(2026, 10, 14, 12)])

    def test_under_two_hours(self):
        res = plan_reminders([appt(starts_at=U(2026, 10, 13, 13))], NOW)
        self.assertEqual([r["send_at"] for r in res], [NOW])
        self.assertIn("at 14:00", res[0]["text"])

    def test_started_or_past(self):
        self.assertEqual(plan_reminders([appt(starts_at=NOW)], NOW), [])
        self.assertEqual(plan_reminders([appt(starts_at=U(2026, 10, 1))], NOW), [])

    def test_never_in_past(self):
        starts = [U(2026, 10, 15, 7, 30), U(2026, 10, 14, 23, 0), U(2026, 10, 25, 0, 30)]
        base = U(2026, 10, 13, 0, 0)
        for i in range(400):
            now = base + timedelta(minutes=41 * i)
            for s in starts:
                for r in plan_reminders([appt(starts_at=s)], now):
                    self.assertGreaterEqual(r["send_at"], now)
                    self.assertLess(r["send_at"], s)

    def test_quiet_boundaries(self):
        self.assertEqual(two_h_send(dub(2026, 10, 20, 20, 59)), dub(2026, 10, 20, 20, 59))
        self.assertEqual(two_h_send(dub(2026, 10, 20, 21, 0)), dub(2026, 10, 20, 20, 0))
        self.assertEqual(two_h_send(dub(2026, 10, 21, 0, 0)), dub(2026, 10, 20, 20, 0))
        self.assertEqual(two_h_send(dub(2026, 10, 20, 7, 59)), dub(2026, 10, 19, 20, 0))
        self.assertEqual(two_h_send(dub(2026, 10, 20, 8, 0)), dub(2026, 10, 20, 8, 0))

    def test_forward_fallback_and_dedupe(self):
        now = U(2026, 10, 13, 21, 30)
        res = plan_reminders([appt(starts_at=U(2026, 10, 14, 8, 30))], now)
        self.assertEqual([r["send_at"] for r in res], [U(2026, 10, 14, 7, 0)])

    def test_forward_drop(self):
        now = U(2026, 10, 13, 21, 30)
        self.assertEqual(plan_reminders([appt(starts_at=U(2026, 10, 14, 6, 30))], now), [])

    def test_channels(self):
        def ch(**kw):
            return [r["channel"] for r in plan_reminders([appt(**kw)], NOW)]
        self.assertEqual(ch(), ["sms", "sms"])
        self.assertEqual(ch(optout_sms_v2=True), ["email", "email"])
        self.assertEqual(ch(phone="  "), ["email", "email"])
        self.assertEqual(ch(phone=None), ["email", "email"])
        self.assertEqual(ch(optout_sms_v2=True, email=" "), [])
        self.assertEqual(ch(phone="", email=None), [])

    def test_optout_missing_or_invalid(self):
        for v in (None, "false", 0):
            with self.assertLogs(logger, "WARNING") as cm:
                res = plan_reminders([appt(optout_sms_v2=v)], NOW)
            self.assertEqual({r["channel"] for r in res}, {"email"})
            self.assertTrue(any("A1" in m for m in cm.output))
        d = appt()
        del d["optout_sms_v2"]
        with self.assertLogs(logger, "WARNING"):
            self.assertEqual(plan_reminders([d], NOW)[0]["channel"], "email")

    def test_old_opt_out_ignored(self):
        self.assertEqual(plan_reminders([appt(opt_out=True)], NOW)[0]["channel"], "sms")
        self.assertEqual(plan_reminders([appt(opt_out=False, optout_sms_v2=True)], NOW)[0]["channel"], "email")

    def _budget(self):
        r = plan_reminders([appt(customer_name="x")], NOW)
        return SMS_MAX_LEN - len(r[0]["text"]) + 1  # max name length that fits

    def _sms(self, name):
        t = plan_reminders([appt(customer_name=name)], NOW)[0]["text"]
        self.assertLessEqual(len(t), SMS_MAX_LEN)
        self.assertTrue(t.endswith(SIGNATURE_DEFAULT))
        self.assertIn("20 Oct 2026 at 15:00", t)
        return t

    def test_length_steps(self):
        b = self._budget()
        self.assertTrue(self._sms("Mary Murphy").startswith("Hi Mary Murphy, a reminder"))
        full = "F" * (b - 4) + " Lee"
        self.assertTrue(self._sms(full).startswith(f"Hi {full},"))
        self.assertTrue(self._sms("Mary " + "B" * 200).startswith("Hi Mary B.,"))
        self.assertTrue(self._sms("F" * b + " Lee").startswith("Hi " + "F" * b + ","))
        t = self._sms("F" * (b + 5) + " Lee")
        self.assertTrue(t.startswith("Hi " + "F" * (b - 1) + ".,"))
        self.assertEqual(len(t), SMS_MAX_LEN)
        self._sms("N" * 300)
        self._sms("  ".join(["Longname"] * 40))

    def test_generic_greeting(self):
        for n in ("", "   ", None):
            t = plan_reminders([appt(customer_name=n)], NOW)[0]["text"]
            self.assertTrue(t.startswith("Hi there, a reminder"))
        d = appt()
        del d["customer_name"]
        self.assertTrue(plan_reminders([d], NOW)[0]["text"].startswith("Hi there,"))

    def test_email_full_name_no_limit(self):
        name = "N" * 300
        r = plan_reminders([appt(customer_name=name, optout_sms_v2=True)], NOW)[0]
        self.assertEqual(r["channel"], "email")
        self.assertIn(name, r["text"])
        self.assertGreater(len(r["text"]), SMS_MAX_LEN)

    def test_pl_signature_and_nfc(self):
        t = plan_reminders([appt(country=" pl ")], NOW)[0]["text"]
        self.assertTrue(t.endswith("Grzegorz Szczepański"))
        t = plan_reminders([appt(customer_name="Jose\u0301")], NOW)[0]["text"]
        self.assertEqual(t, unicodedata.normalize("NFC", t))
        self.assertIn("Jos\u00e9", t)
        self.assertTrue(plan_reminders([appt(country=None)], NOW)[0]["text"].endswith(SIGNATURE_DEFAULT))

    def test_dublin_time_vs_utc(self):
        def txt(s):
            return plan_reminders([appt(starts_at=s)], NOW)[0]["text"]
        self.assertIn("20 Oct 2026 at 23:30", txt(U(2026, 10, 20, 22, 30)))
        self.assertIn("21 Oct 2026 at 00:30", txt(U(2026, 10, 20, 23, 30)))
        self.assertIn("24 Oct 2026 at 13:00", txt(U(2026, 10, 24, 12, 0)))
        self.assertIn("25 Oct 2026 at 12:00", txt(U(2026, 10, 25, 12, 0)))
        ny = datetime(2026, 10, 20, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        self.assertIn("20 Oct 2026 at 15:00", txt(ny))

    def test_elapsed_48h_across_clock_change(self):
        res = plan_reminders([appt(starts_at=U(2026, 10, 26, 12, 0))], NOW)
        self.assertEqual([r["send_at"] for r in res], [U(2026, 10, 24, 12, 0), U(2026, 10, 26, 10, 0)])

    def test_sorting_keys_ties(self):
        res = plan_reminders([appt(id="late", starts_at=U(2026, 10, 22, 14)),
                              appt(id="early", starts_at=U(2026, 10, 20, 14))], NOW)
        self.assertEqual([r["appointment_id"] for r in res], ["early", "early", "late", "late"])
        self.assertEqual([r["send_at"] for r in res], sorted(r["send_at"] for r in res))
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
        res = plan_reminders([appt(id="A"), appt(id="B")], NOW)
        self.assertEqual([r["appointment_id"] for r in res], ["A", "B", "A", "B"])

    def test_output_has_no_contact(self):
        res = plan_reminders([appt(email=EMAIL, phone=PHONE)], NOW)
        self.assertNotIn(EMAIL, repr(res))
        self.assertNotIn(PHONE, repr(res))

    def test_malformed_skipped(self):
        bad = [appt(id=None), appt(starts_at=None), appt(starts_at=datetime(2026, 10, 20, 14)), "junk"]
        d = appt(id="OK")
        with self.assertLogs(logger, "WARNING"):
            res = plan_reminders(bad + [d], NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"OK"})

    def test_no_mutation(self):
        data = [appt(), appt(id="A2", optout_sms_v2=None, opt_out=True)]
        before = copy.deepcopy(data)
        with self.assertLogs(logger, "WARNING"):
            plan_reminders(data, NOW)
        self.assertEqual(data, before)

    def test_logs_have_no_personal_data(self):
        class Cap(logging.Handler):
            def __init__(self):
                super().__init__(logging.DEBUG)
                self.records = []

            def emit(self, record):
                self.records.append(record)

        cap = Cap()
        root = logging.getLogger()
        old = root.level
        root.addHandler(cap)
        root.setLevel(logging.DEBUG)
        try:
            kw = dict(email=EMAIL, phone=PHONE, customer_name="Jane Secret")
            plan_reminders([
                appt(id="N1", **kw),
                appt(id="C1", status="cancelled", **kw),
                appt(id="M1", optout_sms_v2=None, **kw),
                appt(id="X1", starts_at=datetime(2026, 10, 20, 14), **kw),
                appt(id=None, **kw),
                appt(id="NC", optout_sms_v2=True, **dict(kw, email="")),
                appt(id="E1", optout_sms_v2=True, **kw),
            ], NOW)
        finally:
            root.removeHandler(cap)
            root.setLevel(old)
        self.assertTrue(cap.records)
        for r in cap.records:
            blob = (r.getMessage() + repr(r.args) + str(r.msg)).lower()
            for secret in ("jane.secret", "@example.com", "353851112222", "jane", "secret"):
                self.assertNotIn(secret, blob)

    def test_host_timezone_independent(self):
        if not hasattr(_time, "tzset"):
            self.skipTest("tzset unavailable")
        old = os.environ.get("TZ")
        results = []
        try:
            for tz in ("UTC", "America/Los_Angeles", "Asia/Tokyo"):
                os.environ["TZ"] = tz
                _time.tzset()
                results.append(plan_reminders(
                    [appt(starts_at=U(2026, 10, 20, 22, 0)), appt(id="B", starts_at=U(2026, 10, 25, 0, 30))],
                    NOW))
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            _time.tzset()
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])


if __name__ == "__main__":
    unittest.main()