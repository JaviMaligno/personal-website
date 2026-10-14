"""Appointment reminder planning for Brennan Opticians.

Entry point: plan_reminders(appointments, now) returns a list of dicts with keys
appointment_id, channel ("sms" or "email"), send_at (aware UTC datetime) and text.

Decisions taken from the tech lead's hand-off. Items marked CONFIRM are not yet agreed with the client.
- starts_at <= now: no reminders.
- now before the 48h point: reminders at the 48h point and the 2h point.
- 48h point passed, 2h point still ahead: the 48h reminder moves to now and the 2h reminder keeps its time.
  The hand-off label "only the 2h point has passed" cannot occur, because the 2h point is always later than the 48h point. Its intended case (2h point passed, appointment still ahead) is treated as "both passed".
- 2h point passed (appointment still ahead): one reminder at now.
- Quiet hours [21:00, 08:00) Europe/Dublin, applied to SMS and email (CONFIRM). A send time inside the window moves to 20:00 on the evening before the window started. The reminder is dropped if the moved time is before now, or if now is inside the window. Reminders outside the window are not dropped just because now is inside it.
- Quiet-hours and offset arithmetic: offsets are computed as instants; the window check uses Europe/Dublin wall-clock time.
- Opt-out: only optout_sms_v2 is read. Exactly True means opted out: email if a usable email exists, otherwise nothing. Otherwise a phone gives SMS, else an email gives email, else nothing. The legacy opt_out field is ignored.
- Status: exact match on 'cancelled' only.
- SMS: at most 160 code points. The name is truncated with an ellipsis first and dropped second. Date, time and signature are always kept. If the text still does not fit, the reminder is dropped and a WARNING is logged.
- Signature: "Chevonne Nee Divver", or "Grzegorz Szczepański" when country is PL (case-insensitive).
- Output is sorted by (send_at, appointment_id, slot), with the 48h slot before the 2h slot.
- Privacy: email addresses are never logged or returned except in the email send itself. The house-rule INFO line for email reminders gives the appointment id and channel but withholds the address, which conflicts with the "contact" wording of the house rule. For SMS reminders the phone number is logged masked to its last four digits.
- Deliverability note for the client: the signature for PL contains a non-GSM character, so SMS gateways will likely send that text as UCS-2, which limits a segment to 70 characters, not 160.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
EVENING_SLOT = time(20, 0)
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"

log = logging.getLogger(__name__)


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _require_aware(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _usable_email(appt):
    email = _text(appt.get("email"))
    return email if "@" in email else ""


def _signature(country):
    return SIG_PL if _text(country).upper() == "PL" else SIG_DEFAULT


def _choose_channel(appt):
    if appt.get("optout_sms_v2") is True:
        return "email" if _usable_email(appt) else None
    if _text(appt.get("phone")):
        return "sms"
    if _usable_email(appt):
        return "email"
    return None


def _slots(starts_at, now):
    t48 = starts_at - timedelta(hours=48)
    t2 = starts_at - timedelta(hours=2)
    if now < t48:
        return [(0, t48), (1, t2)]
    if now < t2:
        return [(0, now), (1, t2)]
    return [(0, now)]


def _in_quiet_window(local_time):
    return local_time >= QUIET_START or local_time < QUIET_END


def _quiet_adjust(send_at, now):
    """Return the adjusted send time, or None if the reminder must be dropped."""
    local = send_at.astimezone(DUBLIN)
    if not _in_quiet_window(local.time()):
        return send_at
    if _in_quiet_window(now.astimezone(DUBLIN).time()):
        return None
    if local.time() >= QUIET_START:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    moved = datetime.combine(day, EVENING_SLOT, tzinfo=DUBLIN)
    if moved < now:
        return None
    return moved


def _sms_text(name, date_s, time_s, sig):
    when = f"your appointment at Brennan Opticians is on {date_s} at {time_s}. {sig}"
    if name:
        full = f"Hi {name}, {when}"
        if len(full) <= SMS_LIMIT:
            return full
        prefix = "Hi "
        suffix = f", {when}"
        room = SMS_LIMIT - len(prefix) - len(suffix)
        if room >= 2:
            short = name[: room - 1].rstrip() + "…"
            text = f"{prefix}{short}{suffix}"
            if len(text) <= SMS_LIMIT:
                return text
    bare = f"Reminder: {when}"
    if len(bare) <= SMS_LIMIT:
        return bare
    return None


def _email_text(name, date_s, time_s, sig):
    greet = f"Hello {name}," if name else "Hello,"
    return f"{greet}\n\nYour appointment at Brennan Opticians is on {date_s} at {time_s}.\n\n{sig}"


def _mask_phone(phone):
    digits = "".join(c for c in phone if c.isdigit())
    return "*" * max(len(digits) - 4, 0) + digits[-4:]


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    planned = []
    for appt in appointments:
        if appt.get("status") == "cancelled":
            continue
        appt_id = appt["id"]
        starts_at = appt["starts_at"]
        _require_aware(starts_at, f"starts_at for appointment {appt_id}")
        if starts_at <= now:
            continue
        channel = _choose_channel(appt)
        if channel is None:
            continue
        local_start = starts_at.astimezone(DUBLIN)
        date_s = local_start.strftime("%d/%m/%Y")
        time_s = local_start.strftime("%H:%M")
        sig = _signature(appt.get("country"))
        name = _text(appt.get("customer_name"))
        for slot, when in _slots(starts_at, now):
            send_at = _quiet_adjust(when, now)
            if send_at is None or send_at < now:
                continue
            send_at = send_at.astimezone(UTC)
            if channel == "sms":
                text = _sms_text(name, date_s, time_s, sig)
                if text is None:
                    log.warning(
                        "dropped sms reminder appointment_id=%s: text exceeds %d characters",
                        appt_id, SMS_LIMIT,
                    )
                    continue
                contact = _mask_phone(_text(appt.get("phone")))
            else:
                text = _email_text(name, date_s, time_s, sig)
                contact = "email on file (address withheld)"
            planned.append((send_at, appt_id, slot, channel, text, contact))

    planned.sort(key=lambda p: p[:3])
    result = []
    for send_at, appt_id, _slot, channel, text, contact in planned:
        log.info(
            "planned reminder appointment_id=%s channel=%s to=%s send_at=%s",
            appt_id, channel, contact, send_at.isoformat(),
        )
        result.append({
            "appointment_id": appt_id,
            "channel": channel,
            "send_at": send_at,
            "text": text,
        })
    return result


def _dub(*args):
    return datetime(*args, tzinfo=DUBLIN)


NOW = _dub(2026, 10, 13, 9, 0)


def _appt(**overrides):
    base = {
        "id": 1,
        "customer_name": "Aoife Murphy",
        "email": "aoife@example.com",
        "phone": "+353 87 123 4567",
        "country": "IE",
        "status": "booked",
        "starts_at": _dub(2026, 11, 20, 11, 0),
        "optout_sms_v2": None,
    }
    base.update(overrides)
    return base


class ReminderTests(unittest.TestCase):

    def test_cancelled_gives_nothing(self):
        self.assertEqual(plan_reminders([_appt(status="cancelled")], NOW), [])

    def test_status_match_is_exact(self):
        self.assertEqual(len(plan_reminders([_appt(status="Cancelled")], NOW)), 2)

    def test_default_two_sms_reminders(self):
        out = plan_reminders([_appt()], NOW)
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])
        self.assertEqual(out[0]["send_at"], _dub(2026, 11, 18, 11, 0).astimezone(UTC))
        self.assertEqual(out[1]["send_at"], _dub(2026, 11, 20, 9, 0).astimezone(UTC))

    def test_output_keys_and_aware_send_at(self):
        for r in plan_reminders([_appt()], NOW):
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertIsNotNone(r["send_at"].utcoffset())

    def test_opted_out_with_email_uses_email(self):
        out = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_opted_out_without_email_gets_nothing(self):
        self.assertEqual(plan_reminders([_appt(optout_sms_v2=True, email="")], NOW), [])

    def test_optout_false_uses_sms(self):
        out = plan_reminders([_appt(optout_sms_v2=False)], NOW)
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])

    def test_null_optout_without_phone_uses_email(self):
        out = plan_reminders([_appt(phone="", optout_sms_v2=None)], NOW)
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_no_phone_no_email_gets_nothing(self):
        self.assertEqual(plan_reminders([_appt(phone="", email="")], NOW), [])

    def test_legacy_opt_out_field_ignored(self):
        out = plan_reminders([_appt(opt_out=True)], NOW)
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])

    def test_never_both_channels_for_same_reminder(self):
        out = plan_reminders([_appt(optout_sms_v2=False), _appt(id=2, optout_sms_v2=True)], NOW)
        for r in out:
            self.assertIn(r["channel"], ("sms", "email"))
        per_appt = {}
        for r in out:
            per_appt.setdefault(r["appointment_id"], set()).add(r["channel"])
        self.assertTrue(all(len(c) == 1 for c in per_appt.values()))

    def test_sms_short_name_kept_exactly(self):
        out = plan_reminders([_appt(customer_name="Aoife")], NOW)
        self.assertEqual(
            out[0]["text"],
            "Hi Aoife, your appointment at Brennan Opticians is on 20/11/2026 at 11:00. Chevonne Nee Divver",
        )

    def test_sms_long_name_truncated_keeps_date_time_and_signature(self):
        out = plan_reminders([_appt(customer_name="Ó" * 300)], NOW)
        for r in out:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("20/11/2026 at 11:00", r["text"])
            self.assertTrue(r["text"].endswith("Chevonne Nee Divver"))
            self.assertIn("…", r["text"])

    def test_sms_name_dropped_when_truncation_impossible(self):
        text = _sms_text("X" * 200, "20/11/2026", "11:00", SIG_DEFAULT)
        self.assertLessEqual(len(text), SMS_LIMIT)
        self.assertIn("20/11/2026 at 11:00", text)
        self.assertNotIn("XX", text)

    def test_sms_returns_none_when_it_cannot_fit(self):
        self.assertIsNone(_sms_text("Aoife", "20/11/2026", "11:00", "S" * 200))

    def test_sms_limit_counts_code_points(self):
        text = _sms_text("é" * 200, "20/11/2026", "11:00", SIG_DEFAULT)
        self.assertLessEqual(len(text), SMS_LIMIT)

    def test_pl_signature_case_insensitive(self):
        for country in ("pl", "PL", " Pl "):
            out = plan_reminders([_appt(country=country, optout_sms_v2=False)], NOW)
            for r in out:
                self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))

    def test_pl_signature_on_email(self):
        out = plan_reminders([_appt(country="PL", optout_sms_v2=True)], NOW)
        for r in out:
            self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))

    def test_non_pl_signature(self):
        out = plan_reminders([_appt(country=None)], NOW)
        for r in out:
            self.assertTrue(r["text"].endswith("Chevonne Nee Divver"))

    def test_send_in_window_moves_to_previous_evening(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 11, 20, 9, 30))], NOW)
        self.assertEqual(out[1]["send_at"], _dub(2026, 11, 19, 20, 0).astimezone(UTC))

    def test_evening_in_window_moves_to_same_day_20h(self):
        self.assertEqual(
            _quiet_adjust(_dub(2026, 11, 19, 22, 0), NOW), _dub(2026, 11, 19, 20, 0)
        )

    def test_0800_and_2159_not_in_window(self):
        self.assertEqual(_quiet_adjust(_dub(2026, 11, 20, 8, 0), NOW), _dub(2026, 11, 20, 8, 0))
        self.assertEqual(_quiet_adjust(_dub(2026, 11, 19, 20, 59), NOW), _dub(2026, 11, 19, 20, 59))

    def test_moved_time_before_now_dropped(self):
        now = _dub(2026, 11, 19, 20, 30)
        self.assertIsNone(_quiet_adjust(_dub(2026, 11, 20, 7, 0), now))

    def test_now_inside_window_drops_shifted_reminder(self):
        now = _dub(2026, 11, 19, 22, 0)
        self.assertIsNone(_quiet_adjust(_dub(2026, 11, 20, 7, 0), now))

    def test_48h_offset_is_elapsed_time_across_dst_end(self):
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 26, 9, 0))], NOW)
        self.assertEqual(out[0]["send_at"], datetime(2026, 10, 24, 9, 0, tzinfo=UTC))

    def test_quiet_hours_use_dublin_wall_clock_across_dst(self):
        expected = datetime(2026, 10, 24, 19, 0, tzinfo=UTC)
        self.assertEqual(_quiet_adjust(datetime(2026, 10, 25, 3, 0, tzinfo=UTC), NOW), expected)
        self.assertEqual(_quiet_adjust(datetime(2026, 10, 25, 0, 30, tzinfo=UTC), NOW), expected)
        self.assertEqual(_quiet_adjust(datetime(2026, 10, 25, 1, 30, tzinfo=UTC), NOW), expected)

    def test_starts_in_past_or_now_gives_nothing(self):
        self.assertEqual(plan_reminders([_appt(starts_at=NOW - timedelta(hours=1))], NOW), [])
        self.assertEqual(plan_reminders([_appt(starts_at=NOW)], NOW), [])

    def test_only_48h_passed_sends_first_now_and_keeps_2h(self):
        now = _dub(2026, 11, 18, 12, 0)
        out = plan_reminders([_appt()], now)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], now.astimezone(UTC))
        self.assertEqual(out[1]["send_at"], _dub(2026, 11, 20, 9, 0).astimezone(UTC))

    def test_both_passed_gives_one_reminder_at_now(self):
        now = _dub(2026, 11, 20, 9, 30)
        out = plan_reminders([_appt()], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], now.astimezone(UTC))

    def test_never_returns_send_at_before_now(self):
        for now in (NOW, _dub(2026, 11, 18, 12, 0), _dub(2026, 11, 20, 9, 30), _dub(2026, 11, 19, 22, 0)):
            for r in plan_reminders([_appt(), _appt(id=2, starts_at=_dub(2026, 11, 19, 9, 0))], now):
                self.assertGreaterEqual(r["send_at"], now)

    def test_sort_by_send_at_then_id_then_48h_before_2h(self):
        out = plan_reminders([_appt(id=2), _appt(id=1)], NOW)
        keys = [(r["send_at"], r["appointment_id"]) for r in out]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([r["appointment_id"] for r in out], [1, 2, 1, 2])

    def test_sort_tie_puts_48h_slot_first(self):
        a = _appt(id=7, starts_at=_dub(2026, 11, 20, 11, 0))
        b = _appt(id=7, starts_at=_dub(2026, 11, 18, 13, 0))
        out = plan_reminders([b, a], NOW)
        self.assertEqual(out[0]["send_at"], out[1]["send_at"])
        self.assertIn("20/11/2026", out[0]["text"])
        self.assertIn("18/11/2026", out[1]["text"])

    def test_logs_one_line_per_reminder_without_email(self):
        with self.assertLogs(level="INFO") as cm:
            out = plan_reminders([_appt(optout_sms_v2=True, email="secret.person@example.com")], NOW)
        self.assertEqual(len(cm.records), len(out))
        logs = "\n".join(cm.output)
        self.assertNotIn("secret.person", logs)
        self.assertNotIn("@", logs)

    def test_phone_is_masked_in_logs(self):
        with self.assertLogs(level="INFO") as cm:
            plan_reminders([_appt()], NOW)
        logs = "\n".join(cm.output)
        self.assertNotIn("871234", logs)
        self.assertIn("4567", logs)

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([_appt(starts_at=datetime(2026, 11, 20, 11, 0))], NOW)


if __name__ == "__main__":
    unittest.main()