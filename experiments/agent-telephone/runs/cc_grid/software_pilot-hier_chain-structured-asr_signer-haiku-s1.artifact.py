"""Appointment reminder planning for Brennan Opticians.

Standard library only. Single entry point: plan_reminders(appointments, now).

Status notes:
- test_reminders.py was not written and no tests were run, because this agent has no file or shell tools.
- Deviation: the house rule asks for an INFO line naming the contact (channel and contact). R13 and D8 forbid logging the email address, and D8 forbids logging phone numbers and names. The INFO line therefore records appointment id and channel only.
- Items marked CONFIRM are pending client confirmation.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_LEN = 160                      # R10
QUIET_START = time(21, 0)              # R11, Europe/Dublin local
QUIET_END = time(8, 0)                 # R11, Europe/Dublin local
EVENING_SEND = time(20, 0)             # OP-c, moved reminders go to 20:00
MORNING_SEND = time(8, 0)              # OP-c step 3, forward move
SIGNATURE_DEFAULT = "Chevonne Nee Divver"   # R14
SIGNATURE_PL = "Grzegorz Szczepański"       # R14
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})   # OP-b, CONFIRM exact CRM string
REQUIRED_KEYS = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")

logger = logging.getLogger("appointment_reminders")


def _is_naive(dt):
    return dt.tzinfo is None or dt.utcoffset() is None


def _validate_inputs(appointments, now):
    # D1: type and presence checks. Messages carry only the id and field name, never values.
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list")
    if not isinstance(now, datetime) or _is_naive(now):
        raise ValueError("now must be a timezone-aware datetime")
    for index, appt in enumerate(appointments):
        if not isinstance(appt, dict):
            raise TypeError(f"appointment #{index} must be a dict")
        label = appt["id"] if "id" in appt else f"#{index}"
        for key in REQUIRED_KEYS:
            if key not in appt:
                raise ValueError(f"appointment {label}: missing field '{key}'")
        starts_at = appt["starts_at"]
        if not isinstance(starts_at, datetime) or _is_naive(starts_at):
            raise ValueError(
                f"appointment {label}: field 'starts_at' must be a timezone-aware datetime"
            )


def _is_cancelled(status):
    # OP-b: None, empty and any other value are not cancelled.
    return isinstance(status, str) and status.strip().casefold() in CANCELLED_STATUSES


def _choose_channel(appt_id, appt):
    # OP-d and R9. Non-bool opt-out is treated as opted out (conservative default, CONFIRM).
    opt = appt.get("optout_sms_v2")
    if not isinstance(opt, bool):
        logger.warning("appointment_id=%s reason=optout_missing", appt_id)
        opt = True
    phone = appt.get("phone")
    email = appt.get("email")
    has_phone = isinstance(phone, str) and bool(phone.strip())
    has_email = isinstance(email, str) and bool(email.strip())
    if has_phone and not opt:
        return "sms"
    if has_email:
        return "email"
    # CONFIRM: whether staff should be alerted for these appointments.
    logger.warning("appointment_id=%s reason=no_channel", appt_id)
    return None


def _candidate_times(starts_at, now):
    # R6 and R7 with OP-a: a point already passed collapses to now.
    # If both collapse to now, both are returned (literal R7). CONFIRM: R18 may
    # suggest only the 2-hour reminder should be sent in that case.
    points = (starts_at - timedelta(hours=48), starts_at - timedelta(hours=2))
    return [now if point <= now else point for point in points]


def _in_quiet(t):
    local = t.astimezone(DUBLIN).time()
    return local >= QUIET_START or local < QUIET_END


def _dublin_wall(day, clock):
    return datetime.combine(day, clock, tzinfo=DUBLIN).astimezone(UTC)


def _apply_quiet_hours(t, starts_at, now):
    # OP-c. Returns (send_at, skip_reason). skip_reason is None when send_at is usable.
    # CONFIRM: step 3 forward move to 08:00 when now is inside the quiet window.
    if not _in_quiet(t):
        send_at = t
    else:
        local_t = t.astimezone(DUBLIN)
        evening = local_t.date()
        if local_t.time() < QUIET_START:
            evening -= timedelta(days=1)
        m = _dublin_wall(evening, EVENING_SEND)
        if m >= now:
            send_at = m
        elif not _in_quiet(now):
            send_at = now
        else:
            local_now = now.astimezone(DUBLIN)
            day = local_now.date()
            if local_now.time() >= QUIET_START:
                day += timedelta(days=1)
            send_at = _dublin_wall(day, MORNING_SEND)
    if send_at >= starts_at:
        return None, "after_start"
    if _in_quiet(send_at) or send_at < now:
        return None, "quiet_guard"
    return send_at, None


def _signature(country):
    # R14 and D5.
    code = country.strip().upper() if isinstance(country, str) else ""
    return SIGNATURE_PL if code == "PL" else SIGNATURE_DEFAULT


def _sms_text(greeting, date_s, time_s, sig):
    prefix = f"Hi {greeting}," if greeting else "Hi,"
    return (
        f"{prefix} reminder: your Brennan Opticians appointment is on "
        f"{date_s} at {time_s}. {sig}"
    )


def _build_sms(name, date_s, time_s, sig):
    # D4 and R10. Fallback chain: full name, first token, no name.
    # CONFIRM: whether the 160 limit means GSM-7 characters. len() does not model UCS-2.
    candidates = []
    if name:
        candidates.append(name)
        first = name.split()[0]
        if first != name:
            candidates.append(first)
    candidates.append("")
    for greeting in candidates:
        text = _sms_text(greeting, date_s, time_s, sig)
        if len(text) <= SMS_MAX_LEN:
            return text
    return None


def _build_email(name, date_s, time_s, sig):
    # D3. Body is English with the Polish signer name for PL (CONFIRM).
    greeting = f"Dear {name}," if name else "Hello,"
    return (
        f"{greeting}\n\n"
        f"This is a reminder that your Brennan Opticians appointment is on "
        f"{date_s} at {time_s}.\n\n"
        f"Kind regards,\n"
        f"{sig}"
    )


def _log_skip(appt_id, reason, level=logging.INFO):
    logger.log(level, "appointment_id=%s reason=%s", appt_id, reason)


def plan_reminders(appointments, now):
    _validate_inputs(appointments, now)
    now = now.astimezone(UTC)
    planned = []

    for appt in appointments:
        appt_id = appt["id"]

        if _is_cancelled(appt["status"]):
            _log_skip(appt_id, "cancelled")
            continue

        starts_at = appt["starts_at"].astimezone(UTC)
        if starts_at <= now:
            _log_skip(appt_id, "already_started")
            continue

        channel = _choose_channel(appt_id, appt)
        if channel is None:
            continue

        # R5 and R15: text shows the Dublin local start time of the appointment.
        local_start = starts_at.astimezone(DUBLIN)
        date_s = local_start.strftime("%d %b %Y")
        time_s = local_start.strftime("%H:%M")

        raw_name = appt["customer_name"]
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        sig = _signature(appt["country"])

        for t in _candidate_times(starts_at, now):
            send_at, skip = _apply_quiet_hours(t, starts_at, now)
            if skip is not None:
                _log_skip(appt_id, skip)
                continue

            if channel == "sms":
                text = _build_sms(name, date_s, time_s, sig)
                if text is None:
                    _log_skip(appt_id, "sms_too_long")
                    continue
            else:
                text = _build_email(name, date_s, time_s, sig)

            planned.append({
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            logger.info("planned reminder appointment_id=%s channel=%s", appt_id, channel)

    # R16 and D7: deterministic order.
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned