"""Appointment reminder planning for Brennan Opticians.

Tests in test_reminders.py were not executed in this session.
"""

import logging
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
EVENING_SHIFT_HOUR = 20
SMS_MAX_LEN = 160
SIGNATURE_DEFAULT = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"

logger = logging.getLogger("reminders")

_REQUIRED_FIELDS = ("id", "customer_name", "email", "phone", "status", "starts_at")
_CANCELLED = frozenset({"cancelled", "canceled"})
# (kind, offset, slot order for sorting)
_SLOTS = (("48h", FIRST_OFFSET, 0), ("2h", SECOND_OFFSET, 1))


def _is_aware(dt):
    return dt.tzinfo is not None and dt.utcoffset() is not None


def _text(value):
    return "" if value is None else str(value).strip()


def _is_quiet(local):
    return local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR


def _quiet_shift(local):
    # 20:00 Dublin on the evening before the quiet window that contains `local`.
    day = local.date()
    if local.hour < QUIET_END_HOUR:
        day = day - timedelta(days=1)
    return datetime(day.year, day.month, day.day, EVENING_SHIFT_HOUR, tzinfo=DUBLIN)


def _next_morning(now_local):
    # 08:00 Dublin on the morning that ends the quiet window containing `now_local`.
    day = now_local.date()
    if now_local.hour >= QUIET_END_HOUR:
        day = day + timedelta(days=1)
    return datetime(day.year, day.month, day.day, QUIET_END_HOUR, tzinfo=DUBLIN)


def _slot_time(kind, nominal, starts_utc, now_utc):
    """Return (send_at_utc, None) or (None, reason_code)."""
    n = nominal
    if n < now_utc:
        if kind == "48h":
            n = now_utc
        else:
            return None, "slot_in_past"

    local = n.astimezone(DUBLIN)
    if _is_quiet(local):
        n = _quiet_shift(local).astimezone(UTC)

    if n < now_utc:
        n = now_utc
        now_local = now_utc.astimezone(DUBLIN)
        if _is_quiet(now_local):
            n = _next_morning(now_local).astimezone(UTC)

    if n >= starts_utc:
        return None, "slot_at_or_after_start"
    return n, None


def _signature(country):
    return SIGNATURE_PL if _text(country).upper() == "PL" else SIGNATURE_DEFAULT


def _message(name, date_s, time_s, sig):
    prefix = "Hi " + name if name else "Hi"
    return f"{prefix}, reminder: Brennan Opticians appointment on {date_s} at {time_s}.\n{sig}"


def _sms_text(name, date_s, time_s, sig):
    """Return an SMS within SMS_MAX_LEN, or None if it cannot be made to fit."""
    full = _message(name, date_s, time_s, sig)
    if len(full) <= SMS_MAX_LEN:
        return full

    tokens = name.split()
    if tokens:
        tok = tokens[0]
        short = _message(tok, date_s, time_s, sig)
        if len(short) <= SMS_MAX_LEN:
            return short
        no_name_len = len(_message("", date_s, time_s, sig))
        avail = SMS_MAX_LEN - no_name_len - 1  # one extra char for the space after "Hi"
        if avail >= 4:
            truncated = tok[: avail - 3] + "..."
            candidate = _message(truncated, date_s, time_s, sig)
            if len(candidate) <= SMS_MAX_LEN:
                return candidate

    no_name = _message("", date_s, time_s, sig)
    if len(no_name) <= SMS_MAX_LEN:
        return no_name
    return None


def _log_skip(appt_id, channel, kind, reason):
    logger.info(
        "skip appt=%s channel=%s slot=%s action=drop reason=%s",
        appt_id, channel, kind, reason,
    )


def _validate(appt, index):
    if not isinstance(appt, Mapping):
        raise ValueError(f"appointment at index {index} is not a mapping")
    label = appt["id"] if "id" in appt else f"index {index}"
    for field in _REQUIRED_FIELDS:
        if field not in appt:
            raise ValueError(f"appointment {label}: missing field '{field}'")
    starts_at = appt["starts_at"]
    if not isinstance(starts_at, datetime):
        raise ValueError(f"appointment {label}: field 'starts_at' must be a datetime")
    if not _is_aware(starts_at):
        raise ValueError(f"appointment {label}: field 'starts_at' must be timezone-aware")
    return label, starts_at.astimezone(UTC)


def plan_reminders(appointments, now):
    """Plan reminders for the given appointments.

    Returns a list of dicts with keys appointment_id, channel, send_at, text,
    sorted by send_at (UTC) ascending.
    """
    if not isinstance(now, datetime) or not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)

    items = list(appointments)
    validated = [_validate(appt, i) for i, appt in enumerate(items)]

    planned = []
    for appt, (appt_id, starts_utc) in zip(items, validated):
        status = _text(appt["status"]).casefold()
        if status in _CANCELLED:
            _log_skip(appt_id, "-", "-", "cancelled")
            continue
        if starts_utc <= now_utc:
            _log_skip(appt_id, "-", "-", "already_started")
            continue

        phone = _text(appt["phone"])
        email = _text(appt["email"])
        name = _text(appt["customer_name"])
        # Conservative: a missing or None flag counts as opted out. Only an
        # explicit False means the customer may receive SMS.
        opted_out = appt.get("optout_sms_v2") is not False

        if phone and not opted_out:
            channel = "sms"
        elif email:
            channel = "email"
        else:
            _log_skip(appt_id, "-", "-", "opted_out_no_email" if phone else "no_contact")
            continue

        sig = _signature(appt.get("country"))
        local_start = starts_utc.astimezone(DUBLIN)
        date_s = local_start.strftime("%d/%m/%Y")
        time_s = local_start.strftime("%H:%M")

        for kind, offset, order in _SLOTS:
            send_at, reason = _slot_time(kind, starts_utc - offset, starts_utc, now_utc)
            if send_at is None:
                _log_skip(appt_id, channel, kind, reason)
                continue

            if channel == "sms":
                text = _sms_text(name, date_s, time_s, sig)
                if text is None:
                    _log_skip(appt_id, channel, kind, "sms_too_long")
                    continue
            else:
                text = _message(name, date_s, time_s, sig)

            planned.append((send_at, str(appt_id), order, {
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }))
            logger.info(
                "emit appt=%s channel=%s slot=%s action=send send_at=%s",
                appt_id, channel, kind, send_at.isoformat(),
            )

    planned.sort(key=lambda r: (r[0], r[1], r[2]))
    return [r[3] for r in planned]
</br>