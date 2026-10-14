"""Brennan Opticians appointment reminder planning.

Pure planning: returns reminder dicts and sends nothing. Standard library only.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("brennan.reminders")

DUBLIN_TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

# R6: index 0 is the 48-hour reminder, index 1 is the 2-hour reminder.
REMINDER_OFFSETS = (timedelta(hours=48), timedelta(hours=2))

# R20: client rule. Note: non-GSM characters (a-acute, i-acute, n-acute, s-acute, l-stroke)
# make real carriers use UCS-2 with 70-character segments. The client's stated 160 limit
# is implemented as written and must not be changed silently.
SMS_MAX_LENGTH = 160

QUIET_START_HOUR = 21       # R11: 21:00 inclusive is blocked
QUIET_END_HOUR = 8          # R11: 08:00 is allowed
QUIET_MOVE_BACK_HOUR = 20   # R11: quiet sends move back to 20:00 Dublin local

SKIPPED_STATUSES = frozenset({"cancelled"})  # R12, R18

SIGNATURE_IE = "Siobhán Ní Dhuibhir"        # R14
SIGNATURE_PL = "Grzegorz Szczepański"       # R14

OPTOUT_TRUE_VALUES = frozenset({"true", "1", "yes", "y"})     # R21
OPTOUT_FALSE_VALUES = frozenset({"", "false", "0", "no", "n"})  # R21

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")  # R5: literal table, not locale


def plan_reminders(appointments: list[dict], now: datetime) -> list[dict]:
    """Return reminders for the given appointments, sorted by send_at, appointment_id, channel."""
    _validate_datetime(now, "now")
    now_utc = now.astimezone(UTC)
    reminders: list[dict] = []
    for appt in appointments:
        reminders.extend(_plan_one(appt, now_utc))
    reminders.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return reminders


def _validate_datetime(value, label: str) -> None:
    # Error text carries only the field label, never customer data.
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _clean_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optout_state(value) -> tuple[bool, bool]:
    """Return (opted_out, is_unclear). Unclear values fail safe to opted out."""
    if value is None:
        return False, False
    if isinstance(value, bool):
        return value, False
    if isinstance(value, str):
        token = value.strip().lower()
        if token in OPTOUT_TRUE_VALUES:
            return True, False
        if token in OPTOUT_FALSE_VALUES:
            return False, False
    return True, True


def _choose_channel(appt: dict, appt_id) -> tuple[str | None, str | None]:
    phone = _clean_str(appt.get("phone"))
    email = _clean_str(appt.get("email"))
    opted_out, unclear = _optout_state(appt.get("optout_sms_v2"))
    if unclear:
        logger.warning("optout value unclear id=%s reason=unclear_optout", appt_id)
    if phone and not opted_out:
        return "sms", None
    if email:
        return "email", None
    return None, "no_channel"


def _signature_for(country) -> str:
    code = _clean_str(country).upper()
    return SIGNATURE_PL if code == "PL" else SIGNATURE_IE


def _is_quiet(local_dt: datetime) -> bool:
    return local_dt.hour >= QUIET_START_HOUR or local_dt.hour < QUIET_END_HOUR


def _quiet_move_back(local_dt: datetime) -> datetime:
    """20:00 Dublin on the evening before the window start, as UTC."""
    day = local_dt.date()
    if local_dt.hour < QUIET_END_HOUR:
        day = day - timedelta(days=1)
    return datetime(day.year, day.month, day.day, QUIET_MOVE_BACK_HOUR,
                    tzinfo=DUBLIN_TZ).astimezone(UTC)


def _next_morning_utc(now_local: datetime) -> datetime:
    """First allowed instant (08:00 Dublin) after a quiet-window now, as UTC."""
    day = now_local.date()
    if now_local.hour >= QUIET_END_HOUR:
        day = day + timedelta(days=1)
    return datetime(day.year, day.month, day.day, QUIET_END_HOUR,
                    tzinfo=DUBLIN_TZ).astimezone(UTC)


def _resolve_send_time(raw_utc: datetime, now_utc: datetime,
                       starts_utc: datetime, appt_id) -> datetime | None:
    send_at = max(raw_utc, now_utc)  # R7, R8
    local = send_at.astimezone(DUBLIN_TZ)
    if _is_quiet(local):
        moved = _quiet_move_back(local)
        if moved >= now_utc:
            send_at = moved
        else:
            # R19 conflict: the moved time is before now.
            logger.warning("quiet window conflict id=%s reason=quiet_window_conflict", appt_id)
            now_local = now_utc.astimezone(DUBLIN_TZ)
            if not _is_quiet(now_local):
                send_at = now_utc
            else:
                send_at = _next_morning_utc(now_local)
    if send_at >= starts_utc:
        logger.info("dropped id=%s reason=after_start", appt_id)
        return None
    return send_at


def _format_date_time(starts_utc: datetime) -> tuple[str, str]:
    local = starts_utc.astimezone(DUBLIN_TZ)
    date_str = f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"
    hhmm = f"{local.hour:02d}:{local.minute:02d}"
    return date_str, hhmm


def _build_sms(name: str, date_str: str, hhmm: str, signature: str) -> str | None:
    """R10 ladder: full name, first name, first initial, no name. None if nothing fits."""
    parts = name.split()
    if parts:
        candidates = [" ".join(parts), parts[0], f"{parts[0][0]}.", ""]
    else:
        candidates = [""]
    for cand in candidates:
        prefix = f"{cand}, " if cand else ""
        text = f"{prefix}Brennan Opticians appointment on {date_str} at {hhmm}. {signature}"
        if len(text) <= SMS_MAX_LENGTH:
            return text
    return None


def _build_email(name: str, date_str: str, hhmm: str, signature: str) -> str:
    greeting = name if name else "customer"
    return (f"Dear {greeting},\n\n"
            f"This is a reminder of your appointment at Brennan Opticians "
            f"on {date_str} at {hhmm}.\n\n{signature}")


def _plan_one(appt: dict, now_utc: datetime) -> list[dict]:
    if not isinstance(appt, dict):
        raise ValueError("each appointment must be a dict")

    appt_id = appt.get("id")
    status = appt.get("status")
    status_norm = status.strip().lower() if isinstance(status, str) else None

    starts_raw = appt.get("starts_at")
    if starts_raw is not None:
        _validate_datetime(starts_raw, "starts_at")  # R2

    if status_norm in SKIPPED_STATUSES:
        logger.info("skipped id=%s reason=cancelled status=%r", appt_id, status)
        return []

    if starts_raw is None:
        logger.warning("skipped id=%s reason=missing_starts_at status=%r", appt_id, status)
        return []

    starts_utc = starts_raw.astimezone(UTC)
    if starts_utc <= now_utc:
        logger.info("skipped id=%s reason=already_started status=%r", appt_id, status)
        return []

    # R18: every status other than cancelled is treated as active, with a warning.
    logger.warning("status not recognised id=%s reason=unknown_status status=%r",
                   appt_id, status)

    channel, reason = _choose_channel(appt, appt_id)
    if channel is None:
        logger.warning("skipped id=%s reason=%s status=%r", appt_id, reason, status)
        return []

    signature = _signature_for(appt.get("country"))
    date_str, hhmm = _format_date_time(starts_utc)
    name = " ".join(_clean_str(appt.get("customer_name")).split())
    email = _clean_str(appt.get("email"))

    send_times = [
        _resolve_send_time(starts_utc - offset, now_utc, starts_utc, appt_id)
        for offset in REMINDER_OFFSETS
    ]

    # R19 collapse: if the 48h reminder is not before the 2h one, keep only the 2h one.
    if (send_times[0] is not None and send_times[1] is not None
            and send_times[0] >= send_times[1]):
        logger.info("collapsed 48h reminder id=%s reason=collapsed_48h status=%r",
                    appt_id, status)
        send_times[0] = None

    reminders: list[dict] = []
    for send_at in send_times:
        if send_at is None:
            continue
        reminder_channel = channel
        if channel == "sms":
            text = _build_sms(name, date_str, hhmm, signature)
            if text is None:
                # R20: email fallback, one channel only, or drop.
                if email:
                    reminder_channel = "email"
                    text = _build_email(name, date_str, hhmm, signature)
                else:
                    logger.warning("skipped id=%s reason=sms_too_long status=%r",
                                   appt_id, status)
                    continue
        else:
            text = _build_email(name, date_str, hhmm, signature)
        reminders.append({
            "appointment_id": appt_id,
            "channel": reminder_channel,
            "send_at": send_at,
            "text": text,
        })
        # Contact details are deliberately not logged (R13). The appointment id and
        # channel are enough for support to trace each delivery.
        logger.info("planned id=%s channel=%s reason=planned status=%r",
                    appt_id, reminder_channel, status)
    return reminders