import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

# ASSUMPTION: reminder 1 is 48h before the appointment (brief).
REMINDER_1_OFFSET = timedelta(hours=48)
# ASSUMPTION: reminder 2 is 2h before the appointment (brief's "2-hour reminder" scope note).
REMINDER_2_OFFSET = timedelta(hours=2)

QUIET_START = time(21, 0)  # inclusive, blocked
QUIET_END = time(8, 0)     # exclusive, allowed
SHIFT_TO = time(20, 0)     # quiet-hours shift target
# ASSUMPTION: when a shifted time is already past, send at the next 08:00 Dublin.
MORNING_SEND = time(8, 0)

SMS_MAX_LENGTH = 160
SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
# ASSUMPTION: email subject for the sender, flagged for client. Not part of the output shape.
EMAIL_SUBJECT = "Your appointment reminder - Brennan Opticians"

CHANNEL_SMS = "sms"
CHANNEL_EMAIL = "email"

# ASSUMPTION: date rendered as DD Mon YYYY with a fixed English month list (locale-independent).
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _is_present(value):
    return isinstance(value, str) and value.strip() != ""


def _is_cancelled(status):
    return isinstance(status, str) and status.strip().lower() == "cancelled"


def _is_opted_out(flag):
    # ASSUMPTION: only the exact boolean False means not opted out.
    return flag is not False


def _signature_for(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIGNATURE_PL
    return SIGNATURE_DEFAULT


def _require_aware(value, label):
    # Message deliberately contains no customer fields.
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _apply_quiet_shift(candidate_utc):
    local = candidate_utc.astimezone(DUBLIN)
    wall = local.time()
    if wall >= QUIET_START:
        day = local.date()
    elif wall < QUIET_END:
        # ASSUMPTION: 00:00-07:59 on day D shifts to 20:00 on day D-1.
        day = local.date() - timedelta(days=1)
    else:
        return candidate_utc
    return datetime.combine(day, SHIFT_TO, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(now_utc):
    # ASSUMPTION: first 08:00 Dublin strictly after now.
    today = now_utc.astimezone(DUBLIN).date()
    morning = datetime.combine(today, MORNING_SEND, tzinfo=DUBLIN).astimezone(UTC)
    if morning <= now_utc:
        morning = datetime.combine(
            today + timedelta(days=1), MORNING_SEND, tzinfo=DUBLIN
        ).astimezone(UTC)
    return morning


def _finalise(candidate_utc, now_utc, starts_utc):
    send = _apply_quiet_shift(candidate_utc)
    if send < now_utc:
        send = _next_morning(now_utc)
    if now_utc <= send < starts_utc:
        return send
    return None


def _schedule(starts_utc, now_utc):
    """Return [(order, send_utc)] for reminders 1 and 2 after all timing rules."""
    if starts_utc <= now_utc:
        return []
    candidates = []
    nominal1 = starts_utc - REMINDER_1_OFFSET
    candidates.append((1, now_utc if nominal1 < now_utc else nominal1))
    nominal2 = starts_utc - REMINDER_2_OFFSET
    # ASSUMPTION: reminder 2 is dropped when its nominal time has already passed.
    if nominal2 >= now_utc:
        candidates.append((2, nominal2))
    planned = []
    for order, cand in candidates:
        send = _finalise(cand, now_utc, starts_utc)
        if send is not None:
            planned.append((order, send))
    # ASSUMPTION: if both collapse to the same send_at, keep the reminder 2 entry.
    if len(planned) == 2 and planned[0][1] == planned[1][1]:
        planned = planned[1:]
    return planned


def _format_date(local_dt):
    return f"{local_dt.day:02d} {_MONTHS[local_dt.month - 1]} {local_dt.year}"


def _name_forms(customer_name):
    """Name forms in shortening order: full name, first name only, no name."""
    if not _is_present(customer_name):
        return [None]
    full = " ".join(customer_name.split())
    return [full, full.split(" ")[0], None]


def _build_text(name, local_start, signature):
    greeting = f"Hi {name}," if name else "Hi,"
    return (f"{greeting} reminder of your appointment at Brennan Opticians on "
            f"{_format_date(local_start)} at {local_start.strftime('%H:%M')}. {signature}")


def _sms_text(customer_name, local_start, signature, appointment_id):
    for name in _name_forms(customer_name):
        text = _build_text(name, local_start, signature)
        if len(text) <= SMS_MAX_LENGTH:
            return text
    # Never truncate the signature, date or time.
    raise ValueError(
        f"SMS for appointment_id={appointment_id!r} exceeds {SMS_MAX_LENGTH} characters"
    )


def _recipient_label(channel, phone):
    if channel == CHANNEL_SMS:
        s = phone.strip()
        tail = s[-4:] if len(s) >= 4 else "****"
        return f"sms to phone ending {tail}"
    return "email to address on file"


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    now_utc = now.astimezone(UTC)
    planned = []

    for appt in appointments:
        appt_id = appt.get("id")
        starts = appt.get("starts_at")
        _require_aware(starts, f"starts_at of appointment_id={appt_id!r}")
        starts_utc = starts.astimezone(UTC)

        if _is_cancelled(appt.get("status")):
            logger.debug("no reminders appointment_id=%s reason=cancelled", appt_id)
            continue

        schedule = _schedule(starts_utc, now_utc)
        if not schedule:
            continue

        phone = appt.get("phone")
        email = appt.get("email")
        customer_name = appt.get("customer_name")
        signature = _signature_for(appt.get("country"))
        local_start = starts.astimezone(DUBLIN)
        opted_out = _is_opted_out(appt.get("optout_sms_v2"))

        if _is_present(phone) and not opted_out:
            channel = CHANNEL_SMS
        elif _is_present(email):
            channel = CHANNEL_EMAIL
        else:
            reason = "opted_out_no_email" if _is_present(phone) else "no_contact"
            for order, _ in schedule:
                logger.warning(
                    "reminder dropped appointment_id=%s reminder=%d reason=%s",
                    appt_id, order, reason,
                )
            continue

        for order, send_utc in schedule:
            if channel == CHANNEL_SMS:
                text = _sms_text(customer_name, local_start, signature, appt_id)
                contact_phone = phone
            else:
                text = _build_text(_name_forms(customer_name)[0], local_start, signature)
                contact_phone = None
            item = {
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_utc,
                "text": text,
            }
            planned.append((send_utc, appt_id, order, item))
            # Contact is masked for SMS and omitted for email, per the privacy rules.
            logger.info(
                "planned reminder appointment_id=%s channel=%s send_at=%s recipient=%s",
                appt_id, channel, send_utc.isoformat(),
                _recipient_label(channel, contact_phone or ""),
            )

    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    return [p[3] for p in planned]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

import logging as _logging  # noqa: E402

SMS_PHONE = "+353870000001"
EMAIL_ADDR = "aoife@example.com"


def _dub(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=DUBLIN)


def _appt(**overrides):
    base = {
        "id": 1,
        "customer_name": "Aoife Murphy",
        "email": EMAIL_ADDR,
        "phone": SMS_PHONE,
        "country": "IE",
        "status": "booked",
        "starts_at": _dub(2026, 10, 16, 10),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


class PlanRemindersTests(unittest.TestCase):

    def test_example_a_both_sms(self):
        out = plan_reminders([_appt()], _dub(2026, 10, 13, 10))
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])
        self.assertEqual(out[0]["send_at"], _dub(2026, 10, 14, 10))
        self.assertEqual(out[1]["send_at"], _dub(2026, 10, 16, 8))
        self.assertEqual(out[0]["send_at"].utcoffset(), timedelta(0))
        self.assertEqual(set(out[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertIn("on 16 Oct 2026 at 10:00.", out[0]["text"])
        self.assertTrue(out[0]["text"].endswith(SIGNATURE_DEFAULT))

    def test_example_b_reminder2_shifted_from_0700(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 16, 9))], _dub(2026, 10, 13, 10))
        self.assertEqual(out[1]["send_at"], _dub(2026, 10, 15, 20))

    def test_example_c_both_shifted_to_2000(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 15, 23))], _dub(2026, 10, 13, 10))
        self.assertEqual([r["send_at"] for r in out],
                         [_dub(2026, 10, 13, 20), _dub(2026, 10, 15, 20)])

    def test_example_d_reminder1_clamped_to_now(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 14, 18))], _dub(2026, 10, 14, 12))
        self.assertEqual(out[0]["send_at"], _dub(2026, 10, 14, 12))

    def test_example_d_reminder2_kept_per_section_3_rules(self):
        # NOTE: acceptance example D says reminder 2 is dropped. Section 3 keeps it
        # (16:00 is after now and not collapsed). This follows the rules; PM to confirm.
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 14, 18))], _dub(2026, 10, 14, 12))
        self.assertEqual(len(out), 2)
        self.assertEqual(out[1]["send_at"], _dub(2026, 10, 14, 16))

    def test_example_e_now_inside_window(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 15, 12))], _dub(2026, 10, 14, 23))
        self.assertEqual([r["send_at"] for r in out],
                         [_dub(2026, 10, 15, 8), _dub(2026, 10, 15, 10)])

    def test_example_f_past_start_no_reminders(self):
        now = _dub(2026, 10, 13, 10)
        self.assertEqual(plan_reminders([_appt(starts_at=now)], now), [])
        self.assertEqual(plan_reminders([_appt(starts_at=now - timedelta(hours=1))], now), [])

    def test_example_g_cancelled_any_case(self):
        out = plan_reminders([_appt(status="CANCELLED")], _dub(2026, 10, 13, 10))
        self.assertEqual(out, [])

    def test_example_h_opted_out_no_email(self):
        with self.assertLogs(level="WARNING"):
            out = plan_reminders([_appt(optout_sms_v2=True, email=None)],
                                 _dub(2026, 10, 13, 10))
        self.assertEqual(out, [])

    def test_example_i_opted_out_uses_email(self):
        out = plan_reminders([_appt(optout_sms_v2=True)], _dub(2026, 10, 13, 10))
        self.assertEqual([r["channel"] for r in out], ["email", "email"])
        self.assertEqual([r["send_at"] for r in out],
                         [_dub(2026, 10, 14, 10), _dub(2026, 10, 16, 8)])
        self.assertIn("Hi Aoife Murphy,", out[0]["text"])

    def test_example_j_polish_signature(self):
        out = plan_reminders([_appt(country=" pl ")], _dub(2026, 10, 13, 10))
        self.assertTrue(all(r["text"].endswith(SIGNATURE_PL) for r in out))

    def test_example_k_long_name_shortened_to_first_name(self):
        name = "Bartholomew Maximilian Fitzgerald-Montgomery-Smythe-Worthington"
        out = plan_reminders([_appt(customer_name=name)], _dub(2026, 10, 13, 10))
        text = out[0]["text"]
        self.assertTrue(text.startswith("Hi Bartholomew, "))
        self.assertLessEqual(len(text), SMS_MAX_LENGTH)
        self.assertIn("on 16 Oct 2026 at 10:00.", text)
        self.assertTrue(text.endswith(SIGNATURE_DEFAULT))

    def test_example_k_first_name_too_long_drops_name(self):
        name = "A" * 70 + " Smith"
        out = plan_reminders([_appt(customer_name=name)], _dub(2026, 10, 13, 10))
        text = out[0]["text"]
        self.assertTrue(text.startswith("Hi, reminder of your appointment"))
        self.assertIn("on 16 Oct 2026 at 10:00.", text)
        self.assertTrue(text.endswith(SIGNATURE_DEFAULT))
        self.assertLessEqual(len(text), SMS_MAX_LENGTH)

    def test_dst_shift_across_end_of_summer_time(self):
        # 25 Oct 2026 is the DST end in Dublin; 20:00 that day is UTC+0.
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 26, 9))], _dub(2026, 10, 13, 10))
        self.assertEqual(out[1]["send_at"], datetime(2026, 10, 25, 20, 0, tzinfo=UTC))

    def test_collapse_keeps_one_entry(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 15, 9))], _dub(2026, 10, 14, 22))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], _dub(2026, 10, 15, 8))

    def test_both_past_sends_reminder1_now_only(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 14, 13))], _dub(2026, 10, 14, 12))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], _dub(2026, 10, 14, 12))

    def test_morning_fallback_past_start_dropped(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 15, 7, 30))],
                             _dub(2026, 10, 14, 22))
        self.assertEqual(out, [])

    def test_sorted_by_send_at_then_id(self):
        appts = [
            _appt(id=1, starts_at=_dub(2026, 10, 16, 10)),
            _appt(id=2, starts_at=_dub(2026, 10, 15, 12)),
        ]
        out = plan_reminders(appts, _dub(2026, 10, 13, 10))
        self.assertEqual([(r["appointment_id"], r["send_at"]) for r in out], [
            (2, _dub(2026, 10, 13, 12)),
            (1, _dub(2026, 10, 14, 10)),
            (2, _dub(2026, 10, 15, 10)),
            (1, _dub(2026, 10, 16, 8)),
        ])

    def test_missing_optout_key_counts_as_opted_out(self):
        a = _appt(email=None)
        del a["optout_sms_v2"]
        with self.assertLogs(level="WARNING"):
            self.assertEqual(plan_reminders([a], _dub(2026, 10, 13, 10)), [])

    def test_non_boolean_optout_counts_as_opted_out(self):
        with self.assertLogs(level="WARNING"):
            out = plan_reminders([_appt(optout_sms_v2=0, email=None)], _dub(2026, 10, 13, 10))
        self.assertEqual(out, [])

    def test_whitespace_phone_falls_back_to_email(self):
        out = plan_reminders([_appt(phone="   ")], _dub(2026, 10, 13, 10))
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_non_string_phone_is_missing(self):
        out = plan_reminders([_appt(phone=12345)], _dub(2026, 10, 13, 10))
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_naive_now_rejected_without_customer_fields(self):
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([_appt()], datetime(2026, 10, 13, 10))
        self.assertNotIn("example.com", str(ctx.exception))
        self.assertNotIn("Aoife", str(ctx.exception))

    def test_naive_starts_at_rejected_without_email(self):
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([_appt(starts_at=datetime(2026, 10, 16, 10))],
                           _dub(2026, 10, 13, 10))
        self.assertNotIn("example.com", str(ctx.exception))

    def test_logs_one_info_per_reminder_without_email(self):
        with self.assertLogs(level="INFO") as cm:
            out = plan_reminders([_appt()], _dub(2026, 10, 13, 10))
        infos = [r for r in cm.records if r.levelno == _logging.INFO]
        self.assertEqual(len(infos), len(out))
        joined = "\n".join(cm.output)
        self.assertNotIn(EMAIL_ADDR, joined)
        self.assertNotIn(SMS_PHONE, joined)


if __name__ == "__main__":
    unittest.main()