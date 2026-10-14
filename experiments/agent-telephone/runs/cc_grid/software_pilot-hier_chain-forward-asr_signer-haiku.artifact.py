from __future__ import annotations

import logging
import unittest
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

DUBLIN = ZoneInfo("Europe/Dublin")
LEAD_48H = timedelta(hours=48)
LEAD_2H = timedelta(hours=2)
EVENING_SEND = time(20, 0)
MORNING_END = time(8, 0)
SMS_MAX_CHARS = 160
ACTIVE_STATUSES = frozenset({"booked", "confirmed", "scheduled"})  # to be confirmed by Brennan
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
OPT_OUT_TRUE_VALUES = frozenset({"true", "1", "yes"})
SIGNATURE_DEFAULT = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"
WARNING_REASONS = frozenset({"invalid_appointment", "missing_status", "unknown_status", "unexpected_error"})

logger = logging.getLogger("brennan_reminders")


# ---------- timing ----------

def in_quiet_window(dt):
    hour = dt.astimezone(DUBLIN).hour
    return hour >= 21 or hour < 8


def _dublin_at(day, t):
    return datetime.combine(day, t, tzinfo=DUBLIN).astimezone(timezone.utc)


def quiet_shift(nominal_utc):
    local = nominal_utc.astimezone(DUBLIN)
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    return _dublin_at(day, EVENING_SEND)


def next_0800_at_or_after(dt):
    local = dt.astimezone(DUBLIN)
    day = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    return _dublin_at(day, MORNING_END)


def resolve_send_time(nominal_utc, now_utc, starts_utc):
    shifted = quiet_shift(nominal_utc) if in_quiet_window(nominal_utc) else nominal_utc
    final = max(shifted, now_utc)
    if in_quiet_window(final):
        final = next_0800_at_or_after(final)
    if final >= starts_utc:
        return None
    return final


# ---------- messages ----------

def signature_for(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIGNATURE_PL
    return SIGNATURE_DEFAULT


def _sms_text(name, date_s, time_s, signature):
    if name:
        return f"Hi {name}, reminder of your Brennan Opticians appointment on {date_s} at {time_s}. {signature}"
    return f"Hi, reminder of your Brennan Opticians appointment on {date_s} at {time_s}. {signature}"


def render_sms(name, date_s, time_s, signature):
    full = _sms_text(name, date_s, time_s, signature)
    if len(full) <= SMS_MAX_CHARS or not name:
        return full
    for k in range(len(name) - 1, 0, -1):
        candidate = name[:k].rstrip() + "..."
        text = _sms_text(candidate, date_s, time_s, signature)
        if len(text) <= SMS_MAX_CHARS:
            return text
    return _sms_text("", date_s, time_s, signature)


def render_email(name, date_s, time_s, signature):
    greeting = f"Dear {name}," if name else "Hello,"
    return (
        f"{greeting}\n\n"
        f"This is a reminder of your appointment at Brennan Opticians on {date_s} at {time_s}.\n\n"
        f"Kind regards,\n{signature}"
    )


# ---------- routing ----------

def opted_out(appt):
    value = appt.get("optout_sms_v2")
    if value is True:
        return True
    return isinstance(value, str) and value.strip().lower() in OPT_OUT_TRUE_VALUES


def _usable_email(value):
    return isinstance(value, str) and bool(value.strip()) and "@" in value


def _usable_phone(value):
    return isinstance(value, str) and bool(value.strip())


def choose_channel(appt):
    email_ok = _usable_email(appt.get("email"))
    if opted_out(appt):
        return "email" if email_ok else None
    if _usable_phone(appt.get("phone")):
        return "sms"
    if email_ok:
        return "email"
    return None


def _status_reason(appt):
    status = appt.get("status")
    if not isinstance(status, str) or not status.strip():
        return "missing_status"
    normalised = status.strip().lower()
    if normalised in CANCELLED_STATUSES:
        return "cancelled"
    if normalised in ACTIVE_STATUSES:
        return None
    return "unknown_status"


# ---------- planning ----------

def _is_aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _skip(appt_id, reason):
    level = logging.WARNING if reason in WARNING_REASONS else logging.INFO
    logger.log(level, "skip appointment_id=%s reason=%s", appt_id, reason)


def _send_times(starts_utc, now_utc, appt_id):
    t2 = starts_utc - LEAD_2H
    t48 = starts_utc - LEAD_48H
    if now_utc >= t2:
        r = resolve_send_time(now_utc, now_utc, starts_utc)
        return [r] if r is not None else []
    r48 = resolve_send_time(max(t48, now_utc), now_utc, starts_utc)
    r2 = resolve_send_time(t2, now_utc, starts_utc)
    times = []
    if r48 is not None:
        if r2 is None or r48 < r2:
            times.append(r48)
        else:
            logger.info("skip appointment_id=%s reason=collapsed_48h_into_2h", appt_id)
    if r2 is not None:
        times.append(r2)
    return times


def _plan_one(appt, now_utc):
    if not isinstance(appt, Mapping):
        _skip(None, "invalid_appointment")
        return []
    appt_id = appt.get("id")
    if appt_id is None or (isinstance(appt_id, str) and not appt_id.strip()):
        _skip(None, "invalid_appointment")
        return []
    starts = appt.get("starts_at")
    if not _is_aware(starts):
        _skip(appt_id, "invalid_appointment")
        return []

    reason = _status_reason(appt)
    if reason == "unknown_status":
        logger.warning("skip appointment_id=%s reason=%s status=%r",
                       appt_id, reason, appt.get("status"))
        return []
    if reason is not None:
        _skip(appt_id, reason)
        return []

    channel = choose_channel(appt)
    if channel is None:
        _skip(appt_id, "no_contact_route")
        return []

    starts_utc = starts.astimezone(timezone.utc)
    if starts_utc <= now_utc:
        _skip(appt_id, "past_appointment")
        return []

    send_times = _send_times(starts_utc, now_utc, appt_id)
    if not send_times:
        _skip(appt_id, "no_valid_send_time")
        return []

    local_start = starts.astimezone(DUBLIN)
    date_s = local_start.strftime("%d/%m/%Y")
    time_s = local_start.strftime("%H:%M")
    signature = signature_for(appt.get("country"))
    name = appt.get("customer_name")
    name = name.strip() if isinstance(name, str) else ""

    if channel == "sms":
        text = render_sms(name, date_s, time_s, signature)
    else:
        text = render_email(name, date_s, time_s, signature)

    reminders = []
    for send_at in send_times:
        reminders.append({
            "appointment_id": appt_id,
            "channel": channel,
            "send_at": send_at,
            "text": text,
        })
        # Contact values (email, phone, name) and message text are deliberately not logged.
        # appointment_id plus channel is the support trace key.
        logger.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                    appt_id, channel, send_at.isoformat())
    return reminders


def _safe_id(appt):
    try:
        return appt.get("id") if isinstance(appt, Mapping) else None
    except Exception:
        return None


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(timezone.utc)

    result = []
    total = 0
    skipped = 0
    for appt in appointments or ():
        total += 1
        try:
            reminders = _plan_one(appt, now_utc)
        except Exception as exc:
            logger.warning("skip appointment_id=%s reason=unexpected_error error=%s",
                           _safe_id(appt), type(exc).__name__)
            reminders = []
        if reminders:
            result.extend(reminders)
        else:
            skipped += 1

    result.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"], r["text"]))
    logger.info("run summary appointments=%d reminders=%d skipped=%d",
                total, len(result), skipped)
    return result


# ---------- self-tests ----------

def _dub(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=DUBLIN)


def _utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


class _Tests(unittest.TestCase):
    def appt(self, starts, **overrides):
        base = {
            "id": 1,
            "customer_name": "Aoife Murphy",
            "email": "aoife@example.com",
            "phone": "+353870000000",
            "country": "IE",
            "status": "booked",
            "starts_at": starts,
            "optout_sms_v2": False,
        }
        base.update(overrides)
        return base

    def test_dst_48h_uses_absolute_arithmetic(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 26, 10))], _dub(2026, 10, 18, 12))
        self.assertEqual([r["send_at"] for r in out], [_utc(2026, 10, 24, 10), _utc(2026, 10, 26, 8)])

    def test_dst_2h_point_in_window_shifts_to_previous_evening(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 25, 8, 30))], _dub(2026, 10, 18, 12))
        self.assertIn(_utc(2026, 10, 24, 19), [r["send_at"] for r in out])

    def test_quiet_shift_midnight_goes_to_previous_evening(self):
        nominal = _dub(2026, 10, 20, 0).astimezone(timezone.utc)
        now = _utc(2026, 10, 18, 11)
        starts = _utc(2026, 10, 30, 11)
        self.assertEqual(resolve_send_time(nominal, now, starts), _utc(2026, 10, 19, 19))

    def test_quiet_boundary_0800_unchanged(self):
        nominal = _dub(2026, 10, 20, 8).astimezone(timezone.utc)
        now = _utc(2026, 10, 18, 11)
        starts = _utc(2026, 10, 30, 11)
        self.assertEqual(resolve_send_time(nominal, now, starts), nominal)

    def test_past_shift_sends_now(self):
        now = _dub(2026, 10, 19, 20, 45).astimezone(timezone.utc)
        out = plan_reminders([self.appt(_dub(2026, 10, 19, 21, 30))], now)
        self.assertEqual([r["send_at"] for r in out], [now])

    def test_appointment_too_soon_gets_no_reminder(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 20, 0, 30))], _dub(2026, 10, 19, 22))
        self.assertEqual(out, [])

    def test_cancelled_variants_yield_nothing(self):
        for status in ["cancelled", "Cancelled", " CANCELED ", "rescheduled", "", None]:
            with self.subTest(status=status):
                out = plan_reminders([self.appt(_dub(2026, 10, 30, 12), status=status)],
                                     _dub(2026, 10, 18, 12))
                self.assertEqual(out, [])

    def test_pl_signature_for_sms_and_email(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 30, 12), country=" pl ")], _dub(2026, 10, 18, 12))
        self.assertTrue(out)
        for r in out:
            self.assertTrue(r["text"].endswith(SIGNATURE_PL))

    def test_long_name_sms_truncated_keeps_date_time_signature(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 26, 10), customer_name="A" * 200,
                                        optout_sms_v2=False)], _dub(2026, 10, 18, 12))
        sms = [r for r in out if r["channel"] == "sms"]
        self.assertTrue(sms)
        for r in sms:
            self.assertLessEqual(len(r["text"]), SMS_MAX_CHARS)
            self.assertIn("26/10/2026", r["text"])
            self.assertIn("10:00", r["text"])
            self.assertTrue(r["text"].endswith(SIGNATURE_DEFAULT))
            self.assertIn("...", r["text"])

    def test_opt_out_routes_to_email_only(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 30, 12), optout_sms_v2=True)],
                             _dub(2026, 10, 18, 12))
        self.assertTrue(out)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_opt_out_without_email_yields_nothing(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 30, 12), optout_sms_v2="true", email="  ")],
                             _dub(2026, 10, 18, 12))
        self.assertEqual(out, [])

    def test_legacy_opt_out_field_ignored(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 30, 12), opt_out=True)],
                             _dub(2026, 10, 18, 12))
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_past_appointment_yields_nothing(self):
        out = plan_reminders([self.appt(_dub(2026, 10, 18, 12))], _dub(2026, 10, 18, 12))
        self.assertEqual(out, [])

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 18, 12))

    def test_naive_starts_skipped_others_kept(self):
        bad = self.appt(datetime(2026, 10, 30, 12), id=2)
        good = self.appt(_dub(2026, 10, 30, 12), id=3)
        out = plan_reminders([bad, good], _dub(2026, 10, 18, 12))
        self.assertTrue(out)
        self.assertTrue(all(r["appointment_id"] == 3 for r in out))

    def test_missing_id_skipped(self):
        bad = self.appt(_dub(2026, 10, 30, 12))
        del bad["id"]
        self.assertEqual(plan_reminders([bad], _dub(2026, 10, 18, 12)), [])

    def test_reversed_input_gives_identical_output(self):
        appts = [self.appt(_dub(2026, 10, 30, 12), id=i) for i in (5, 2, 9)]
        now = _dub(2026, 10, 18, 12)
        self.assertEqual(plan_reminders(appts, now), plan_reminders(list(reversed(appts)), now))

    def test_logs_contain_no_contact_values(self):
        email = "pat.o@example.ie"
        phone = "+353871234567"
        name = "Siobhán Ó Briain"
        appts = [
            self.appt(_dub(2026, 10, 30, 12), email=email, phone=phone, customer_name=name),
            self.appt(_dub(2026, 10, 30, 12), id=2, email=email, phone="", customer_name=name,
                      optout_sms_v2=True),
        ]
        with self.assertLogs("brennan_reminders", level="INFO") as cm:
            plan_reminders(appts, _dub(2026, 10, 18, 12))
        for record in cm.records:
            message = record.getMessage()
            self.assertNotIn(email, message)
            self.assertNotIn(phone, message)
            self.assertNotIn(name, message)


if __name__ == "__main__":
    unittest.main()