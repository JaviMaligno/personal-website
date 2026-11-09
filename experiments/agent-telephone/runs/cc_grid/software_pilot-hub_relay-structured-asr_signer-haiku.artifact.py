"""Appointment reminder planning for Brennan Opticians.

Entry point: plan_reminders(appointments, now).
Run the unit tests with: python -m unittest <this file>
Status: the tests below were written but NOT executed in this session.

[CONFIRM] defaults implemented, pending client approval:
- R9: status is compared case-insensitively; only "cancelled" is excluded.
- R12: date is DD Mon YYYY with English month abbreviations; time is HH:MM Dublin local.
- R14: ties on send_at are broken by appointment_id (string order).
- R17: email is plain text (greeting, date and time, signature), no subject, no length limit.
- R20: if the 48h and 2h reminders resolve to the same send time, only the 2h reminder is kept.
- R21: a 2h reminder whose time has passed is sent at now, subject to R8 and R20.
- R22: an SMS that cannot fit in 160 characters after shortening falls back to email if an email
  address exists; otherwise no reminder is produced.
- R24: naive datetimes in starts_at or now raise ValueError. now is validated even for empty input.
- R8: quiet-hours moves follow the spec. If the move lands before now, use now when now is outside
  quiet hours, otherwise the next 08:00 Dublin local time.
- R7: shortening order is full name, then first name, then no name.
- Unlisted assumption: a reminder whose send time is at or after starts_at is dropped.

R5 versus R8 conflict: R5 forbids send_at earlier than now, but the R8 move back to 20:00 can land
before now. Resolution used: move to now (if now is outside quiet hours) or to the next 08:00 Dublin
local time (if now is inside quiet hours). Both R5 and R8 hold. The client must confirm this.

R10 versus the house logging rule: the house rule asks for the contact in each log line, but R10
forbids personal data in logs. Resolution used: each log line carries appointment_id and channel only,
and support traces the recipient through the appointment_id. The client must confirm this.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIGNATURE = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
EVENING_SEND = time(20, 0)
MORNING_SEND = time(8, 0)
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)

logger = logging.getLogger(__name__)


def _naive(value):
    return not isinstance(value, datetime) or value.utcoffset() is None


def _is_quiet(utc_dt):
    hour = utc_dt.astimezone(DUBLIN).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _dublin_wall(day, clock):
    return datetime.combine(day, clock, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(now):
    today = now.astimezone(DUBLIN).date()
    candidate = _dublin_wall(today, MORNING_SEND)
    if candidate <= now:
        candidate = _dublin_wall(today + timedelta(days=1), MORNING_SEND)
    return candidate


def _apply_quiet_hours(send, now):
    """Both arguments are UTC-aware. Returns a UTC-aware time outside quiet hours, never before now."""
    if not _is_quiet(send):
        return send
    local = send.astimezone(DUBLIN)
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    target = _dublin_wall(day, EVENING_SEND)
    if target >= now:
        return target
    if not _is_quiet(now):
        return now
    return _next_morning(now)


def _fmt_date(local):
    return f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"


def _sms_text(name, sig, date_s, time_s):
    first = name.split()[0] if name else ""
    for who in (name, first, ""):
        prefix = f"{who}, " if who else ""
        text = f"Brennan Opticians: {prefix}appointment {date_s} at {time_s} (Dublin time). {sig}"
        if len(text) <= SMS_LIMIT:
            return text
    return None


def _email_text(name, sig, date_s, time_s):
    greeting = f"Dear {name}," if name else "Hello,"
    return (
        f"{greeting}\n\n"
        f"This is a reminder of your appointment at Brennan Opticians on {date_s} at {time_s} (Dublin time).\n\n"
        f"{sig}"
    )


def _choose_message(appt, starts_local):
    name = str(appt.get("customer_name") or "").strip()
    phone = str(appt.get("phone") or "").strip()
    email = str(appt.get("email") or "").strip()
    opted_out = bool(appt.get("optout_sms_v2", False))
    country = str(appt.get("country") or "").strip().upper()
    sig = SIGNATURE_PL if country == "PL" else SIGNATURE
    date_s = _fmt_date(starts_local)
    time_s = starts_local.strftime("%H:%M")
    if phone and not opted_out:
        sms = _sms_text(name, sig, date_s, time_s)
        if sms is not None:
            return "sms", sms
    if email:
        return "email", _email_text(name, sig, date_s, time_s)
    return None, None


def _plan_one(appt, now):
    appt_id = appt["id"]
    if str(appt.get("status") or "").strip().lower() == "cancelled":
        return []
    starts = appt["starts_at"].astimezone(UTC)
    if starts <= now:
        return []
    channel, text = _choose_message(appt, starts.astimezone(DUBLIN))
    if channel is None:
        logger.info("no usable channel appointment_id=%s", appt_id)
        return []
    first = _apply_quiet_hours(max(starts - FIRST_OFFSET, now), now)
    second = _apply_quiet_hours(max(starts - SECOND_OFFSET, now), now)
    sends = [second] if first == second else [first, second]
    return [
        {"appointment_id": appt_id, "channel": channel, "send_at": s, "text": text}
        for s in sends
        if now <= s < starts
    ]


def plan_reminders(appointments, now):
    if _naive(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        if _naive(appt["starts_at"]):
            raise ValueError(f"starts_at must be timezone-aware (appointment_id={appt['id']})")
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    for r in planned:
        logger.info(
            "planned reminder appointment_id=%s channel=%s send_at=%s",
            r["appointment_id"], r["channel"], r["send_at"].isoformat(),
        )
    return planned


# ---------------------------------------------------------------- tests

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def _appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": "Anna Murphy",
        "email": "anna@example.com",
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 11, 2, 10, 0, tzinfo=DUBLIN),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


def _sends(out):
    return [r["send_at"] for r in out]


class ReminderTests(unittest.TestCase):

    def test_r2_reads_only_optout_sms_v2(self):
        out = plan_reminders([_appt(optout_sms_v2=False, opt_out=True)], NOW)
        self.assertEqual({r["channel"] for r in out}, {"sms"})
        out = plan_reminders([_appt(optout_sms_v2=True, opt_out=False)], NOW)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_r3_offsets_48h_and_2h(self):
        out = plan_reminders([_appt()], NOW)
        self.assertEqual(
            _sends(out),
            [datetime(2026, 10, 31, 10, 0, tzinfo=UTC), datetime(2026, 11, 2, 8, 0, tzinfo=UTC)],
        )

    def test_r4_r5_past_48h_sends_at_now(self):
        now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        out = plan_reminders([_appt()], now)
        self.assertEqual(_sends(out), [now, datetime(2026, 11, 2, 8, 0, tzinfo=UTC)])
        self.assertTrue(all(s >= now for s in _sends(out)))

    def test_r20_both_due_now_keeps_only_second(self):
        now = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
        out = plan_reminders([_appt()], now)
        self.assertEqual(_sends(out), [now])

    def test_r6_sms_when_allowed_email_when_opted_out(self):
        out = plan_reminders([_appt()], NOW)
        self.assertEqual({r["channel"] for r in out}, {"sms"})
        out = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_r6_r18_no_channel_produces_nothing(self):
        out = plan_reminders([_appt(optout_sms_v2=True, email="")], NOW)
        self.assertEqual(out, [])

    def test_r7_sms_within_limit_keeps_date_and_time(self):
        out = plan_reminders([_appt(customer_name="A" * 200)], NOW)
        sms = [r for r in out if r["channel"] == "sms"]
        self.assertTrue(sms)
        for r in sms:
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("02 Nov 2026", r["text"])
            self.assertIn("10:00", r["text"])

    def test_r8_evening_move_21h_to_20h_same_day(self):
        starts = datetime(2026, 11, 2, 23, 30, tzinfo=DUBLIN)
        out = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertEqual(
            _sends(out),
            [datetime(2026, 10, 31, 20, 0, tzinfo=UTC), datetime(2026, 11, 2, 20, 0, tzinfo=UTC)],
        )

    def test_r8_early_morning_move_to_previous_evening(self):
        starts = datetime(2026, 11, 3, 7, 0, tzinfo=DUBLIN)
        out = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertIn(datetime(2026, 11, 2, 20, 0, tzinfo=UTC), _sends(out))
        self.assertTrue(all(not (r["send_at"].astimezone(DUBLIN).hour >= 21
                                 or r["send_at"].astimezone(DUBLIN).hour < 8) for r in out))

    def test_r8_boundary_0800_not_moved(self):
        starts = datetime(2026, 11, 3, 10, 0, tzinfo=DUBLIN)
        out = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertIn(datetime(2026, 11, 3, 8, 0, tzinfo=UTC), _sends(out))

    def test_r8_dst_transition_day(self):
        # DST ends 2026-10-25 at 01:00 UTC. The 2h send falls at 05:30 GMT on 26 Oct,
        # moves to 20:00 on 25 Oct, which is GMT (UTC+0).
        starts = datetime(2026, 10, 26, 7, 30, tzinfo=DUBLIN)
        out = plan_reminders([_appt(starts_at=starts)], NOW)
        self.assertEqual(
            _sends(out),
            [datetime(2026, 10, 24, 7, 30, tzinfo=UTC), datetime(2026, 10, 25, 20, 0, tzinfo=UTC)],
        )

    def test_r9_cancelled_produces_nothing(self):
        self.assertEqual(plan_reminders([_appt(status="cancelled")], NOW), [])

    def test_r11_signature_default_and_pl(self):
        out = plan_reminders([_appt()], NOW)
        self.assertTrue(all(r["text"].endswith("Chevonne Nee Divver") for r in out))
        out = plan_reminders([_appt(country="pl", optout_sms_v2=True)], NOW)
        self.assertTrue(out)
        self.assertTrue(all(r["text"].endswith("Grzegorz Szczepański") for r in out))

    def test_r12_date_and_time_format(self):
        out = plan_reminders([_appt()], NOW)
        self.assertTrue(all("02 Nov 2026" in r["text"] and "10:00" in r["text"]
                            for r in out if r["channel"] == "sms"))

    def test_r14_sorted_by_send_at_then_id(self):
        out = plan_reminders([_appt(id="B"), _appt(id="A")], NOW)
        self.assertEqual([r["appointment_id"] for r in out], ["A", "B", "A", "B"])
        self.assertEqual(out, sorted(out, key=lambda r: (r["send_at"], r["appointment_id"])))

    def test_r19_started_appointment_produces_nothing(self):
        starts = datetime(2026, 10, 20, 12, 0, tzinfo=DUBLIN)
        self.assertEqual(plan_reminders([_appt(starts_at=starts)], NOW), [])

    def test_r24_empty_and_naive_inputs(self):
        self.assertEqual(plan_reminders([], NOW), [])
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 20, 12, 0))
        with self.assertRaises(ValueError):
            plan_reminders([_appt(starts_at=datetime(2026, 11, 2, 10, 0))], NOW)

    def test_r25_output_keys_exact(self):
        out = plan_reminders([_appt()], NOW)
        self.assertTrue(out)
        for r in out:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})

    def test_r10_no_personal_data_in_logs(self):
        appt = _appt(id="Z9", customer_name="Secret Person",
                     email="secret.person@example.com", phone="+353871234567")
        with self.assertLogs(logger, level="INFO") as cm:
            out = plan_reminders([appt], NOW)
        self.assertTrue(out)
        joined = "\n".join(cm.output)
        for secret in ("secret.person@example.com", "+353871234567", "Secret Person", "Secret", "Person"):
            self.assertNotIn(secret, joined)
        self.assertIn("Z9", joined)


if __name__ == "__main__":
    unittest.main()