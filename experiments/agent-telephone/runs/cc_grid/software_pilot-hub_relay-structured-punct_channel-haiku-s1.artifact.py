"""Brennan Opticians appointment reminders.

Public entry point: plan_reminders(appointments, now).

Report (OPEN items and deviations):
- R5 date format DD/MM/YYYY, set in DATE_FORMAT (OPEN, client to confirm). Times are HH:MM 24-hour, Europe/Dublin.
- R8 if the 2h point has already passed, that reminder is skipped (OPEN, client to confirm). Appointments that have already started get no reminders (assumption, logged as a warning).
- R10 SMS rule (OPEN, client decision): the client wording is contradictory. Default in _sms_allowed(): SMS only when a phone number exists and optout_sms_v2 is exactly False (or 0). A missing or None flag is treated as opted out. Customers who opted out get no reminder, and no email is sent instead, because the client said "Don't email them instead". The "email" channel is therefore never produced. The email field is not read or logged.
- R11 each reminder has exactly one channel.
- R12 SMS text is limited to 160 characters by len(). The customer name is shortened with an ellipsis (U+2026). The date, time and signature are never truncated. The signature has non-GSM-7 characters (á, í, ń, ł), so the message is likely UCS-2. Under UCS-2 a single segment holds 70 characters and concatenated segments hold 67 each, so the 160-character budget does not keep the message to one segment. Client to decide whether this is acceptable.
- R13 quiet hours are blocked from 21:00 up to 07:59:59 Europe/Dublin local time. 08:00 is allowed. A send time at or after 21:00 moves back to 20:00 the same local day. A send time before 08:00 moves back to 20:00 of the previous local day, since 20:00 of the same day would be later. Conversion uses zoneinfo, so DST is handled. If the adjusted time falls before now, the reminder is skipped to keep R9, and a WARNING is logged. This happens, for example, when now is after 21:00 local time.
- R15 email addresses are never logged, printed or returned, because the email channel is unused.
- R16 signature is "Siobhán Ní Dhuibhir", or "Grzegorz Szczepański" when country is "PL".
- R19 sort key is (send_at, str(appointment_id), reminder order), with the first reminder before the second.
- Logging: one INFO line per planned reminder with appointment id, channel, contact and send time. For SMS the contact is the phone number, which is personal data and is logged as the house rule requires.
- Arithmetic is done in UTC to avoid wall-clock errors across DST.
- Test status: the tests below were written but have NOT been executed. Run with: python -I -m unittest <absolute path to this file>
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_CHARS = 160
DATE_FORMAT = "%d/%m/%Y"  # OPEN R5
TIME_FORMAT = "%H:%M"
LEAD_FIRST = timedelta(hours=48)
LEAD_SECOND = timedelta(hours=2)
QUIET_BLOCK_FROM_MIN = 21 * 60  # 21:00 is blocked
QUIET_ALLOW_FROM_MIN = 8 * 60   # 08:00 is allowed
QUIET_TARGET = time(20, 0)
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
ELLIPSIS = "\u2026"


def _clean(value):
    return value.strip() if isinstance(value, str) else ""


def _sms_allowed(appt):
    # OPEN R10: text only if a phone exists and optout_sms_v2 is exactly False (or 0).
    # Missing or None is treated as opted out. The legacy opt_out field is never read.
    return bool(_clean(appt.get("phone"))) and appt.get("optout_sms_v2") in (False, 0)


def _channel(appt):
    # R10/R11: one channel per reminder. Email is never selected (client: "Don't email them instead").
    return "sms" if _sms_allowed(appt) else None


def _quiet_adjust(point_utc):
    # R13: move a send time in the quiet window back to 20:00 Europe/Dublin.
    local = point_utc.astimezone(DUBLIN)
    minute = local.hour * 60 + local.minute
    if minute >= QUIET_BLOCK_FROM_MIN:
        anchor = local.date()
    elif minute < QUIET_ALLOW_FROM_MIN:
        anchor = local.date() - timedelta(days=1)
    else:
        return point_utc
    return datetime.combine(anchor, QUIET_TARGET, tzinfo=DUBLIN).astimezone(UTC)


def _body(name, date_s, time_s, sig):
    greeting = f"Hi {name}" if name else "Hi"
    return f"{greeting}, your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"


def _sms_text(name, date_s, time_s, sig):
    # R12: keep date, time and signature. Shorten the name if the text exceeds 160 characters.
    text = _body(name, date_s, time_s, sig)
    if len(text) <= SMS_MAX_CHARS:
        return text
    room = SMS_MAX_CHARS - len(_body("", date_s, time_s, sig)) - 1
    if room >= 4:
        text = _body(name[:room - 1] + ELLIPSIS, date_s, time_s, sig)
    else:
        text = _body("", date_s, time_s, sig)
    if len(text) > SMS_MAX_CHARS:
        logger.warning("SMS text is %d characters after truncation; date, time and signature kept", len(text))
    return text


def plan_reminders(appointments, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    planned = []

    for appt in appointments or []:
        appt_id = appt.get("id")

        # R14
        if _clean(appt.get("status")).lower() == "cancelled":
            continue

        channel = _channel(appt)
        if channel is None:
            logger.debug("no reminder for appointment_id=%s: SMS not permitted", appt_id)
            continue

        starts_at = appt.get("starts_at")
        if not isinstance(starts_at, datetime) or starts_at.utcoffset() is None:
            logger.warning("no reminders for appointment_id=%s: starts_at missing or naive", appt_id)
            continue

        starts = starts_at.astimezone(UTC)
        if starts <= now_utc:
            logger.warning("no reminders for appointment_id=%s: start time already passed", appt_id)
            continue

        starts_local = starts.astimezone(DUBLIN)
        date_s = starts_local.strftime(DATE_FORMAT)
        time_s = starts_local.strftime(TIME_FORMAT)
        name = _clean(appt.get("customer_name"))
        sig = SIG_PL if _clean(appt.get("country")).upper() == "PL" else SIG_DEFAULT
        text = _sms_text(name, date_s, time_s, sig)
        phone = _clean(appt.get("phone"))

        for order, lead in enumerate((LEAD_FIRST, LEAD_SECOND)):
            point = starts - lead
            if point < now_utc:
                if order == 1:  # OPEN R8: 2h point already passed, skip
                    continue
                point = now_utc  # R8: first reminder moves to now

            send_at = _quiet_adjust(point)  # R13
            if send_at < now_utc:  # R9 wins over R13 when they conflict
                logger.warning(
                    "skipping reminder %d for appointment_id=%s: quiet-hours adjustment %s is before now",
                    order + 1, appt_id, send_at.isoformat(),
                )
                continue

            planned.append((
                (send_at, str(appt_id), order),
                {"appointment_id": appt_id, "channel": channel, "send_at": send_at, "text": text},
            ))
            logger.info(
                "planned reminder %d for appointment_id=%s channel=%s contact=%s send_at=%s",
                order + 1, appt_id, channel, phone, send_at.isoformat(),
            )

    planned.sort(key=lambda item: item[0])  # R19
    return [item[1] for item in planned]


class ReminderTests(unittest.TestCase):
    NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)

    def appt(self, **overrides):
        base = {
            "id": "A1",
            "customer_name": "Aoife Murphy",
            "email": "aoife@example.com",
            "phone": "+353851234567",
            "country": "IE",
            "status": "booked",
            "starts_at": datetime(2026, 10, 20, 14, 0, tzinfo=DUBLIN),
            "optout_sms_v2": False,
        }
        base.update(overrides)
        return base

    def test_r7_reminders_at_48h_and_2h(self):
        a = self.appt()
        out = plan_reminders([a], self.NOW)
        starts = a["starts_at"].astimezone(UTC)
        self.assertEqual([r["send_at"] for r in out],
                         [starts - timedelta(hours=48), starts - timedelta(hours=2)])
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_r8_r9_first_reminder_moves_to_now(self):
        now = datetime(2026, 10, 13, 13, 0, tzinfo=UTC)
        starts = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
        out = plan_reminders([self.appt(starts_at=starts)], now)
        self.assertEqual(out[0]["send_at"], now)
        self.assertEqual(out[1]["send_at"], starts - timedelta(hours=2))
        for r in out:
            self.assertGreaterEqual(r["send_at"], now)

    def test_r12_sms_limit_keeps_date_time_signature(self):
        out = plan_reminders([self.appt(customer_name="X" * 300,
                                        starts_at=datetime(2026, 10, 15, 12, 0, tzinfo=UTC))], self.NOW)
        self.assertTrue(out)
        for r in out:
            self.assertLessEqual(len(r["text"]), SMS_MAX_CHARS)
            self.assertIn("15/10/2026", r["text"])
            self.assertIn("13:00", r["text"])
            self.assertTrue(r["text"].endswith(SIG_DEFAULT))

    def test_r13_quiet_hours_move_to_2000_summer_time(self):
        starts = datetime(2026, 10, 20, 23, 30, tzinfo=DUBLIN)
        out = plan_reminders([self.appt(starts_at=starts)], self.NOW)
        self.assertEqual([r["send_at"] for r in out],
                         [datetime(2026, 10, 18, 19, 0, tzinfo=UTC),
                          datetime(2026, 10, 20, 19, 0, tzinfo=UTC)])

    def test_r13_quiet_hours_move_to_2000_winter_time(self):
        starts = datetime(2026, 11, 2, 23, 0, tzinfo=DUBLIN)
        out = plan_reminders([self.appt(starts_at=starts)], self.NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[-1]["send_at"], datetime(2026, 11, 2, 20, 0, tzinfo=UTC))

    def test_r14_cancelled_gets_no_reminders(self):
        self.assertEqual(plan_reminders([self.appt(status="cancelled")], self.NOW), [])

    def test_r16_polish_signature(self):
        out = plan_reminders([self.appt(country="PL")], self.NOW)
        self.assertTrue(out)
        for r in out:
            self.assertTrue(r["text"].endswith(SIG_PL))
            self.assertNotIn(SIG_DEFAULT, r["text"])

    def test_r6_uses_optout_sms_v2_only(self):
        self.assertEqual(plan_reminders([self.appt(optout_sms_v2=True)], self.NOW), [])
        self.assertEqual(len(plan_reminders([self.appt(optout_sms_v2=False, opt_out=True)], self.NOW)), 2)

    def test_r2_missing_phone_or_email_does_not_raise(self):
        self.assertEqual(plan_reminders([self.appt(phone=None, email=None)], self.NOW), [])
        self.assertEqual(len(plan_reminders([self.appt(email=None)], self.NOW)), 2)

    def test_r19_sorted_with_tie_breaker(self):
        starts = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
        out = plan_reminders(
            [self.appt(id="b", starts_at=starts), self.appt(id="a", starts_at=starts)],
            datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        )
        self.assertEqual([r["appointment_id"] for r in out], ["a", "b", "a", "b"])
        sends = [r["send_at"] for r in out]
        self.assertEqual(sends, sorted(sends))

    def test_logs_never_contain_email(self):
        with self.assertLogs(level="INFO") as cm:
            plan_reminders([self.appt(email="secret.person@example.com")], self.NOW)
        self.assertTrue(cm.output)
        self.assertFalse(any("secret.person" in line or "@" in line for line in cm.output))


if __name__ == "__main__":
    unittest.main()