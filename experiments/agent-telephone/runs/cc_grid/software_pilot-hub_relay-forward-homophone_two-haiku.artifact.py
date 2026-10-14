"""Appointment reminder planning for Brennan Opticians.

plan_reminders() is pure planning. It sends nothing and makes no network or DB calls.
Each planned reminder is logged at INFO with the appointment id, channel and a masked contact.

Deviations and interpretations for the tech lead:
- Quiet window: a send time in 21:00-07:59 Europe/Dublin moves back to 20:00 Dublin on the same
  day (21:00-23:59) or the previous day (00:00-07:59). If that moved time is before now and now is
  outside the window, the send is now. If now is inside the window, the send is 08:00 Dublin on the
  first morning at or after now.
- A past nominal time becomes now, and that now is also quiet-window adjusted.
- An appointment less than 2 hours away gets reminder 1 and reminder 2 both at now, same channel
  and text. Kept per decision 2, but it means two identical messages. Flagged for review.
- SMS shortening: the name is truncated to fit with a trailing ellipsis. If fewer than 2 name
  characters would remain, the name is dropped. If the SMS is still over 160 characters, it is
  returned anyway and a WARNING is logged with the appointment id.
- Logging: the brief asks for the contact in each log line, but the email address must never be
  logged. SMS lines log the last 4 digits of the phone. Email lines log "email on file".
- optout_sms_v2 is read with bool(). The legacy opt_out field is never read.
- Validation: a naive starts_at or now raises ValueError. Messages name only the appointment id.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REMINDER_1_BEFORE = timedelta(hours=48)
REMINDER_2_BEFORE = timedelta(hours=2)


def _check_aware(value, label):
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _in_quiet_window(local):
    return local.hour >= 21 or local.hour < 8


def _dublin_at(day, hour):
    return datetime.combine(day, time(hour, 0), tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(now):
    local_day = now.astimezone(DUBLIN).date()
    candidate = _dublin_at(local_day, 8)
    if candidate < now:
        candidate = _dublin_at(local_day + timedelta(days=1), 8)
    return candidate


def _send_time(nominal, now):
    t = nominal if nominal >= now else now
    local = t.astimezone(DUBLIN)
    if not _in_quiet_window(local):
        return t
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    moved = _dublin_at(day, 20)
    if moved >= now:
        return moved
    if not _in_quiet_window(now.astimezone(DUBLIN)):
        return now
    return _next_morning(now)


def _date_str(d):
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def _build_text(name, date_s, time_s, sig):
    if name:
        return (f"Hi {name}, your Brennan Opticians appointment is on "
                f"{date_s} at {time_s}. {sig}")
    return (f"Your Brennan Opticians appointment is on "
            f"{date_s} at {time_s}. {sig}")


def _sms_text(name, date_s, time_s, sig):
    full = _build_text(name, date_s, time_s, sig)
    if len(full) <= SMS_LIMIT or not name:
        return full
    overflow = len(full) - SMS_LIMIT
    keep = len(name) - overflow
    if keep >= 2:
        short = _build_text(name[:keep - 1] + "…", date_s, time_s, sig)
        if len(short) <= SMS_LIMIT:
            return short
    return _build_text("", date_s, time_s, sig)


def _channel(appt):
    email = str(appt.get("email") or "").strip()
    phone = str(appt.get("phone") or "").strip()
    if bool(appt.get("optout_sms_v2")):
        return "email" if email else None
    if phone:
        return "sms"
    return "email" if email else None


def plan_reminders(appointments, now):
    _check_aware(now, "now")
    appointments = list(appointments)
    for appt in appointments:
        _check_aware(appt["starts_at"],
                     f"starts_at of appointment {appt.get('id')!r}")

    planned = []
    for appt in appointments:
        if str(appt.get("status") or "").casefold() == "cancelled":
            continue
        starts_at = appt["starts_at"]
        if starts_at <= now:
            continue
        channel = _channel(appt)
        if channel is None:
            continue

        appt_id = appt["id"]
        name = " ".join(str(appt.get("customer_name") or "").split())
        sig = SIG_PL if appt.get("country") == "PL" else SIG_DEFAULT
        local_start = starts_at.astimezone(DUBLIN)
        date_s = _date_str(local_start.date())
        time_s = local_start.strftime("%H:%M")
        phone_digits = "".join(c for c in str(appt.get("phone") or "") if c.isdigit())

        for nominal in (starts_at - REMINDER_1_BEFORE, starts_at - REMINDER_2_BEFORE):
            send_at = _send_time(nominal, now).astimezone(UTC)
            if channel == "sms":
                text = _sms_text(name, date_s, time_s, sig)
                if len(text) > SMS_LIMIT:
                    log.warning("SMS still over %d characters for appointment_id=%s",
                                SMS_LIMIT, appt_id)
                contact = f"phone ending {phone_digits[-4:]}"
            else:
                text = _build_text(name, date_s, time_s, sig)
                contact = "email on file"
            log.info("planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                     appt_id, channel, contact, send_at.isoformat())
            planned.append({
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })

    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


if __name__ == "__main__":
    import unittest

    NOW = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
    EMAIL = "aoife@example.com"

    def _appt(**kw):
        base = {
            "id": "A1",
            "customer_name": "Aoife Murphy",
            "email": EMAIL,
            "phone": "+353861234567",
            "country": "IE",
            "status": "booked",
            "starts_at": NOW + timedelta(hours=72),
            "optout_sms_v2": False,
        }
        base.update(kw)
        return base

    def _hours_clear(test, reminders):
        for r in reminders:
            hour = r["send_at"].astimezone(DUBLIN).hour
            test.assertFalse(hour >= 21 or hour < 8, r["send_at"])

    class PlanRemindersTests(unittest.TestCase):

        def test_72h_gives_48h_and_2h_reminders(self):
            r = plan_reminders([_appt()], NOW)
            self.assertEqual([x["send_at"] for x in r],
                             [NOW + timedelta(hours=24), NOW + timedelta(hours=70)])
            self.assertTrue(all(x["channel"] == "sms" for x in r))

        def test_30h_sends_first_reminder_now(self):
            r = plan_reminders([_appt(starts_at=NOW + timedelta(hours=30))], NOW)
            self.assertEqual([x["send_at"] for x in r],
                             [NOW, NOW + timedelta(hours=28)])

        def test_cancelled_gives_nothing(self):
            self.assertEqual(plan_reminders([_appt(status="CANCELLED")], NOW), [])

        def test_past_appointment_gives_nothing(self):
            self.assertEqual(
                plan_reminders([_appt(starts_at=NOW - timedelta(hours=1))], NOW), [])

        def test_opted_out_gets_email_only(self):
            r = plan_reminders([_appt(optout_sms_v2=True)], NOW)
            self.assertEqual([x["channel"] for x in r], ["email", "email"])

        def test_opted_out_without_email_gets_nothing(self):
            self.assertEqual(
                plan_reminders([_appt(optout_sms_v2=True, email="")], NOW), [])

        def test_old_opt_out_field_is_ignored(self):
            r = plan_reminders([_appt(opt_out=True)], NOW)
            self.assertEqual([x["channel"] for x in r], ["sms", "sms"])

        def test_no_phone_falls_back_to_email(self):
            r = plan_reminders([_appt(phone="")], NOW)
            self.assertEqual([x["channel"] for x in r], ["email", "email"])

        def test_quiet_window_moves_back_to_2000_dublin(self):
            starts = datetime(2026, 10, 16, 23, 30, tzinfo=DUBLIN)
            r = plan_reminders([_appt(starts_at=starts)], NOW)
            self.assertEqual([x["send_at"] for x in r],
                             [datetime(2026, 10, 14, 19, 0, tzinfo=UTC),
                              datetime(2026, 10, 16, 19, 0, tzinfo=UTC)])
            _hours_clear(self, r)

        def test_quiet_window_when_now_is_inside_window(self):
            now = datetime(2026, 10, 13, 22, 0, tzinfo=UTC)  # 23:00 Dublin
            starts = datetime(2026, 10, 14, 13, 0, tzinfo=DUBLIN)
            r = plan_reminders([_appt(starts_at=starts)], now)
            self.assertEqual([x["send_at"] for x in r],
                             [datetime(2026, 10, 14, 7, 0, tzinfo=UTC),
                              datetime(2026, 10, 14, 10, 0, tzinfo=UTC)])
            _hours_clear(self, r)
            self.assertTrue(all(x["send_at"] >= now for x in r))

        def test_sms_within_limit_with_date_time_and_signature(self):
            name = ("Bartholomew Maximilian Featherstonehaugh-Montgomery "
                    "the Third of Kilkenny County")
            r = plan_reminders([_appt(customer_name=name)], NOW)
            self.assertTrue(r)
            for x in r:
                self.assertLessEqual(len(x["text"]), SMS_LIMIT)
                self.assertIn("16 Oct 2026 at 11:00", x["text"])
                self.assertTrue(x["text"].endswith(SIG_DEFAULT))

        def test_sms_name_truncated_with_ellipsis_when_needed(self):
            name = "X" * 150
            r = plan_reminders([_appt(customer_name=name)], NOW)
            self.assertTrue(all(len(x["text"]) <= SMS_LIMIT for x in r))
            self.assertIn("…", r[0]["text"])
            self.assertIn("16 Oct 2026 at 11:00", r[0]["text"])

        def test_pl_signature(self):
            r = plan_reminders([_appt(country="PL")], NOW)
            self.assertTrue(all(x["text"].endswith(SIG_PL) for x in r))

        def test_sorted_by_send_at_then_id_then_channel(self):
            a = _appt(id="B", starts_at=NOW + timedelta(hours=72))
            b = _appt(id="A", starts_at=NOW + timedelta(hours=72))
            c = _appt(id="C", starts_at=NOW + timedelta(hours=30))
            r = plan_reminders([a, b, c], NOW)
            keys = [(x["send_at"], x["appointment_id"], x["channel"]) for x in r]
            self.assertEqual(keys, sorted(keys))

        def test_returns_exactly_four_keys(self):
            r = plan_reminders([_appt()], NOW)
            self.assertTrue(all(set(x) == {"appointment_id", "channel", "send_at", "text"}
                                for x in r))

        def test_no_email_in_logs(self):
            for appt in (_appt(optout_sms_v2=True), _appt()):
                with self.assertLogs(level="INFO") as cm:
                    plan_reminders([appt], NOW)
                joined = "\n".join(cm.output)
                self.assertNotIn(EMAIL, joined)
                self.assertIn("A1", joined)
                self.assertEqual(len(cm.records), 2)

        def test_no_email_in_exceptions(self):
            with self.assertRaises(ValueError) as cm:
                plan_reminders([_appt(starts_at=datetime(2026, 10, 16, 10, 0))], NOW)
            self.assertNotIn(EMAIL, str(cm.exception))

        def test_naive_now_raises(self):
            with self.assertRaises(ValueError):
                plan_reminders([], datetime(2026, 10, 13, 10, 0))

    unittest.main()