# reminders.py
```python
"""Appointment reminder planning for Brennan Opticians.

Pure planning: plan_reminders() returns reminder dicts and sends nothing.

Decisions for the client to confirm:
- The second reminder is 2 hours before the appointment (assumption).
- Dates are DD/MM/YYYY and times are HH:MM, both Europe/Dublin local.
- Cancelled matching is exact and case-sensitive.
- The Polish signature applies only when country is exactly "PL".
- Reminders that would share a send_at and channel for the same appointment collapse to one.
- A missing or null optout_sms_v2 counts as not opted out. Any truthy value counts as opted out.
- Logging: one INFO line per planned reminder with appointment_id, channel and contact kind
  ("phone" or "email"). No contact values, names or message texts are logged.
- If an SMS cannot fit in 160 characters even without a name, the shortest text is returned
  and a WARNING with appointment_id is logged.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_LEN = 160
FIRST_LEAD = timedelta(hours=48)
SECOND_LEAD = timedelta(hours=2)
QUIET_END = time(8, 0)
QUIET_START = time(21, 0)
EVENING_SEND = time(20, 0)
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"


def _check_aware(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _dublin_to_utc(day, t):
    return datetime.combine(day, t, tzinfo=DUBLIN).astimezone(UTC)


def _permitted(dt):
    t = dt.astimezone(DUBLIN).time()
    return QUIET_END <= t < QUIET_START


def _next_permitted(now):
    if _permitted(now):
        return now
    local = now.astimezone(DUBLIN)
    day = local.date() if local.time() < QUIET_END else local.date() + timedelta(days=1)
    return _dublin_to_utc(day, QUIET_END)


def _apply_quiet_window(send_at, now):
    if _permitted(send_at):
        return send_at
    local = send_at.astimezone(DUBLIN)
    if local.time() >= QUIET_START:
        evening = local.date()
    else:
        evening = local.date() - timedelta(days=1)
    evening_send = _dublin_to_utc(evening, EVENING_SEND)
    if evening_send >= now:
        return evening_send
    return _next_permitted(now)


def _choose_channel(appt):
    phone = (appt.get("phone") or "").strip()
    email = (appt.get("email") or "").strip()
    if appt.get("optout_sms_v2"):
        return "email" if email else None
    if phone:
        return "sms"
    if email:
        return "email"
    return None


def _signature(country):
    return PL_SIGNATURE if country == "PL" else DEFAULT_SIGNATURE


def _body(name, date_s, time_s, signature):
    greeting = f"Hi {name}, " if name else "Hi, "
    return f"{greeting}reminder of your appointment at Brennan Opticians on {date_s} at {time_s}. {signature}"


def _name_options(full_name):
    options = []
    if full_name:
        options.append(full_name)
        parts = full_name.split()
        if len(parts) >= 2:
            options.append(f"{parts[0]} {parts[-1][0]}.")
    options.append("")
    return options


def _build_text(channel, full_name, starts_local, signature):
    date_s = starts_local.strftime("%d/%m/%Y")
    time_s = starts_local.strftime("%H:%M")
    if channel == "email":
        return _body(full_name, date_s, time_s, signature), True
    for name in _name_options(full_name):
        text = _body(name, date_s, time_s, signature)
        if len(text) <= SMS_MAX_LEN:
            return text, True
    return _body("", date_s, time_s, signature), False


def plan_reminders(appointments, now):
    _check_aware(now, "now")
    planned = []
    for appt in appointments:
        starts_at = appt["starts_at"]
        _check_aware(starts_at, "starts_at")
        appt_id = appt["id"]

        if appt.get("status") == "cancelled":
            continue
        if starts_at <= now:
            continue

        channel = _choose_channel(appt)
        if channel is None:
            continue

        full_name = (appt.get("customer_name") or "").strip()
        signature = _signature(appt.get("country"))
        starts_local = starts_at.astimezone(DUBLIN)
        text, fits = _build_text(channel, full_name, starts_local, signature)
        if channel == "sms" and not fits:
            logger.warning("SMS exceeds %d characters even without name appointment_id=%s",
                           SMS_MAX_LEN, appt_id)

        candidates = [
            max(starts_at - FIRST_LEAD, now),
            max(starts_at - SECOND_LEAD, now),
        ]
        seen = set()
        contact_kind = "phone" if channel == "sms" else "email"
        for candidate in candidates:
            send_at = _apply_quiet_window(candidate, now)
            if send_at in seen:
                continue
            seen.add(send_at)
            planned.append({
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            logger.info("reminder planned appointment_id=%s channel=%s contact=%s send_at=%s",
                        appt_id, channel, contact_kind, send_at.isoformat())

    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned
```

# test_reminders.py
```python
# Not executed in this session. Run with: python -m unittest test_reminders
import logging
import unittest
from datetime import datetime, timezone

from reminders import DUBLIN, plan_reminders

UTC = timezone.utc
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": "aoife@example.com",
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 10, 14, 8, 30, tzinfo=DUBLIN),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


class PlanRemindersTests(unittest.TestCase):

    def test_example_two_reminders(self):
        out = plan_reminders([appt()], NOW)
        self.assertEqual([r["send_at"] for r in out], [
            datetime(2026, 10, 13, 12, 0, tzinfo=UTC),
            datetime(2026, 10, 13, 19, 0, tzinfo=UTC),
        ])
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_cancelled_returns_empty(self):
        self.assertEqual(plan_reminders([appt(status="cancelled")], NOW), [])

    def test_cancelled_match_is_case_sensitive(self):
        out = plan_reminders([appt(status="Cancelled")], NOW)
        self.assertEqual(len(out), 2)

    def test_optout_with_email_sends_email_only(self):
        out = plan_reminders([appt(optout_sms_v2=True)], NOW)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_optout_without_email_returns_nothing(self):
        out = plan_reminders([appt(optout_sms_v2=True, email="")], NOW)
        self.assertEqual(out, [])

    def test_no_phone_sends_email_only(self):
        out = plan_reminders([appt(phone="")], NOW)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_no_phone_and_no_email_returns_nothing(self):
        out = plan_reminders([appt(phone=None, email=None)], NOW)
        self.assertEqual(out, [])

    def test_null_optout_counts_as_not_opted_out(self):
        out = plan_reminders([appt(optout_sms_v2=None)], NOW)
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_sms_length_and_content_with_long_name(self):
        long_name = " ".join(["Bartholomewson"] * 6)
        out = plan_reminders([appt(customer_name=long_name)], NOW)
        self.assertTrue(out)
        for r in out:
            self.assertEqual(r["channel"], "sms")
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("14/10/2026", r["text"])
            self.assertIn("08:30", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_email_keeps_full_name_without_limit(self):
        long_name = " ".join(["Bartholomewson"] * 6)
        out = plan_reminders([appt(customer_name=long_name, optout_sms_v2=True)], NOW)
        self.assertIn(long_name, out[0]["text"])

    def test_polish_signature(self):
        out = plan_reminders([appt(country="PL")], NOW)
        self.assertTrue(all(r["text"].endswith("Grzegorz Szczepański") for r in out))

    def test_no_send_before_now(self):
        starts = datetime(2026, 10, 13, 20, 0, tzinfo=DUBLIN)
        out = plan_reminders([appt(starts_at=starts)], NOW)
        for r in out:
            self.assertGreaterEqual(r["send_at"], NOW)

    def test_past_appointment_skipped(self):
        starts = datetime(2026, 10, 13, 11, 0, tzinfo=UTC)
        self.assertEqual(plan_reminders([appt(starts_at=starts)], NOW), [])

    def test_quiet_window_evening_rule(self):
        starts = datetime(2026, 10, 15, 22, 0, tzinfo=DUBLIN)
        out = plan_reminders([appt(starts_at=starts)], NOW)
        self.assertEqual([r["send_at"] for r in out], [
            datetime(2026, 10, 13, 19, 0, tzinfo=UTC),
            datetime(2026, 10, 15, 19, 0, tzinfo=UTC),
        ])

    def test_quiet_window_next_permitted_when_evening_passed(self):
        now = datetime(2026, 10, 13, 20, 30, tzinfo=UTC)  # 21:30 Dublin
        starts = datetime(2026, 10, 14, 6, 0, tzinfo=DUBLIN)
        out = plan_reminders([appt(starts_at=starts)], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], datetime(2026, 10, 14, 7, 0, tzinfo=UTC))

    def test_no_send_in_quiet_window(self):
        for hour in range(24):
            starts = datetime(2026, 10, 20, hour, 0, tzinfo=DUBLIN)
            out = plan_reminders([appt(starts_at=starts)], NOW)
            for r in out:
                t = r["send_at"].astimezone(DUBLIN).time()
                self.assertFalse(t >= datetime(2000, 1, 1, 21).time() or t < datetime(2000, 1, 1, 8).time(),
                                 f"send_at {r['send_at']} in quiet window")

    def test_duplicate_send_at_collapses_to_one(self):
        starts = datetime(2026, 10, 13, 14, 0, tzinfo=DUBLIN)
        out = plan_reminders([appt(starts_at=starts)], NOW)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], NOW)

    def test_sorted_output(self):
        appts = [
            appt(id="B", starts_at=datetime(2026, 10, 16, 10, 0, tzinfo=DUBLIN)),
            appt(id="A", starts_at=datetime(2026, 10, 14, 8, 30, tzinfo=DUBLIN)),
            appt(id="C", starts_at=datetime(2026, 10, 15, 15, 0, tzinfo=DUBLIN)),
        ]
        out = plan_reminders(appts, NOW)
        keys = [(r["send_at"], str(r["appointment_id"]), r["channel"]) for r in out]
        self.assertEqual(keys, sorted(keys))

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([appt()], datetime(2026, 10, 13, 12, 0))

    def test_naive_starts_at_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([appt(starts_at=datetime(2026, 10, 14, 8, 30))], NOW)

    def test_no_contact_data_in_logs(self):
        a = appt(email="secret.person@example.com", phone="+353871234567", optout_sms_v2=True)
        with self.assertLogs(level=logging.DEBUG) as cm:
            out = plan_reminders([a], NOW)
        text = "\n".join(cm.output)
        self.assertNotIn("secret.person@example.com", text)
        self.assertNotIn("+353871234567", text)
        self.assertNotIn("Aoife", text)
        info = [r for r in cm.records if r.levelno == logging.INFO]
        self.assertEqual(len(info), len(out))


if __name__ == "__main__":
    unittest.main()
```