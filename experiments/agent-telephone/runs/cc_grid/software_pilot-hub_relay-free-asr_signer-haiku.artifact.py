# Module for Brennan Opticians appointment reminders.
# Stdlib only, Python 3.12. Tests are at the bottom of this module (run: python -m unittest).
#
# Notes for review (not executed in this session):
# - The house rule asks for one INFO log line per reminder with the contact. That conflicts with the
#   client's privacy requirement (no logging at all, no contact data in output). This module follows the
#   client requirement and emits nothing. Confirm before adding any log output.
# - Opt-out is treated as "opted out" unless optout_sms_v2 is exactly False (missing, None, 0, "false" all opt out).
# - Quiet-hours fallback for the second reminder never clamps to now; it is dropped instead.
# - All reminder arithmetic is done in UTC; Dublin local time is used only for quiet-hour checks and text.

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
DEFAULT_SIGNATURE = "Chevonne Nee Divver"
PL_SIGNATURE = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _text(value):
    return "" if value is None else str(value).strip()


def _is_quiet(utc_dt):
    hour = utc_dt.astimezone(DUBLIN).hour
    return hour >= 21 or hour < 8


def _last_evening(utc_dt):
    local = utc_dt.astimezone(DUBLIN)
    day = local.date() if local.hour >= 20 else local.date() - timedelta(days=1)
    return datetime(day.year, day.month, day.day, 20, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(utc_now):
    local = utc_now.astimezone(DUBLIN)
    day = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    return datetime(day.year, day.month, day.day, 8, tzinfo=DUBLIN).astimezone(UTC)


def _schedule(nominal, starts, now, first):
    t = nominal
    if t < now:
        if not first:
            return None
        t = now
    if _is_quiet(t):
        evening = _last_evening(t)
        if evening >= now:
            t = evening
        elif not _is_quiet(now):
            if not first:
                return None
            t = now
        else:
            t = _next_morning(now)
            if t >= starts:
                return None
    if t < now or t >= starts:
        return None
    return t


def _sms_text(name, date, hhmm, sig, appt_id):
    first = name.split()[0] if name else ""
    for who in (name, first):
        if who:
            body = f"Brennan Opticians: appointment reminder for {who}, {date} at {hhmm}. - {sig}"
            if len(body) <= SMS_LIMIT:
                return body
    body = f"Brennan Opticians: appointment reminder, {date} at {hhmm}. - {sig}"
    if len(body) > SMS_LIMIT:
        raise ValueError(f"SMS for appointment {appt_id!r} exceeds {SMS_LIMIT} characters")
    return body


def _email_text(name, date, hhmm, sig):
    greeting = f"Dear {name}," if name else "Hello,"
    return (
        f"{greeting}\n\n"
        f"This is a reminder of your appointment at Brennan Opticians on {date} at {hhmm}.\n\n"
        f"Kind regards,\n{sig}"
    )


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    found = []
    for appt in appointments:
        appt_id = appt.get("id")
        starts = appt.get("starts_at")
        if not _aware(starts):
            raise ValueError(f"starts_at for appointment {appt_id!r} must be timezone-aware")
        if _text(appt.get("status")).lower() == "cancelled":
            continue
        phone = _text(appt.get("phone"))
        email = _text(appt.get("email"))
        if phone and appt.get("optout_sms_v2") is False:
            channel = "sms"
        elif email:
            channel = "email"
        else:
            continue

        starts_utc = starts.astimezone(UTC)
        local = starts.astimezone(DUBLIN)
        date = f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"
        hhmm = f"{local.hour:02d}:{local.minute:02d}"
        sig = PL_SIGNATURE if _text(appt.get("country")).upper() == "PL" else DEFAULT_SIGNATURE
        name = _text(appt.get("customer_name"))
        if channel == "sms":
            text = _sms_text(name, date, hhmm, sig, appt_id)
        else:
            text = _email_text(name, date, hhmm, sig)

        nominals = (starts_utc - timedelta(hours=48), starts_utc - timedelta(hours=2))
        for order, nominal in enumerate(nominals):
            send_at = _schedule(nominal, starts_utc, now_utc, first=(order == 0))
            if send_at is not None:
                reminder = {
                    "appointment_id": appt_id,
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
                found.append((send_at, appt_id, order, reminder))

    found.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in found]


# ---------------------------------------------------------------- tests

import inspect
import sys
import unittest

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=DUBLIN)


def mk(**overrides):
    appt = {
        "id": 1,
        "customer_name": "Ann Murphy",
        "email": "ann@example.com",
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 10, 20, 12, 0, tzinfo=DUBLIN),
        "optout_sms_v2": False,
    }
    appt.update(overrides)
    return appt


def utc(*args):
    return datetime(*args, tzinfo=UTC)


class PlanRemindersTests(unittest.TestCase):

    def test_keys_and_sort_order(self):
        r = plan_reminders([mk(id=2), mk(id=1)], NOW)
        self.assertEqual(len(r), 4)
        for item in r:
            self.assertEqual(set(item), {"appointment_id", "channel", "send_at", "text"})
        keys = [(item["send_at"], item["appointment_id"]) for item in r]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(r[0]["appointment_id"], 1)

    def test_cancelled_produces_nothing(self):
        self.assertEqual(plan_reminders([mk(status=" Cancelled ")], NOW), [])
        self.assertEqual(plan_reminders([mk(status="CANCELLED")], NOW), [])

    def test_opt_out_read_only_from_v2(self):
        r = plan_reminders([mk(opt_out=True, optout_sms_v2=False)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"sms"})
        r = plan_reminders([mk(opt_out=False, optout_sms_v2=True)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})
        a = mk(opt_out=False)
        del a["optout_sms_v2"]
        r = plan_reminders([a], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_phone_without_opt_out_is_sms_only(self):
        r = plan_reminders([mk()], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual({x["channel"] for x in r}, {"sms"})

    def test_opted_out_with_email_is_email_only(self):
        r = plan_reminders([mk(optout_sms_v2=True)], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_no_phone_no_email_gives_nothing(self):
        self.assertEqual(plan_reminders([mk(phone="  ", email="")], NOW), [])
        self.assertEqual(plan_reminders([mk(phone=None, email=None, optout_sms_v2=True)], NOW), [])

    def test_invariants_including_dst_days(self):
        starts_cases = [
            datetime(2026, 3, 29, 9, 0, tzinfo=DUBLIN),
            datetime(2026, 10, 25, 9, 0, tzinfo=DUBLIN),
            datetime(2026, 10, 26, 10, 0, tzinfo=DUBLIN),
            datetime(2026, 10, 17, 15, 0, tzinfo=DUBLIN),
            datetime(2026, 10, 20, 23, 30, tzinfo=DUBLIN),
            datetime(2026, 10, 18, 7, 30, tzinfo=DUBLIN),
        ]
        nows = [NOW, datetime(2026, 10, 16, 22, 0, tzinfo=DUBLIN), datetime(2026, 10, 16, 20, 30, tzinfo=DUBLIN)]
        for s in starts_cases:
            for n in nows:
                for r in plan_reminders([mk(starts_at=s)], n):
                    send = r["send_at"]
                    self.assertIsNotNone(send.utcoffset())
                    self.assertGreaterEqual(send, n)
                    self.assertLess(send, s)
                    self.assertTrue(8 <= send.astimezone(DUBLIN).hour < 21)

    def test_worked_example(self):
        now = datetime(2026, 10, 16, 22, 0, tzinfo=DUBLIN)
        starts = datetime(2026, 10, 17, 15, 0, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], now)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["send_at"], utc(2026, 10, 17, 7, 0))
        self.assertEqual(r[1]["send_at"], utc(2026, 10, 17, 12, 0))

    def test_first_clamps_to_now_and_second_dropped_when_late(self):
        starts = datetime(2026, 10, 17, 15, 0, tzinfo=DUBLIN)
        now = datetime(2026, 10, 17, 13, 30, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], now.astimezone(UTC))

    def test_quiet_boundary_21_00_moves_to_20_00(self):
        starts = datetime(2026, 10, 17, 23, 0, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["send_at"], utc(2026, 10, 14, 19, 0))
        self.assertEqual(r[1]["send_at"], utc(2026, 10, 17, 19, 0))

    def test_quiet_boundary_08_00_is_allowed(self):
        starts = datetime(2026, 10, 17, 10, 0, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[1]["send_at"], utc(2026, 10, 17, 7, 0))

    def test_quiet_boundary_07_59_moves_to_previous_20_00(self):
        starts = datetime(2026, 10, 17, 9, 59, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[1]["send_at"], utc(2026, 10, 16, 19, 0))

    def test_second_never_clamped_to_now(self):
        now = datetime(2026, 10, 16, 20, 30, tzinfo=DUBLIN)
        starts = datetime(2026, 10, 16, 23, 0, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], now.astimezone(UTC))

    def test_dst_fall_back_second_reminder(self):
        starts = datetime(2026, 10, 26, 10, 0, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], NOW)
        self.assertEqual(r[1]["send_at"], utc(2026, 10, 26, 8, 0))

    def test_dst_spring_forward_quiet_hours(self):
        starts = datetime(2026, 3, 29, 9, 0, tzinfo=DUBLIN)
        r = plan_reminders([mk(starts_at=starts)], NOW)
        self.assertEqual(r[1]["send_at"], utc(2026, 3, 28, 20, 0))

    def test_sms_name_shortening_and_required_fields(self):
        name = "Maximilian " + "Q" * 75
        r = plan_reminders([mk(customer_name=name)], NOW)
        self.assertEqual(len(r), 2)
        for item in r:
            self.assertEqual(item["channel"], "sms")
            self.assertLessEqual(len(item["text"]), SMS_LIMIT)
            self.assertIn("20 Oct 2026 at 12:00", item["text"])
            self.assertIn("Chevonne Nee Divver", item["text"])
            self.assertNotIn("QQQ", item["text"])
        self.assertEqual(
            r[0]["text"],
            "Brennan Opticians: appointment reminder for Maximilian, 20 Oct 2026 at 12:00. - Chevonne Nee Divver",
        )

    def test_sms_omits_name_when_first_name_too_long(self):
        name = "M" * 150 + " Q"
        r = plan_reminders([mk(customer_name=name)], NOW)
        self.assertEqual(
            r[0]["text"],
            "Brennan Opticians: appointment reminder, 20 Oct 2026 at 12:00. - Chevonne Nee Divver",
        )

    def test_sms_no_name_too_long_raises(self):
        from unittest import mock  # local import, test-only
        with self.assertRaises(ValueError):
            _sms_text("", "20 Oct 2026", "12:00", "S" * 200, 5)

    def test_text_uses_starts_at_not_send_time(self):
        r = plan_reminders([mk()], NOW)
        self.assertEqual(r[0]["send_at"], utc(2026, 10, 18, 11, 0))
        for item in r:
            self.assertIn("20 Oct 2026 at 12:00", item["text"])

    def test_pl_signature_and_default(self):
        r = plan_reminders([mk(country=" pl ", phone="", email="ann@example.com", optout_sms_v2=True)], NOW)
        self.assertIn("\nGrzegorz Szczepański", r[0]["text"])
        self.assertNotIn("Chevonne", r[0]["text"])
        r = plan_reminders([mk(country="GB")], NOW)
        self.assertTrue(r[0]["text"].endswith("Chevonne Nee Divver"))
        self.assertNotIn("Grzegorz", r[0]["text"])

    def test_pl_sms_uses_pl_signature(self):
        r = plan_reminders([mk(country="pl")], NOW)
        self.assertTrue(r[0]["text"].endswith("Grzegorz Szczepański"))

    def test_email_exact_body_and_blank_name(self):
        r = plan_reminders([mk(phone="", optout_sms_v2=True)], NOW)
        self.assertEqual(
            r[0]["text"],
            "Dear Ann Murphy,\n\nThis is a reminder of your appointment at Brennan Opticians "
            "on 20 Oct 2026 at 12:00.\n\nKind regards,\nChevonne Nee Divver",
        )
        r = plan_reminders([mk(customer_name="   ", phone="", optout_sms_v2=True)], NOW)
        self.assertTrue(r[0]["text"].startswith("Hello,\n\n"))
        self.assertNotIn("@", r[0]["text"])
        self.assertNotIn("http", r[0]["text"])

    def test_naive_starts_raises_without_pii(self):
        a = mk(
            id=77,
            customer_name="Secret Person",
            email="secret.person@example.com",
            phone="+353850000000",
            starts_at=datetime(2026, 10, 20, 12, 0),
        )
        with self.assertRaises(ValueError) as cm:
            plan_reminders([a], NOW)
        msg = str(cm.exception)
        self.assertIn("77", msg)
        for pii in ("Secret", "Person", "secret", "example.com", "850000000"):
            self.assertNotIn(pii, msg)

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([mk()], datetime(2026, 10, 1, 12, 0))

    def test_module_does_not_log(self):
        src = inspect.getsource(sys.modules[__name__])
        for needle in ("import " + "logging", "get" + "Logger", "pri" + "nt("):
            self.assertNotIn(needle, src)


if __name__ == "__main__":
    unittest.main()