"""Appointment reminder planning for Brennan Opticians.

plan_reminders(appointments, now) is a pure function apart from INFO logging.
It never reads the clock and never reads the legacy opt_out field.

Decisions and open items for client sign-off:
- Quiet hours are 21:00 to 08:00 Europe/Dublin, evaluated with zoneinfo.
  A reminder whose nominal time is quiet moves to 20:00 Dublin on the preceding
  evening. If that is before now, use now when now is outside quiet hours,
  otherwise use the first 08:00 Dublin at or after now. Drop it if the result is
  at or after starts_at. The quiet-hours case deliberately overrides the
  "send_at = now" rule. This is the tech lead's provisional resolution.
- If the appointment is within 2 hours of now and has not started, exactly one
  reminder is planned at now, subject to quiet hours. The 48-hour reminder is not
  planned in that case. This is provisional.
- No phone on file means email. This is provisional. A slot needs a non-empty
  email address, otherwise nothing is produced for it.
- Phone with optout_sms_v2 true means email, under the same email-required rule.
- Cancelled and already started or past appointments produce nothing.
- Country is normalised with strip().upper(). "PL" uses the Polish signature.
- All copy is provisional. PROVISIONAL_TAG marks it and should be removed on sign-off.
- SMS length is measured with len(). Accented characters usually force UCS-2
  encoding, which gives 70-character segments on many carriers. Needs confirmation.
- Logging: email addresses are never logged. Email reminders are logged with a
  truncated SHA-256 reference, which departs from the literal "channel and contact"
  house rule and needs confirmation. SMS reminders log the phone number.
- The tests live in the __main__ block and were not executed in the authoring environment.
"""

import hashlib
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
TWO_HOURS = timedelta(hours=2)
FORTY_EIGHT_HOURS = timedelta(hours=48)
SMS_LIMIT = 160
PROVISIONAL_TAG = "[PROVISIONAL] "
SIG_IE = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
_FIELDS = ("id", "customer_name", "email", "phone", "country", "status",
           "starts_at", "optout_sms_v2")


def _validate(appt, where):
    for f in _FIELDS:
        if f not in appt:
            raise ValueError(f"{where}.{f} is missing")
    if isinstance(appt["id"], bool) or not isinstance(appt["id"], (int, str)):
        raise ValueError(f"{where}.id must be an int or str")
    for f in ("customer_name", "status"):
        if not isinstance(appt[f], str):
            raise ValueError(f"{where}.{f} must be a str")
    for f in ("email", "phone", "country"):
        if appt[f] is not None and not isinstance(appt[f], str):
            raise ValueError(f"{where}.{f} must be a str or None")
    if not isinstance(appt["optout_sms_v2"], bool):
        raise ValueError(f"{where}.optout_sms_v2 must be a bool")
    s = appt["starts_at"]
    if not isinstance(s, datetime):
        raise ValueError(f"{where}.starts_at must be a datetime")
    if s.utcoffset() is None:
        raise ValueError(f"{where}.starts_at must be timezone-aware")


def _is_quiet(t):
    h = t.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _dublin_utc(day, hour):
    return datetime.combine(day, time(hour, 0), tzinfo=DUBLIN).astimezone(UTC)


def _apply_quiet(t, now, start):
    """Return the allowed send time for nominal time t, or None to drop it."""
    if not _is_quiet(t):
        return t
    local = t.astimezone(DUBLIN)
    evening = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    cand = _dublin_utc(evening, 20)
    if cand >= now:
        result = cand
    elif not _is_quiet(now):
        result = now
    else:
        d = now.astimezone(DUBLIN).date()
        result = _dublin_utc(d, 8)
        if result < now:
            result = _dublin_utc(d + timedelta(days=1), 8)
    if result >= start:
        return None
    return result


def _sms_text(name, date_s, time_s, sig):
    head = f"{PROVISIONAL_TAG}Brennan Opticians: reminder for "
    tail = f". Appointment {date_s} at {time_s} (Dublin time). {sig}"
    room = SMS_LIMIT - len(head) - len(tail)
    if len(name) > room:
        name = name[:max(room - 3, 0)].rstrip() + "..."
    return head + name + tail


def _email_text(name, date_s, time_s, sig):
    return (f"{PROVISIONAL_TAG}Dear {name},\n\n"
            f"This is a reminder of your appointment at Brennan Opticians on "
            f"{date_s} at {time_s} (Dublin time).\n\n"
            f"Kind regards,\n{sig}")


def _plan_one(appt, now):
    """Return a list of (sort_key, reminder, contact_ref) for one appointment."""
    if appt["status"].strip().lower() == "cancelled":
        return []
    start = appt["starts_at"].astimezone(UTC)
    if start <= now:
        return []

    slots = []
    if start - now <= TWO_HOURS:
        slots.append((2, now))  # immediate reminder, one only
    else:
        slots.append((2, start - TWO_HOURS))
        # 48-hour reminder: delete these two lines to descope it.
        slots.append((1, max(start - FORTY_EIGHT_HOURS, now)))

    phone = (appt["phone"] or "").strip()
    email = (appt["email"] or "").strip()
    if phone and not appt["optout_sms_v2"]:
        channel = "sms"
        contact = f"phone={phone}"
    else:
        channel = "email"
        if not email:
            return []
        ref = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:12]
        contact = f"email_ref={ref}"

    country = (appt["country"] or "").strip().upper()
    sig = SIG_PL if country == "PL" else SIG_IE
    local = start.astimezone(DUBLIN)
    date_s = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    name = appt["customer_name"].strip() or "customer"

    out = []
    aid = appt["id"]
    id_key = (isinstance(aid, str), aid)
    for slot, nominal in slots:
        send_at = _apply_quiet(nominal, now, start)
        if send_at is None:
            continue
        if channel == "sms":
            text = _sms_text(name, date_s, time_s, sig)
        else:
            text = _email_text(name, date_s, time_s, sig)
        reminder = {"appointment_id": aid, "channel": channel,
                    "send_at": send_at, "text": text}
        out.append(((send_at, id_key, slot), reminder, contact))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list")
    for i, appt in enumerate(appointments):
        if not isinstance(appt, dict):
            raise ValueError(f"appointments[{i}] must be a dict")
        _validate(appt, f"appointments[{i}]")

    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda p: p[0])

    result = []
    for _, reminder, contact in planned:
        log.info("planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                 reminder["appointment_id"], reminder["channel"], contact,
                 reminder["send_at"].isoformat())
        result.append(reminder)
    return result


if __name__ == "__main__":
    NOW = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)

    def _appt(**kw):
        base = dict(id=1, customer_name="Anna Murphy", email="anna@example.test",
                    phone="+353870000000", country="IE", status="booked",
                    starts_at=datetime(2026, 10, 20, 10, 0, tzinfo=DUBLIN),
                    optout_sms_v2=False)
        base.update(kw)
        return base

    class Tests(unittest.TestCase):
        def test_empty(self):
            self.assertEqual(plan_reminders([], NOW), [])

        def test_two_sms_reminders(self):
            out = plan_reminders([_appt()], NOW)
            self.assertEqual([r["channel"] for r in out], ["sms", "sms"])
            self.assertEqual(out[0]["send_at"], datetime(2026, 10, 18, 9, 0, tzinfo=UTC))
            self.assertEqual(out[1]["send_at"], datetime(2026, 10, 20, 7, 0, tzinfo=UTC))
            for r in out:
                self.assertTrue(r["text"].endswith(SIG_IE))
                self.assertIn("20 October 2026", r["text"])
                self.assertIn("10:00", r["text"])
                self.assertLessEqual(len(r["text"]), SMS_LIMIT)

        def test_cancelled_and_started_produce_nothing(self):
            self.assertEqual(plan_reminders([_appt(status="cancelled")], NOW), [])
            past = _appt(starts_at=datetime(2026, 10, 12, 10, 0, tzinfo=DUBLIN))
            self.assertEqual(plan_reminders([past], NOW), [])

        def test_optout_uses_email_and_needs_address(self):
            out = plan_reminders([_appt(optout_sms_v2=True)], NOW)
            self.assertEqual([r["channel"] for r in out], ["email", "email"])
            self.assertEqual(plan_reminders([_appt(optout_sms_v2=True, email="")], NOW), [])

        def test_no_phone_uses_email(self):
            out = plan_reminders([_appt(phone=None)], NOW)
            self.assertEqual([r["channel"] for r in out], ["email", "email"])

        def test_immediate_single_reminder(self):
            soon = _appt(starts_at=datetime(2026, 10, 13, 10, 0, tzinfo=UTC))
            out = plan_reminders([soon], NOW)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["send_at"], NOW)

        def test_first_clamped_to_now(self):
            start = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
            out = plan_reminders([_appt(starts_at=start)], NOW)
            self.assertEqual(len(out), 2)
            self.assertEqual(out[0]["send_at"], NOW)
            self.assertEqual(out[1]["send_at"], datetime(2026, 10, 14, 10, 0, tzinfo=UTC))

        def test_dst_quiet_hours(self):
            # 08:00 GMT on 26 Oct 2026; 2-hour nominal 06:00 GMT is quiet.
            start = datetime(2026, 10, 26, 8, 0, tzinfo=DUBLIN)
            now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
            out = plan_reminders([_appt(starts_at=start)], now)
            second = [r for r in out if r["send_at"].hour == 20]
            self.assertEqual(len(second), 1)
            self.assertEqual(second[0]["send_at"], datetime(2026, 10, 25, 20, 0, tzinfo=UTC))

        def test_morning_drop_when_after_start(self):
            start = datetime(2026, 10, 14, 8, 0, tzinfo=DUBLIN)
            now = datetime(2026, 10, 13, 22, 0, tzinfo=DUBLIN)
            self.assertEqual(plan_reminders([_appt(starts_at=start)], now), [])

        def test_polish_signature(self):
            out = plan_reminders([_appt(country=" pl ")], NOW)
            self.assertTrue(all(r["text"].endswith(SIG_PL) for r in out))

        def test_long_name_truncated_keeps_signature(self):
            out = plan_reminders([_appt(customer_name="A" * 300)], NOW)
            for r in out:
                self.assertLessEqual(len(r["text"]), SMS_LIMIT)
                self.assertIn("20 October 2026", r["text"])
                self.assertTrue(r["text"].endswith(SIG_IE))

        def test_naive_datetime_names_field(self):
            with self.assertRaisesRegex(ValueError, "starts_at"):
                plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 10, 0))], NOW)
            with self.assertRaisesRegex(ValueError, "now"):
                plan_reminders([], datetime(2026, 10, 13, 9, 0))

        def test_logs_do_not_contain_email(self):
            with self.assertLogs("reminders", level="INFO") as cm:
                plan_reminders([_appt(phone=None)], NOW)
            self.assertNotIn("anna@example.test", "\n".join(cm.output))

    unittest.main()