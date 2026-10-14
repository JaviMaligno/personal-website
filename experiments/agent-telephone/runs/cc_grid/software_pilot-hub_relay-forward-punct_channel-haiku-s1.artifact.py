"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now)

Defaults applied (for client confirmation):
1. Opt-out: SMS only when optout_sms_v2 is exactly False. True, None or a missing key means
   opted out, and opted-out customers get no reminder at all (no email either). The brief wording
   ("text them if optout_sms_v2 is true") reads the other way; the spec default is followed here.
2. Email fallback: only when not opted out, there is no usable phone number, and there is a usable email.
3. Appointments with starts_at <= now are skipped.
4. Conflict resolution: the spec's catch-up rule (send at now when the 48h point has passed) would send
   a reminder for an appointment 1 hour away, which contradicts the acceptance criterion. Catch-up and
   2h reminders are therefore only planned when the 2h point is still in the future. An appointment
   less than or equal to 2 hours away gets no reminder.
5. Quiet hours: when the candidate is in the window and now is also in the window, the reminder is
   deferred to the next 08:00 Dublin time.
6. Not in spec: any send time at or after the appointment start is dropped.
7. Not in spec: duplicate sends for the same appointment and time (for example, catch-up and deferral
   landing on the same instant) are collapsed to one.
8. Logging: one INFO line per planned reminder with appointment_id and channel only. The house rule
   asks for the contact as well, but phone numbers and email addresses must not be logged (DPC audit),
   so recipients are identified by appointment id and no contact detail is logged.
9. SMS shortening order: full name, first name, first initial with period, no name. Email uses the full
   name with no length limit.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
LEAD_48 = timedelta(hours=48)
LEAD_2 = timedelta(hours=2)


def _aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _text_field(value):
    return value.strip() if isinstance(value, str) else ""


def _in_quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _dublin_at(day, hour):
    return datetime.combine(day, time(hour, 0), tzinfo=DUBLIN).astimezone(UTC)


def _quiet_adjust(send, now):
    local = send.astimezone(DUBLIN)
    if not _in_quiet(local):
        return send
    now_local = now.astimezone(DUBLIN)
    if _in_quiet(now_local):
        day = now_local.date() if now_local.hour < QUIET_END.hour else now_local.date() + timedelta(days=1)
        return _dublin_at(day, QUIET_END.hour)
    day = local.date() if local.hour >= QUIET_START.hour else local.date() - timedelta(days=1)
    return _dublin_at(day, 20)


def _name_variants(full):
    parts = full.split()
    if not parts:
        return [""]
    options = [" ".join(parts), parts[0], parts[0][0] + ".", ""]
    unique = []
    for option in options:
        if option not in unique:
            unique.append(option)
    return unique


def _message(name, starts_local, signature):
    when = f"{starts_local.day:02d} {MONTHS[starts_local.month - 1]} {starts_local.year}"
    hhmm = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    greeting = f"Hi {name}, " if name else "Hi, "
    return f"{greeting}reminder of your Brennan Opticians appointment on {when} at {hhmm}. {signature}"


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)

    indexed = []
    for appt in appointments:
        if not _aware(appt.get("starts_at")):
            raise ValueError(
                f"appointment {appt.get('id')!s}: starts_at must be a timezone-aware datetime")
        indexed.append((appt, appt["starts_at"].astimezone(UTC)))

    plans = []
    seen = set()
    for idx, (appt, starts) in enumerate(indexed):
        appt_id = appt.get("id")

        if str(appt.get("status", "")).strip().lower() == "cancelled":
            continue
        if starts <= now_utc:
            continue
        if appt.get("optout_sms_v2") is not False:
            continue

        if _text_field(appt.get("phone")):
            channel = "sms"
        elif _text_field(appt.get("email")):
            channel = "email"
        else:
            continue

        t2 = starts - LEAD_2
        if t2 <= now_utc:
            continue
        t48 = starts - LEAD_48
        first = t48 if t48 > now_utc else now_utc

        starts_local = starts.astimezone(DUBLIN)
        signature = SIGNATURE_PL if _text_field(appt.get("country")).lower() == "pl" else SIGNATURE
        name = _text_field(appt.get("customer_name"))

        if channel == "email":
            text = _message(name, starts_local, signature)
        else:
            text = None
            for variant in _name_variants(name):
                candidate = _message(variant, starts_local, signature)
                if len(candidate) <= SMS_LIMIT:
                    text = candidate
                    break
            if text is None:
                raise ValueError(
                    f"appointment {appt_id!s}: SMS text cannot fit in {SMS_LIMIT} characters")

        for raw_send in (first, t2):
            send = max(_quiet_adjust(raw_send, now_utc), now_utc)
            if send >= starts:
                continue
            key = (idx, send)
            if key in seen:
                continue
            seen.add(key)
            plans.append({
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send,
                "text": text,
            })
            log.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                     appt_id, channel, send.isoformat())

    plans.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return plans


class PlanRemindersTests(unittest.TestCase):
    NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)

    def appt(self, **overrides):
        base = {
            "id": "A1",
            "customer_name": "Aoife Murphy",
            "email": "aoife.murphy@example.com",
            "phone": "+353851234567",
            "country": "IE",
            "status": "booked",
            "starts_at": datetime(2026, 10, 20, 14, 0, tzinfo=DUBLIN),
            "optout_sms_v2": False,
        }
        base.update(overrides)
        return base

    @staticmethod
    def sends(out):
        return [r["send_at"] for r in out]

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([self.appt()], datetime(2026, 10, 17, 12, 0))

    def test_naive_starts_raises_without_leaking_pii(self):
        appt = self.appt(starts_at=datetime(2026, 10, 20, 14, 0))
        with self.assertRaises(ValueError) as cm:
            plan_reminders([appt], self.NOW)
        msg = str(cm.exception)
        self.assertIn("A1", msg)
        for secret in ("aoife.murphy@example.com", "+353851234567", "Aoife", "Murphy"):
            self.assertNotIn(secret, msg)

    def test_cancelled_produces_nothing(self):
        for status in ("cancelled", " CANCELLED ", "Cancelled"):
            self.assertEqual(plan_reminders([self.appt(status=status)], self.NOW), [])

    def test_three_days_out_two_reminders(self):
        out = plan_reminders([self.appt()], self.NOW)
        self.assertEqual(self.sends(out),
                         [datetime(2026, 10, 18, 13, 0, tzinfo=UTC),
                          datetime(2026, 10, 20, 11, 0, tzinfo=UTC)])
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])

    def test_one_day_out_immediate_and_two_hour(self):
        now = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 14, 10, 0, tzinfo=UTC))
        out = plan_reminders([appt], now)
        self.assertEqual(self.sends(out),
                         [now, datetime(2026, 10, 14, 8, 0, tzinfo=UTC)])

    def test_one_hour_out_no_reminder(self):
        now = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 13, 11, 0, tzinfo=UTC))
        self.assertEqual(plan_reminders([appt], now), [])

    def test_already_started_no_reminder(self):
        appt = self.appt(starts_at=self.NOW - timedelta(hours=1))
        self.assertEqual(plan_reminders([appt], self.NOW), [])

    def test_opted_out_flags_send_nothing(self):
        for value in (True, None):
            self.assertEqual(plan_reminders([self.appt(optout_sms_v2=value)], self.NOW), [])
        missing = self.appt()
        del missing["optout_sms_v2"]
        self.assertEqual(plan_reminders([missing], self.NOW), [])

    def test_no_phone_gets_email_only(self):
        for phone in ("", "   ", None):
            out = plan_reminders([self.appt(phone=phone)], self.NOW)
            self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_no_contact_no_reminder(self):
        appt = self.appt(phone=None, email="")
        self.assertEqual(plan_reminders([appt], self.NOW), [])

    def test_never_both_channels(self):
        out = plan_reminders([self.appt()], self.NOW)
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_quiet_2230_moves_to_2000_same_day(self):
        now = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 21, 0, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(self.sends(out),
                         [now, datetime(2026, 10, 20, 19, 0, tzinfo=UTC)])

    def test_quiet_0600_moves_to_2000_previous_day(self):
        now = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 21, 8, 0, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(self.sends(out),
                         [now, datetime(2026, 10, 20, 19, 0, tzinfo=UTC)])

    def test_dst_end_quiet_adjustment_uses_local_offset(self):
        # Europe/Dublin returns to GMT on 2026-10-25. 20:00 on 25 Oct is still IST (19:00 UTC).
        now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
        appt = self.appt(starts_at=datetime(2026, 10, 26, 8, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(self.sends(out),
                         [datetime(2026, 10, 24, 8, 30, tzinfo=UTC),
                          datetime(2026, 10, 25, 19, 0, tzinfo=UTC)])

    def test_now_in_quiet_window_defers_to_0800(self):
        now = datetime(2026, 10, 20, 22, 0, tzinfo=UTC)  # 23:00 Dublin
        appt = self.appt(starts_at=datetime(2026, 10, 21, 9, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(self.sends(out), [datetime(2026, 10, 21, 7, 0, tzinfo=UTC)])

    def test_quiet_adjusted_time_clamped_to_now(self):
        now = datetime(2026, 10, 20, 19, 30, tzinfo=UTC)  # 20:30 Dublin
        appt = self.appt(starts_at=datetime(2026, 10, 21, 0, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(self.sends(out), [now])

    def test_exact_text(self):
        out = plan_reminders([self.appt()], self.NOW)
        self.assertEqual(
            out[0]["text"],
            "Hi Aoife Murphy, reminder of your Brennan Opticians appointment on "
            "20 Oct 2026 at 14:00. Siobhán Ní Dhuibhir")

    def test_pl_signature(self):
        out = plan_reminders([self.appt(country=" pl ")], self.NOW)
        self.assertTrue(all(r["text"].endswith("Grzegorz Szczepański") for r in out))

    def test_sms_name_shortened_to_first_name_then_initial(self):
        out = plan_reminders([self.appt(customer_name="Maximilian " + "Y" * 60)], self.NOW)
        self.assertTrue(out[0]["text"].startswith("Hi Maximilian, "))
        out = plan_reminders([self.appt(customer_name="X" * 80 + " Surname")], self.NOW)
        self.assertTrue(out[0]["text"].startswith("Hi X., "))
        for r in out:
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("20 Oct 2026 at 14:00", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_email_has_no_length_limit(self):
        name = "Y" * 300
        appt = self.appt(phone="", customer_name=name)
        out = plan_reminders([appt], self.NOW)
        self.assertTrue(out[0]["text"].startswith("Hi " + name + ", "))
        self.assertGreater(len(out[0]["text"]), 160)

    def test_sorted_with_tie_break(self):
        appts = [self.appt(id="A2"), self.appt(id="A1")]
        out = plan_reminders(appts, self.NOW)
        keys = [(r["send_at"], r["appointment_id"], r["channel"]) for r in out]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([r["appointment_id"] for r in out], ["A1", "A2", "A1", "A2"])

    def test_output_keys_and_utc(self):
        out = plan_reminders([self.appt()], self.NOW)
        for r in out:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(r["send_at"].utcoffset(), timedelta(0))

    def test_logs_contain_no_pii(self):
        appt = self.appt(id="A9", customer_name="Zara Quinlan",
                         email="zara.quinlan@example.com", phone="+353871112233")
        with self.assertLogs(level="INFO") as cm:
            out = plan_reminders([appt], self.NOW)
        self.assertEqual(len(cm.output), len(out))
        joined = "\n".join(cm.output)
        for secret in ("@", "zara", "Zara", "Quinlan", "+353871112233", "871112233"):
            self.assertNotIn(secret, joined)


if __name__ == "__main__":
    unittest.main()