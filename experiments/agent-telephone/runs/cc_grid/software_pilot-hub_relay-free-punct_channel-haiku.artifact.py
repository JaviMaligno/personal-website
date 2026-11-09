"""Brennan Opticians appointment reminder planner.

Single standard-library module. Public entry point: plan_reminders(appointments, now).

Status: written without tool access, so the tests in this module have not been executed.

Decisions for the client to confirm:
1. Opt-out flag polarity: implemented literally as the client stated. SMS is used when optout_sms_v2 is exactly True and a non-empty phone is present. The field name suggests the opposite meaning, so this needs confirmation. The legacy opt_out field is not read.
2. Email fallback: email is used only when SMS is not eligible and a non-empty email is present. Each reminder has exactly one channel. If the two planned reminders for one appointment resolve to the same send time, only the 2-hour reminder is kept.
3. SMS that cannot fit in 160 characters: after trying the full name, the first name, and the plain greeting, the reminder is omitted and a WARNING is logged with the appointment id only. It is not truncated and it does not fall back to email. Email has no length limit.
4. Logging contact: INFO lines name the appointment id, the channel, and a masked contact. For SMS the contact is the last four digits of the phone number. For email the contact is the literal text "email (redacted)", so no email address is logged.
5. Output send_at values are returned in UTC.
6. Sends that fall in quiet hours and cannot be moved to an earlier 20:00 are dropped, as specified. A reminder is never moved later.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from unittest import mock
import unittest
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
SMS_MAX_LEN = 160
FIRST_LEAD = timedelta(hours=48)
SECOND_LEAD = timedelta(hours=2)
QUIET_END_HOUR = 8
EVENING_HOUR = 20
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _clean(value):
    return (value or "").strip()


def _require_aware(dt, what):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} must be timezone-aware")


def _is_cancelled(status):
    return _clean(status).casefold() == "cancelled"


def _is_quiet(local):
    return local.hour >= 21 or local.hour < QUIET_END_HOUR


def choose_channel(appt):
    """Client rule (not fully confirmed; keep changes here).

    SMS when a non-empty phone exists and optout_sms_v2 is exactly True.
    Otherwise email when a non-empty email exists. Otherwise None.
    """
    if _clean(appt.get("phone")) and appt.get("optout_sms_v2") is True:
        return "sms"
    if _clean(appt.get("email")):
        return "email"
    return None


def _apply_quiet_hours(send_utc, now_utc):
    """Return the adjusted UTC send time, or None if the reminder must be dropped."""
    local = send_utc.astimezone(DUBLIN)
    if not _is_quiet(local):
        return send_utc
    day = local.date()
    if local.hour < QUIET_END_HOUR:
        day -= timedelta(days=1)
    evening = datetime.combine(day, time(EVENING_HOUR), tzinfo=DUBLIN).astimezone(UTC)
    if evening >= now_utc:
        return evening
    if not _is_quiet(now_utc.astimezone(DUBLIN)):
        return now_utc
    return None


def _send_times(starts_utc, now_utc):
    """Return the UTC send times for one appointment (at most two, deduplicated)."""
    second = None
    second_raw = starts_utc - SECOND_LEAD
    if second_raw >= now_utc:
        second = _apply_quiet_hours(second_raw, now_utc)

    first_raw = max(starts_utc - FIRST_LEAD, now_utc)
    first = _apply_quiet_hours(first_raw, now_utc)

    times = []
    if second is not None:
        times.append(second)
    if first is not None and first != second:
        times.append(first)
    return [t for t in times if now_utc <= t < starts_utc]


def _signature(country):
    return PL_SIGNATURE if _clean(country).upper() == "PL" else DEFAULT_SIGNATURE


def _greeting(name):
    return f"Hi {name}" if name else "Hello"


def _body(greeting, local, signature):
    date = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    return (f"{greeting}, your Brennan Opticians appointment is "
            f"{date} at {local:%H:%M}. {signature}")


def _sms_text(name, local, signature):
    """Try full name, then first name, then plain greeting. None if nothing fits."""
    first = name.split()[0] if name else ""
    for option in dict.fromkeys([name, first, ""]):
        text = _body(_greeting(option), local, signature)
        if len(text) <= SMS_MAX_LEN:
            return text
    return None


def _text(appt, channel, local):
    name = _clean(appt.get("customer_name"))
    signature = _signature(appt.get("country"))
    if channel == "email":
        return _body(_greeting(name), local, signature)
    return _sms_text(name, local, signature)


def _contact(appt, channel):
    if channel == "sms":
        phone = _clean(appt.get("phone"))
        return "phone ...%s" % (phone[-4:] if len(phone) >= 4 else "****")
    return "email (redacted)"


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    now_utc = now.astimezone(UTC)
    planned = []

    for appt in appointments:
        appt_id = appt["id"]
        starts = appt["starts_at"]
        _require_aware(starts, f"starts_at (appointment_id={appt_id})")

        if _is_cancelled(appt.get("status")):
            continue
        starts_utc = starts.astimezone(UTC)
        if starts_utc <= now_utc:
            continue

        channel = choose_channel(appt)
        if channel is None:
            log.debug("no contact channel for appointment_id=%s; skipped", appt_id)
            continue

        text = _text(appt, channel, starts.astimezone(DUBLIN))
        if text is None:
            log.warning("SMS for appointment_id=%s does not fit in %d characters; "
                        "reminder omitted", appt_id, SMS_MAX_LEN)
            continue

        contact = _contact(appt, channel)
        for send in _send_times(starts_utc, now_utc):
            planned.append((send, appt_id, channel, text, contact))

    planned.sort(key=lambda p: (p[0], p[1]))

    result = []
    for send, appt_id, channel, text, contact in planned:
        log.info("reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                 appt_id, channel, contact, send.isoformat())
        result.append({
            "appointment_id": appt_id,
            "channel": channel,
            "send_at": send,
            "text": text,
        })
    return result


# ---------------------------------------------------------------- tests

EMAIL = "aoife.byrne@example.com"
PHONE = "+353 85 123 4567"
NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


def _appt(**overrides):
    a = {
        "id": "A1",
        "customer_name": "Aoife Byrne",
        "email": EMAIL,
        "phone": PHONE,
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 10, 20, 14, 0, tzinfo=UTC),
        "optout_sms_v2": False,
    }
    a.update(overrides)
    return a


def _send_ats(result):
    return [r["send_at"] for r in result]


class TimingTests(unittest.TestCase):
    def test_second_reminder_at_2h_and_first_at_48h(self):
        res = plan_reminders([_appt()], NOW)
        self.assertEqual(_send_ats(res), [
            datetime(2026, 10, 18, 14, 0, tzinfo=UTC),
            datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        ])

    def test_first_sent_now_when_48h_point_passed(self):
        now = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
        res = plan_reminders([_appt()], now)
        self.assertEqual(_send_ats(res), [now, datetime(2026, 10, 20, 12, 0, tzinfo=UTC)])

    def test_second_dropped_when_past(self):
        now = datetime(2026, 10, 20, 12, 30, tzinfo=UTC)
        res = plan_reminders([_appt()], now)
        self.assertEqual(_send_ats(res), [now])

    def test_started_appointment_skipped(self):
        now = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
        self.assertEqual(plan_reminders([_appt()], now), [])

    def test_appointment_exactly_now_skipped(self):
        now = datetime(2026, 10, 20, 14, 0, tzinfo=UTC)
        self.assertEqual(plan_reminders([_appt()], now), [])


class QuietHoursTests(unittest.TestCase):
    def test_post_dst_move_to_previous_evening(self):
        # 09:00 GMT on 26 Oct; 2h point is 07:00 GMT (quiet); moved to 20:00 GMT on 25 Oct.
        starts = datetime(2026, 10, 26, 9, 0, tzinfo=DUBLIN)
        now = datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
        res = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(_send_ats(res), [
            datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
            datetime(2026, 10, 25, 20, 0, tzinfo=UTC),
        ])

    def test_pre_dst_move_to_previous_evening(self):
        # 09:00 IST on 24 Oct; 2h point is 07:00 IST (quiet); moved to 20:00 IST on 23 Oct.
        starts = datetime(2026, 10, 24, 9, 0, tzinfo=DUBLIN)
        now = datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
        res = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(_send_ats(res), [
            datetime(2026, 10, 22, 8, 0, tzinfo=UTC),
            datetime(2026, 10, 23, 19, 0, tzinfo=UTC),
        ])

    def test_moved_time_uses_now_when_now_outside_quiet(self):
        starts = datetime(2026, 10, 20, 22, 30, tzinfo=UTC)  # 23:30 IST
        now = datetime(2026, 10, 20, 19, 30, tzinfo=UTC)     # 20:30 IST, not quiet
        res = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(_send_ats(res), [now])

    def test_moved_time_dropped_when_now_quiet(self):
        starts = datetime(2026, 10, 20, 22, 30, tzinfo=UTC)
        now = datetime(2026, 10, 20, 20, 30, tzinfo=UTC)     # 21:30 IST, quiet
        self.assertEqual(plan_reminders([_appt(starts_at=starts)], now), [])


class FilterAndChannelTests(unittest.TestCase):
    def test_cancelled_skipped_case_insensitive(self):
        self.assertEqual(plan_reminders([_appt(status="  Cancelled ")], NOW), [])

    def test_other_status_eligible(self):
        self.assertEqual(len(plan_reminders([_appt(status="CONFIRMED")], NOW)), 2)

    def test_sms_when_phone_and_flag_true(self):
        res = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual({r["channel"] for r in res}, {"sms"})

    def test_email_when_flag_false(self):
        res = plan_reminders([_appt(optout_sms_v2=False)], NOW)
        self.assertEqual({r["channel"] for r in res}, {"email"})

    def test_email_fallback_when_phone_empty(self):
        res = plan_reminders([_appt(optout_sms_v2=True, phone="   ")], NOW)
        self.assertEqual({r["channel"] for r in res}, {"email"})

    def test_non_bool_flag_not_treated_as_sms(self):
        res = plan_reminders([_appt(optout_sms_v2="true")], NOW)
        self.assertEqual({r["channel"] for r in res}, {"email"})

    def test_skipped_when_no_channel(self):
        res = plan_reminders([_appt(optout_sms_v2=True, phone="", email=" ")], NOW)
        self.assertEqual(res, [])

    def test_no_double_send_for_same_appointment_and_time(self):
        res = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        keys = [(r["appointment_id"], r["send_at"]) for r in res]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(r["channel"] == "sms" for r in res))

    def test_collapsed_duplicate_times_yield_one_reminder(self):
        # Both reminders resolve to "now" (20:30 UTC, not quiet in Dublin).
        now = datetime(2026, 10, 20, 20, 30, tzinfo=UTC)
        starts = datetime(2026, 10, 20, 22, 30, tzinfo=UTC)
        res = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(len(res), 1)


class TextTests(unittest.TestCase):
    def test_exact_email_text(self):
        res = plan_reminders([_appt()], NOW)
        self.assertEqual(res[0]["text"],
                         "Hi Aoife Byrne, your Brennan Opticians appointment is "
                         "20 Oct 2026 at 15:00. Siobhán Ní Dhuibhir")

    def test_empty_name_uses_hello(self):
        res = plan_reminders([_appt(customer_name="  ")], NOW)
        self.assertTrue(res[0]["text"].startswith("Hello, your Brennan Opticians"))

    def test_pl_signature(self):
        res = plan_reminders([_appt(country=" pl ", optout_sms_v2=True)], NOW)
        self.assertTrue(all(r["text"].endswith("Grzegorz Szczepański") for r in res))

    def test_non_pl_signature(self):
        res = plan_reminders([_appt(country="IE")], NOW)
        self.assertTrue(all(r["text"].endswith("Siobhán Ní Dhuibhir") for r in res))

    def test_sms_shortens_to_first_name(self):
        name = "Mary " + "X" * 150
        res = plan_reminders([_appt(customer_name=name, optout_sms_v2=True)], NOW)
        for r in res:
            self.assertTrue(r["text"].startswith("Hi Mary, your"))
            self.assertIn("20 Oct 2026 at 15:00.", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_sms_shortens_to_plain_greeting(self):
        res = plan_reminders([_appt(customer_name="X" * 200, optout_sms_v2=True)], NOW)
        for r in res:
            self.assertTrue(r["text"].startswith("Hello, your Brennan Opticians"))

    def test_sms_length_limit(self):
        for name in ["Aoife Byrne", "Mary " + "X" * 150, "X" * 200, ""]:
            res = plan_reminders([_appt(customer_name=name, optout_sms_v2=True)], NOW)
            for r in res:
                self.assertLessEqual(len(r["text"]), 160)

    def test_unfit_sms_is_omitted_and_warned(self):
        with mock.patch(__name__ + "._signature", return_value="S" * 200):
            with self.assertLogs(log, level="WARNING") as cm:
                res = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual(res, [])
        self.assertEqual(len(cm.records), 1)
        self.assertNotIn(PHONE, cm.output[0])

    def test_sms_helper_returns_none_when_nothing_fits(self):
        local = datetime(2026, 10, 20, 15, 0, tzinfo=DUBLIN)
        self.assertIsNone(_sms_text("Aoife Byrne", local, "S" * 200))


class OutputTests(unittest.TestCase):
    def test_sorted_by_send_at_then_id(self):
        starts = datetime(2026, 10, 20, 14, 0, tzinfo=UTC)
        appts = [
            _appt(id="B", starts_at=starts),
            _appt(id="A", starts_at=starts),
            _appt(id="C", starts_at=datetime(2026, 10, 21, 14, 0, tzinfo=UTC)),
        ]
        res = plan_reminders(appts, NOW)
        keys = [(r["send_at"], r["appointment_id"]) for r in res]
        self.assertEqual(len(res), 6)
        self.assertEqual(keys, sorted(keys))

    def test_result_has_exactly_four_keys(self):
        res = plan_reminders([_appt()], NOW)
        self.assertTrue(all(set(r) == {"appointment_id", "channel", "send_at", "text"}
                            for r in res))

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([_appt()], datetime(2026, 10, 10, 9, 0))

    def test_naive_starts_at_raises_without_leaking_email(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 14, 0))], NOW)
        self.assertNotIn(EMAIL, str(cm.exception))

    def test_no_email_in_output_or_logs(self):
        with self.assertLogs(log, level="INFO") as cm:
            res = plan_reminders([_appt(optout_sms_v2=False),
                                  _appt(id="S1", optout_sms_v2=True)], NOW)
        self.assertTrue(res)
        blob = repr(res) + "\n".join(cm.output)
        self.assertNotIn(EMAIL, blob)
        self.assertNotIn("aoife.byrne", blob)
        self.assertNotIn(PHONE, blob)
        self.assertEqual(len(cm.records), len(res))


if __name__ == "__main__":
    unittest.main()