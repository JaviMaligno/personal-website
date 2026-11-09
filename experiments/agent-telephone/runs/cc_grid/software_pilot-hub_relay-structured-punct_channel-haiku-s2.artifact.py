"""
Brennan Opticians appointment reminder planner.

Reviewer notes (kept here because the reply is code only):

OPEN items and where they are isolated:
- Q1 (R9) SMS gate: sms_gate_passes(). Literal client wording is "text if optout_sms_v2 is true". This conflicts with R5, where the field is an opt-out flag, so true most likely means opted out. The literal wording is the default. Invert only in sms_gate_passes() after confirmation.
- Q2 (R23) Email fallback: choose_channel() and EMAIL_FALLBACK_ENABLED. Email is used only when there is no phone and an email exists. Set EMAIL_FALLBACK_ENABLED to False to switch it off.
- Q3 (R24) Email timing, quiet hours and cancellation follow the SMS path. Both channels go through _plan_one() and apply_quiet_hours().
- Q4 (R20) The 2-hour reminder is skipped, not sent immediately, if its point is before now. See _plan_one().
- Q5 (R25) Quiet hours: apply_quiet_hours(). Conflict with R8: moving a reminder back to 20:00 can land before now. The code then defers to 08:00 Dublin the next allowed morning.
- Q6 (R22) Only the exact status "cancelled" excludes an appointment. See _plan_one().
- Q7 (R27) SMS length is len(text). Non-GSM characters may change real segment size. SMS_LIMIT is not changed.
- Q9 (R29) Date format is in format_when().
- Q10 (R32) Deduplication is the caller's job. The function is stateless.

Other conflicts:
- R9 vs R5: the gate meaning is ambiguous (see Q1).
- R23 vs "don't email instead": with a phone present but the gate failing, nothing is sent, so email is not used as a substitute.
- House rule (log the contact) vs R13/R33 (never log contact details): logs carry appointment_id and channel only.
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
EMAIL_FALLBACK_ENABLED = True  # Q2
QUIET_START_HOUR = 21  # R11, R25
QUIET_END_HOUR = 8
EVENING_HOUR = 20
FIRST_OFFSET = timedelta(hours=48)  # R6
SECOND_OFFSET = timedelta(hours=2)
REQUIRED_KEYS = (
    "id", "customer_name", "email", "phone", "country",
    "status", "starts_at", "optout_sms_v2",
)
CHANNELS = ("sms", "email")
SIG_DEFAULT = "Siobhán Ní Dhuibhir"  # R14
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

logger = logging.getLogger(__name__)


def _require_aware(dt, label):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return dt.astimezone(UTC)


def _validate(appt):
    # R30: messages name keys only, never values (R13, R33).
    if not isinstance(appt, dict):
        raise ValueError("each appointment must be a dict")
    missing = [k for k in REQUIRED_KEYS if k not in appt]
    if missing:
        raise ValueError("appointment is missing required keys: " + ", ".join(missing))
    _require_aware(appt["starts_at"], "starts_at")


def _check_channel(channel):
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel: {channel!r}")
    return channel


def _has_value(v):
    return bool(v and str(v).strip())


def sms_gate_passes(appt):
    # Q1 OPEN. Literal client wording: "text them if optout_sms_v2 is true".
    # Conflicts with R5 (the field is an opt-out flag). Do not invert without confirmation.
    return bool(appt["optout_sms_v2"])


def choose_channel(appt):
    # R9 and R23 (Q2). Returns "sms", "email", or None. Never both.
    if _has_value(appt["phone"]):
        return "sms" if sms_gate_passes(appt) else None
    if EMAIL_FALLBACK_ENABLED and _has_value(appt["email"]):
        return "email"
    return None


def signature_for(country):
    return SIG_PL if country == "PL" else SIG_DEFAULT  # R14


def format_when(starts_utc):
    # Q9 OPEN. "DD Mon YYYY" and HH:MM in Europe/Dublin (R4, R29).
    local = starts_utc.astimezone(DUBLIN)
    date_str = f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"
    time_str = f"{local.hour:02d}:{local.minute:02d}"
    return date_str, time_str


def name_variants(name):
    # R10, R28: full name, first initial plus surname, first name, first initial.
    # The caller appends "" last to drop the name.
    parts = name.split()
    if not parts:
        return []
    first, last = parts[0], parts[-1]
    candidates = [" ".join(parts)]
    if len(parts) >= 2:
        candidates.append(f"{first[0]}. {last}")
    candidates.append(first)
    candidates.append(f"{first[0]}.")
    unique = []
    for c in candidates:
        if c not in unique:
            unique.append(c)
    return unique


def _body(name, when_date, when_time, sig):
    prefix = f"Hi {name}, " if name else ""
    return f"{prefix}Brennan Opticians appointment on {when_date} at {when_time}. {sig}"


def build_text(channel, appt, starts_utc):
    _check_channel(channel)
    sig = signature_for(appt["country"])
    when_date, when_time = format_when(starts_utc)
    name = " ".join(str(appt["customer_name"]).split())
    if channel == "email":
        return _body(name, when_date, when_time, sig)  # R24: no length limit
    for candidate in name_variants(name) + [""]:
        text = _body(candidate, when_date, when_time, sig)
        if len(text) <= SMS_LIMIT:
            return text
    raise ValueError("SMS fixed text exceeds SMS_LIMIT even without a customer name")


def _is_quiet(local):
    return local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR


def apply_quiet_hours(send_utc, now_utc):
    # Q5 OPEN (R25). Caller guarantees send_utc >= now_utc.
    local = send_utc.astimezone(DUBLIN)
    if not _is_quiet(local):
        return send_utc
    day = local.date()
    evening_day = day if local.hour >= QUIET_START_HOUR else day - timedelta(days=1)
    evening = datetime(evening_day.year, evening_day.month, evening_day.day,
                       EVENING_HOUR, 0, tzinfo=DUBLIN).astimezone(UTC)
    if evening >= now_utc:
        return evening
    # Conflict R25 vs R8: the 20:00 target is before now. Defer to 08:00 Dublin,
    # the next allowed morning at or after the send time.
    morning_day = day + timedelta(days=1) if local.hour >= QUIET_START_HOUR else day
    return datetime(morning_day.year, morning_day.month, morning_day.day,
                    QUIET_END_HOUR, 0, tzinfo=DUBLIN).astimezone(UTC)


def _plan_one(appt, now_utc):
    if appt["status"] == "cancelled":  # R12, R22: exact match only
        return []
    starts = _require_aware(appt["starts_at"], "starts_at")
    if starts <= now_utc:  # R21
        return []
    channel = choose_channel(appt)
    if channel is None:
        return []

    points = []
    first = starts - FIRST_OFFSET  # R6, absolute-time arithmetic in UTC
    if first < now_utc:
        first = now_utc  # R7 applies to the first reminder only (R19)
    points.append(first)
    second = starts - SECOND_OFFSET
    if second >= now_utc:  # R20: never send the 2-hour reminder late
        points.append(second)

    text = build_text(channel, appt, starts)
    out = []
    for point in points:
        send_at = apply_quiet_hours(point, now_utc)
        if send_at < now_utc or _is_quiet(send_at.astimezone(DUBLIN)):
            raise RuntimeError("internal error: reminder violates timing rules")
        out.append({
            "appointment_id": appt["id"],
            "channel": _check_channel(channel),
            "send_at": send_at,
            "text": text,
        })
    return out


def plan_reminders(appointments, now):
    now_utc = _require_aware(now, "now")
    appts = list(appointments)
    for appt in appts:
        _validate(appt)
    planned = []
    for appt in appts:
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))  # R17, R31
    for r in planned:
        # House rule asks for the contact in this line. R13 and R33 forbid it,
        # so the line carries the appointment id (recipient) and channel only.
        logger.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                    r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return planned


# ---------------------------------------------------------------------------
# Tests. Fake data only. No email address is printed or logged.
# ---------------------------------------------------------------------------
import sys
import unittest
from unittest import mock


def D(*args):
    return datetime(*args, tzinfo=DUBLIN)


FAKE_EMAIL = "fake.customer@example.test"


def make_appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": FAKE_EMAIL,
        "phone": "+353800000000",
        "country": "IE",
        "status": "booked",
        "starts_at": D(2026, 10, 18, 14, 0),
        "optout_sms_v2": True,  # Q1: literal wording, gate passes
    }
    base.update(overrides)
    return base


class PlanRemindersTests(unittest.TestCase):

    def test_ac1_five_days_out_gives_two_reminders(self):
        now = D(2026, 10, 13, 9, 0)
        out = plan_reminders([make_appt()], now)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], D(2026, 10, 16, 14, 0))
        self.assertEqual(out[1]["send_at"], D(2026, 10, 18, 12, 0))

    def test_ac2_three_hours_out_sends_immediately_then_two_hour(self):
        now = D(2026, 10, 13, 10, 0)
        out = plan_reminders([make_appt(starts_at=D(2026, 10, 13, 13, 0))], now)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], now)  # R7, 10:00 is not quiet
        self.assertEqual(out[1]["send_at"], D(2026, 10, 13, 11, 0))

    def test_ac3_cancelled_gives_empty(self):
        out = plan_reminders([make_appt(status="cancelled")], D(2026, 10, 13, 9, 0))
        self.assertEqual(out, [])

    def test_status_match_is_exact(self):
        out = plan_reminders([make_appt(status="Cancelled")], D(2026, 10, 13, 9, 0))
        self.assertEqual(len(out), 2)

    def test_dst_arithmetic_is_absolute(self):
        now = D(2026, 10, 13, 9, 0)
        starts = D(2026, 10, 27, 10, 0)  # after the 25 Oct fall-back
        out = plan_reminders([make_appt(starts_at=starts)], now)
        expected_first = starts.astimezone(UTC) - timedelta(hours=48)
        self.assertEqual(out[0]["send_at"], expected_first)

    def test_quiet_hours_move_two_hour_reminder_to_evening(self):
        now = D(2026, 10, 13, 9, 0)
        starts = D(2026, 10, 15, 7, 0)  # 2-hour point is 05:00, quiet
        out = plan_reminders([make_appt(starts_at=starts)], now)
        self.assertEqual(out[-1]["send_at"], D(2026, 10, 14, 20, 0))

    def test_quiet_hours_defer_when_evening_is_before_now(self):
        now = D(2026, 10, 13, 21, 30)  # immediate send falls in quiet hours
        starts = D(2026, 10, 14, 2, 0)
        out = plan_reminders([make_appt(starts_at=starts)], now)
        self.assertEqual(len(out), 2)
        for r in out:
            self.assertEqual(r["send_at"], D(2026, 10, 14, 8, 0))

    def test_ac4_invariants_over_grid(self):
        now = D(2026, 10, 13, 9, 0)
        for hours in range(1, 200, 7):
            starts = now + timedelta(hours=hours)
            for r in plan_reminders([make_appt(starts_at=starts)], now):
                self.assertGreaterEqual(r["send_at"], now)
                local = r["send_at"].astimezone(DUBLIN)
                self.assertFalse(local.hour >= 21 or local.hour < 8)

    def test_no_reminder_after_start(self):
        now = D(2026, 10, 13, 9, 0)
        out = plan_reminders([make_appt(starts_at=D(2026, 10, 13, 8, 0))], now)
        self.assertEqual(out, [])

    def test_ac5_sms_length_date_time_and_signature(self):
        now = D(2026, 10, 13, 9, 0)
        long_name = "X" * 90 + " " + "Y" * 90
        out = plan_reminders([make_appt(customer_name=long_name)], now)
        for r in out:
            self.assertEqual(r["channel"], "sms")
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("18 Oct 2026", r["text"].replace("18 Oct 2026", "18 Oct 2026"))
            self.assertIn("14:00", r["text"].replace("14:00", "14:00") if r["send_at"] else "")
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_name_shortens_to_initial_when_needed(self):
        now = D(2026, 10, 13, 9, 0)
        long_name = "X" * 100 + " " + "Y" * 100
        out = plan_reminders([make_appt(customer_name=long_name)], now)
        self.assertTrue(out[0]["text"].startswith("Hi X., "))

    def test_fixed_text_too_long_raises(self):
        now = D(2026, 10, 13, 9, 0)
        with mock.patch.object(sys.modules[__name__], "SMS_LIMIT", 30):
            with self.assertRaises(ValueError):
                plan_reminders([make_appt()], now)

    def test_ac6_polish_signature(self):
        now = D(2026, 10, 13, 9, 0)
        out = plan_reminders([make_appt(country="PL")], now)
        for r in out:
            self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))

    def test_ac7_no_sms_and_email_for_same_reminder(self):
        now = D(2026, 10, 13, 9, 0)
        out = plan_reminders([make_appt(optout_sms_v2=False)], now)
        self.assertEqual(out, [])  # phone present, gate fails: no email substitute

    def test_email_only_when_no_phone(self):
        now = D(2026, 10, 13, 9, 0)
        out = plan_reminders([make_appt(phone=None)], now)
        self.assertEqual(len(out), 2)
        for r in out:
            self.assertEqual(r["channel"], "email")
            self.assertNotIn(FAKE_EMAIL, r["text"])

    def test_ac8_sorted_ascending(self):
        now = D(2026, 10, 13, 9, 0)
        appts = [
            make_appt(id="B", starts_at=D(2026, 10, 20, 14, 0)),
            make_appt(id="A", starts_at=D(2026, 10, 18, 14, 0)),
        ]
        out = plan_reminders(appts, now)
        sends = [r["send_at"] for r in out]
        self.assertEqual(sends, sorted(sends))

    def test_ac9_no_email_in_logs(self):
        now = D(2026, 10, 13, 9, 0)
        with self.assertLogs(level="INFO") as cm:
            plan_reminders([make_appt()], now)
        self.assertNotIn(FAKE_EMAIL, "\n".join(cm.output))

    def test_ac10_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([make_appt()], datetime(2026, 10, 13, 9, 0))

    def test_ac10_missing_key_raises_without_email(self):
        bad = make_appt()
        del bad["optout_sms_v2"]
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([bad], D(2026, 10, 13, 9, 0))
        self.assertNotIn(FAKE_EMAIL, str(ctx.exception))

    def test_unknown_channel_raises(self):
        with self.assertRaises(ValueError):
            _check_channel("fax")

    def test_naive_starts_at_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([make_appt(starts_at=datetime(2026, 10, 18, 14, 0))],
                           D(2026, 10, 13, 9, 0))


if __name__ == "__main__":
    unittest.main()