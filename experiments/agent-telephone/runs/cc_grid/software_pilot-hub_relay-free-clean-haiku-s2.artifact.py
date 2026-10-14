"""Appointment reminder planner for Brennan Opticians.

Single entry point: plan_reminders(appointments, now).

Output: list of dicts with appointment_id, channel ("sms" or "email"),
send_at (timezone-aware UTC datetime) and text, sorted by send_at.

AMBIGUITY CHOICES (conservative defaults; change them in this block only):
 1. Date text is "14 Oct 2026" (English, unambiguous); time is HH:MM Dublin local.
 2. If a quiet-hour shift would land before now, defer to 08:00 Dublin on the
    next morning if that is not in the past; otherwise skip the reminder.
 3. If the 2-hour point has passed but the appointment has not started, skip
    the 2-hour reminder (no late sends).
 4. If the 48-hour point has passed, the first reminder is sent at now (still
    subject to quiet hours); the 2-hour reminder is still sent if it is future.
 5. Channel: SMS if phone present and optout_sms_v2 is false; otherwise email
    if an email is present; otherwise no reminder. Never both.
 6. Any status other than "cancelled" (case-insensitive) is treated as active.
 7. Naive datetimes for now or starts_at raise ValueError.
 8. SMS name shortening order: full name, first name, first name truncated with
    an ellipsis, then no name at all. Length counted in Python characters.
 9. Appointments with starts_at <= now produce no reminders.
10. Any send at or after starts_at is dropped (only possible via deferral).
11. Email messages are not length-limited and use the full customer name.
12. Log lines carry appointment_id and a masked contact (last 4 digits of the
    phone for SMS; "email-on-file (redacted)" for email). No email address,
    name, or message text is logged.
13. Output send_at values are UTC. All arithmetic is done in UTC so that DST
    transitions do not shift the 48-hour and 2-hour offsets.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_CHARS = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
EVENING_SEND = time(20, 0)
MORNING_DEFER = time(8, 0)
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
ELLIPSIS = "\u2026"
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _require_aware(dt, what):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")


def _choose_channel(appt):
    phone = str(appt.get("phone") or "").strip()
    email = str(appt.get("email") or "").strip()
    opted_out = bool(appt.get("optout_sms_v2"))
    if phone and not opted_out:
        return "sms", phone
    if email:
        return "email", email
    return None


def _apply_quiet(raw_utc, now_utc, starts_utc):
    """Return the allowed send instant (UTC) or None to skip."""
    local = raw_utc.astimezone(DUBLIN)
    t = local.time()
    if QUIET_END <= t < QUIET_START:
        send = raw_utc
    else:
        if t >= QUIET_START:
            evening_day = local.date()
            morning_day = evening_day + timedelta(days=1)
        else:
            evening_day = local.date() - timedelta(days=1)
            morning_day = local.date()
        send = datetime.combine(evening_day, EVENING_SEND, tzinfo=DUBLIN).astimezone(UTC)
        if send < now_utc:
            send = datetime.combine(morning_day, MORNING_DEFER, tzinfo=DUBLIN).astimezone(UTC)
            if send < now_utc:
                return None
    if send < now_utc or send >= starts_utc:
        return None
    return send


def _fmt_date(local):
    return f"{local.day} {_MONTHS[local.month - 1]} {local.year}"


def _fmt_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def _signature(country):
    return SIG_PL if str(country or "").strip().upper() == "PL" else SIG_DEFAULT


def _sms_text(name, date_s, time_s, sig):
    def render(who):
        greet = f"Hi {who}. " if who else ""
        return (f"{greet}Brennan Opticians reminder: your appointment is on "
                f"{date_s} at {time_s} (Dublin time). {sig}")

    full = render(name)
    if len(full) <= SMS_MAX_CHARS:
        return full
    parts = name.split()
    first = parts[0] if parts else ""
    if first:
        short = render(first)
        if len(short) <= SMS_MAX_CHARS:
            return short
        for n in range(len(first) - 1, 0, -1):
            cand = render(first[:n] + ELLIPSIS)
            if len(cand) <= SMS_MAX_CHARS:
                return cand
    return render("")


def _email_text(name, date_s, time_s, sig):
    return (f"Hi {name or 'there'},\n"
            f"This is a reminder of your Brennan Opticians appointment on "
            f"{date_s} at {time_s} (Dublin time).\n{sig}")


def _mask(channel, address):
    if channel == "sms":
        return "***" + address[-4:]
    return "email-on-file (redacted)"


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    now_utc = now.astimezone(UTC)
    out = []

    for appt in appointments:
        aid = appt.get("id")
        if str(appt.get("status") or "").strip().lower() == "cancelled":
            continue

        starts = appt.get("starts_at")
        _require_aware(starts, f"starts_at of appointment {aid!r}")
        starts_utc = starts.astimezone(UTC)
        if starts_utc <= now_utc:
            continue

        contact = _choose_channel(appt)
        if contact is None:
            continue
        channel, address = contact

        local = starts_utc.astimezone(DUBLIN)
        date_s, time_s = _fmt_date(local), _fmt_time(local)
        sig = _signature(appt.get("country"))
        name = str(appt.get("customer_name") or "").strip()

        # 2-hour reminder is planned first (higher priority), then 48-hour.
        raw_candidates = []
        second_raw = starts_utc - SECOND_OFFSET
        if second_raw >= now_utc:
            raw_candidates.append(second_raw)
        first_raw = starts_utc - FIRST_OFFSET
        raw_candidates.append(first_raw if first_raw >= now_utc else now_utc)

        for raw in raw_candidates:
            send = _apply_quiet(raw, now_utc, starts_utc)
            if send is None:
                continue
            if channel == "sms":
                text = _sms_text(name, date_s, time_s, sig)
            else:
                text = _email_text(name, date_s, time_s, sig)
            out.append({"appointment_id": aid, "channel": channel,
                        "send_at": send, "text": text})
            log.info("reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                     aid, channel, _mask(channel, address), send.isoformat())

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    return out


# ---------------------------------------------------------------- tests

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
TEST_EMAIL = "customer.test@example.invalid"


def _appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": TEST_EMAIL,
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 10, 20, 10, 0, tzinfo=DUBLIN),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


class ReminderTests(unittest.TestCase):

    def sends(self, results, channel=None):
        return [r["send_at"] for r in results
                if channel is None or r["channel"] == channel]

    def test_two_hour_and_forty_eight_hour_reminders(self):
        res = plan_reminders([_appt()], NOW)
        self.assertEqual(self.sends(res), [
            datetime(2026, 10, 18, 9, 0, tzinfo=UTC),
            datetime(2026, 10, 20, 7, 0, tzinfo=UTC),
        ])
        self.assertTrue(all(r["channel"] == "sms" for r in res))

    def test_two_hour_reminder_is_correct_alone(self):
        now = datetime(2026, 10, 20, 6, 0, tzinfo=UTC)
        res = plan_reminders([_appt()], now)
        self.assertEqual(self.sends(res), [datetime(2026, 10, 20, 7, 0, tzinfo=UTC)])

    def test_dst_forty_eight_hours_is_absolute(self):
        # Clocks go back on 25 Oct 2026; 48 absolute hours before 26 Oct 10:00 GMT
        # is 24 Oct 10:00 UTC (11:00 IST), not 24 Oct 10:00 GMT wall-clock.
        appt = _appt(starts_at=datetime(2026, 10, 26, 10, 0, tzinfo=DUBLIN))
        res = plan_reminders([appt], datetime(2026, 10, 1, tzinfo=UTC))
        self.assertEqual(self.sends(res), [
            datetime(2026, 10, 24, 10, 0, tzinfo=UTC),
            datetime(2026, 10, 26, 8, 0, tzinfo=UTC),
        ])

    def test_quiet_hours_two_hour_at_2100_shifts_to_2000(self):
        appt = _appt(starts_at=datetime(2026, 10, 20, 23, 0, tzinfo=DUBLIN))
        res = plan_reminders([appt], NOW)
        self.assertIn(datetime(2026, 10, 20, 19, 0, tzinfo=UTC), self.sends(res))

    def test_quiet_hours_boundary_0800_not_shifted(self):
        appt = _appt(starts_at=datetime(2026, 10, 20, 10, 0, tzinfo=DUBLIN))
        now = datetime(2026, 10, 20, 6, 0, tzinfo=UTC)
        res = plan_reminders([appt], now)
        self.assertEqual(self.sends(res), [datetime(2026, 10, 20, 7, 0, tzinfo=UTC)])

    def test_quiet_hours_early_morning_shifts_to_previous_evening(self):
        appt = _appt(starts_at=datetime(2026, 10, 21, 8, 30, tzinfo=DUBLIN))
        res = plan_reminders([appt], NOW)
        self.assertIn(datetime(2026, 10, 20, 19, 0, tzinfo=UTC), self.sends(res))

    def test_quiet_shift_in_past_defers_to_morning(self):
        now = datetime(2026, 10, 20, 19, 30, tzinfo=UTC)  # 20:30 Dublin
        appt = _appt(starts_at=datetime(2026, 10, 21, 8, 30, tzinfo=DUBLIN))
        res = plan_reminders([appt], now)
        two_hour = [r["send_at"] for r in res
                    if r["send_at"] > datetime(2026, 10, 21, 0, 0, tzinfo=UTC)]
        self.assertEqual(two_hour, [datetime(2026, 10, 21, 7, 0, tzinfo=UTC)])

    def test_deferred_send_after_start_is_skipped(self):
        now = datetime(2026, 10, 20, 19, 30, tzinfo=UTC)
        appt = _appt(starts_at=datetime(2026, 10, 21, 7, 30, tzinfo=DUBLIN))
        res = plan_reminders([appt], now)
        self.assertFalse([r for r in res if r["send_at"] > datetime(2026, 10, 21, tzinfo=UTC)])

    def test_two_hour_passed_skips_it_and_sends_first_now(self):
        now = datetime(2026, 10, 20, 8, 30, tzinfo=UTC)  # 09:30 Dublin, start 10:00
        res = plan_reminders([_appt()], now)
        self.assertEqual(self.sends(res), [now])

    def test_cancelled_produces_nothing(self):
        self.assertEqual(plan_reminders([_appt(status="cancelled")], NOW), [])

    def test_polish_signature(self):
        res = plan_reminders([_appt(country="PL", customer_name="Anna Kowalska")], NOW)
        self.assertTrue(res)
        for r in res:
            self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))

    def test_irish_signature(self):
        res = plan_reminders([_appt()], NOW)
        self.assertTrue(all(r["text"].endswith("Siobhán Ní Dhuibhir") for r in res))

    def test_long_sms_keeps_date_and_time(self):
        name = "Maximilian Alexander Konstantinos Wolfgang Fitzgerald-Montgomery " * 3
        res = plan_reminders([_appt(customer_name=name)], NOW)
        self.assertTrue(res)
        for r in res:
            self.assertLessEqual(len(r["text"]), SMS_MAX_CHARS)
            self.assertIn("20 Oct 2026", r["text"])
            self.assertIn("10:00", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_opted_out_without_email_gets_nothing(self):
        appt = _appt(optout_sms_v2=True, email=None)
        self.assertEqual(plan_reminders([appt], NOW), [])

    def test_opted_out_with_email_gets_email(self):
        res = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertTrue(res)
        self.assertTrue(all(r["channel"] == "email" for r in res))

    def test_missing_phone_uses_email(self):
        res = plan_reminders([_appt(phone=None)], NOW)
        self.assertTrue(all(r["channel"] == "email" for r in res))

    def test_no_contact_gets_nothing(self):
        self.assertEqual(plan_reminders([_appt(phone=None, email=None)], NOW), [])

    def test_past_starts_at_gets_nothing(self):
        appt = _appt(starts_at=datetime(2026, 10, 1, 10, 0, tzinfo=DUBLIN))
        self.assertEqual(plan_reminders([appt], NOW), [])

    def test_sorted_by_send_at(self):
        appts = [
            _appt(id="late", starts_at=datetime(2026, 10, 30, 10, 0, tzinfo=DUBLIN)),
            _appt(id="early", starts_at=datetime(2026, 10, 15, 10, 0, tzinfo=DUBLIN)),
        ]
        res = plan_reminders(appts, NOW)
        times = [r["send_at"] for r in res]
        self.assertEqual(times, sorted(times))

    def test_naive_datetimes_raise(self):
        with self.assertRaises(ValueError):
            plan_reminders([_appt()], datetime(2026, 10, 10, 12, 0))
        with self.assertRaises(ValueError):
            plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 10, 0))], NOW)

    def test_no_customer_email_in_output_or_logs(self):
        with self.assertLogs(level="INFO") as cm:
            res = plan_reminders([_appt(phone=None)], NOW)
        self.assertTrue(res)
        self.assertNotIn(TEST_EMAIL, "\n".join(cm.output))
        self.assertNotIn(TEST_EMAIL, repr(res))


if __name__ == "__main__":
    unittest.main()