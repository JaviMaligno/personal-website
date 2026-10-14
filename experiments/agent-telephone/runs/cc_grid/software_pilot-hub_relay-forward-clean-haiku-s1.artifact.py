"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now). Standard library only, Python 3.12.
"""
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
QUIET_START_HOUR = 21  # 21:00 Dublin local
MORNING_HOUR = 8       # 08:00 Dublin local
EVENING_HOUR = 20      # 20:00 Dublin local


def _require_aware(dt, what):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} must be timezone-aware")


def _apply_quiet_hours(send_at, now):
    """Move a send time out of the 21:00-08:00 Dublin quiet window.

    21:00-23:59 moves to 20:00 the same date; 00:00-07:59 moves to 20:00 the
    previous date. Conversion to UTC is done with the Dublin zone, so DST is
    handled by zoneinfo.

    ASSUMPTION Q1: if the shifted time is already in the past, use 08:00 Dublin
    the next morning instead. This is a known conflict with the brief's
    'never return a send_at in the past' rule; flagged for the client.
    """
    local = send_at.astimezone(DUBLIN)
    if MORNING_HOUR <= local.hour < QUIET_START_HOUR:
        return send_at
    if local.hour >= QUIET_START_HOUR:
        evening_date = local.date()
    else:
        evening_date = local.date() - timedelta(days=1)
    shifted = datetime.combine(evening_date, time(EVENING_HOUR), tzinfo=DUBLIN).astimezone(UTC)
    if shifted >= now:
        return shifted
    # ASSUMPTION Q1: shifted time is already past, use 08:00 the next morning.
    return datetime.combine(
        evening_date + timedelta(days=1), time(MORNING_HOUR), tzinfo=DUBLIN
    ).astimezone(UTC)


def _body(starts_at, country):
    local = starts_at.astimezone(DUBLIN)
    # ASSUMPTION Q7: simple date format, e.g. "Tuesday 14 October", and HH:MM.
    date_s = f"{local:%A} {local.day} {local:%B}"
    time_s = f"{local:%H:%M}"
    sig = SIG_PL if (country or "").strip().upper() == "PL" else SIG_DEFAULT
    return f"Brennan Opticians: your appointment is {date_s} at {time_s}. {sig}"


def _sms_text(full_name, body):
    """Return the SMS text, shortening the name as needed, or None if it cannot fit.

    ASSUMPTION Q8: length counted in Python characters.
    Shortening order: full name, then first name only, then no name.
    Date, time and signature are never removed.
    """
    parts = full_name.split()
    first = parts[0] if parts else ""
    for name in (full_name, first, ""):
        text = (f"Hi {name}, " if name else "") + body
        if len(text) <= SMS_LIMIT:
            return text
    return None


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    now = now.astimezone(UTC)
    planned = []

    for a in appointments:
        appt_id = a["id"]
        starts_at = a["starts_at"]
        _require_aware(starts_at, "starts_at")

        # ASSUMPTION Q6: only the exact lowercase value "cancelled" is skipped.
        if a.get("status") == "cancelled":
            continue
        if starts_at <= now:
            continue

        full_name = (a.get("customer_name") or "").strip()
        phone = (a.get("phone") or "").strip()
        email = (a.get("email") or "").strip()
        # Only the v2 field is read. Missing or null counts as opted out.
        opt = a.get("optout_sms_v2")
        sms_ok = bool(phone) and opt is not None and not opt

        if sms_ok:
            channel = "sms"
        elif email:
            channel = "email"
        else:
            # ASSUMPTION: no usable channel, so nothing is planned.
            log.warning("no usable contact channel appointment_id=%s", appt_id)
            continue

        # Schedule: 48h and 2h points are absolute UTC durations.
        t48 = starts_at - timedelta(hours=48)
        t2 = starts_at - timedelta(hours=2)
        if t2 > now:
            # Catch-up: if the 48h point has passed, the first reminder goes at now.
            times = [now if t48 <= now else t48, t2]
        else:
            # ASSUMPTION Q2: both points have passed, so send only the 2h reminder, at now.
            times = [now]

        body = _body(starts_at, a.get("country"))
        for raw_send_at in times:
            send_at = _apply_quiet_hours(raw_send_at, now)
            # ASSUMPTION: a reminder that would go out at or after the appointment is not sent.
            if send_at >= starts_at:
                continue

            if channel == "sms":
                text = _sms_text(full_name, body)
                if text is None:
                    log.warning("sms too long, not emitted appointment_id=%s", appt_id)
                    continue
            else:
                # Email has no length limit.
                text = (f"Hi {full_name}, " if full_name else "") + body

            planned.append({
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            # Contact (phone/email) is deliberately not logged, per the DPC audit
            # and the no-customer-data rule. The appointment ID is the recipient reference.
            log.info("planned reminder appointment_id=%s channel=%s", appt_id, channel)

    planned.sort(key=lambda r: (r["send_at"], r["appointment_id"]))
    return planned


class PlanRemindersTests(unittest.TestCase):
    NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
    EMAIL = "ann@example.com"

    def appt(self, **overrides):
        base = {
            "id": "A1",
            "customer_name": "Ann Murphy",
            "email": self.EMAIL,
            "phone": "+353850000000",
            "country": "IE",
            "status": "booked",
            "starts_at": datetime(2026, 10, 16, 10, 0, tzinfo=DUBLIN),
            "optout_sms_v2": False,
        }
        base.update(overrides)
        return base

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 12, 0))

    def test_naive_starts_at_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([self.appt(starts_at=datetime(2026, 10, 16, 10, 0))], self.NOW)

    def test_cancelled_skipped(self):
        self.assertEqual(plan_reminders([self.appt(status="cancelled")], self.NOW), [])

    def test_optout_v2_routes_to_email(self):
        out = plan_reminders([self.appt(optout_sms_v2=True, opt_out=False)], self.NOW)
        self.assertTrue(out)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_missing_optout_v2_routes_to_email(self):
        appt = self.appt()
        del appt["optout_sms_v2"]
        out = plan_reminders([appt], self.NOW)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_pl_signature(self):
        out = plan_reminders([self.appt(country="pl")], self.NOW)
        self.assertTrue(out)
        self.assertTrue(all(r["text"].endswith(SIG_PL) for r in out))

    def test_sms_length_cut(self):
        long_first = "Maximilian " + "Z" * 200
        out = plan_reminders([self.appt(customer_name=long_first)], self.NOW)
        self.assertTrue(out)
        for r in out:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("Hi Maximilian,", r["text"])
            self.assertIn("16 October at 10:00", r["text"])
            self.assertTrue(r["text"].endswith(SIG_DEFAULT))

        single = "Q" * 200
        out = plan_reminders([self.appt(customer_name=single)], self.NOW)
        for r in out:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertTrue(r["text"].startswith("Brennan"))
            self.assertIn("16 October at 10:00", r["text"])

    def test_quiet_hours_shift(self):
        # 14 Oct 08:30 Dublin. The 2h point is 07:30 local, inside quiet hours,
        # so it moves to 20:00 on 13 Oct Dublin (19:00 UTC).
        appt = self.appt(starts_at=datetime(2026, 10, 14, 8, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], self.NOW)
        self.assertEqual(
            [r["send_at"] for r in out],
            [self.NOW, datetime(2026, 10, 13, 19, 0, tzinfo=UTC)],
        )

    def test_catch_up_at_now(self):
        # The 48h and 2h points have both passed, so one reminder is sent at now.
        appt = self.appt(starts_at=datetime(2026, 10, 13, 14, 0, tzinfo=UTC))
        out = plan_reminders([appt], self.NOW)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], self.NOW)

    def test_quiet_hours_past_shift_uses_next_morning(self):
        # Q1 default: now is 22:30 Dublin, so the catch-up time is quiet and its 20:00
        # shift is already past. The reminder moves to 08:00 on 14 Oct Dublin (07:00 UTC).
        now = datetime(2026, 10, 13, 21, 30, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 14, 15, 0, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(out[0]["send_at"], datetime(2026, 10, 14, 7, 0, tzinfo=UTC))

    def test_dst_date(self):
        # 25 Oct 2026 is the Dublin DST change date.
        now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 25, 10, 0, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[1]["send_at"], datetime(2026, 10, 25, 8, 0, tzinfo=UTC))
        for r in out:
            self.assertIn("Sunday 25 October at 10:00", r["text"])

    def test_sorting_and_tie_break(self):
        appts = [self.appt(id="b"), self.appt(id="a")]
        out = plan_reminders(appts, self.NOW)
        self.assertEqual([r["appointment_id"] for r in out], ["a", "b", "a", "b"])
        times = [r["send_at"] for r in out]
        self.assertEqual(times, sorted(times))

    def test_no_email_in_logs_or_output(self):
        with self.assertLogs(log, level="INFO") as cm:
            out = plan_reminders([self.appt()], self.NOW)
        self.assertTrue(out)
        self.assertNotIn(self.EMAIL, "\n".join(cm.output))
        self.assertNotIn(self.EMAIL, repr(out))
        self.assertNotIn("+353850000000", "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()