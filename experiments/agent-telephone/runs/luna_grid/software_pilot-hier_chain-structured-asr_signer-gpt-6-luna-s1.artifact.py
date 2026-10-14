from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNOFF = "Chevonne Nee Divver"
_POLISH_SIGNOFF = "Grzegorz Szczepański"
_LOG = logging.getLogger(__name__)


def _require_aware(value, field):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(_DUBLIN)


def _quiet_hours(send_at, now):
    local = send_at.astimezone(_DUBLIN)
    if local.hour >= 21 or local.hour < 8:
        candidate = local.replace(hour=20, minute=0, second=0, microsecond=0)
        if local.hour < 8:
            candidate -= timedelta(days=1)
        if candidate < now:
            candidate = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if candidate < now:
                candidate += timedelta(days=1)
        return candidate
    return local


def _message(name, starts_at, signoff, sms):
    local_start = starts_at.astimezone(_DUBLIN)
    date_time = f"{local_start:%d %B %Y} at {local_start:%H:%M}"
    prefix = f"Hi {name}, " if name else ""
    fixed = f"Reminder: your appointment is on {date_time}. {signoff}"
    if not sms:
        return prefix + fixed

    available = 160 - len(fixed) - (len(prefix) - len(name or ""))
    if available < 0:
        return None
    name = name or ""
    if len(name) > available:
        name = name[:available]
    return f"Hi {name}, {fixed}" if name else fixed


def plan_reminders(appointments, now):
    now_local = _require_aware(now, "now")
    reminders = []

    for appointment in appointments:
        if str(appointment["status"]).casefold() == "cancelled":
            continue

        starts_at = _require_aware(appointment["starts_at"], "starts_at")
        signoff = (
            _POLISH_SIGNOFF
            if appointment["country"] == "PL"
            else _SIGNOFF
        )
        phone = appointment["phone"]
        use_sms = bool(phone) and appointment["optout_sms_v2"] is not True
        channel = "sms" if use_sms else "email"
        contact = str(phone) if use_sms else "[email redacted]"

        for offset in (48, 2):
            scheduled = starts_at - timedelta(hours=offset)
            if offset == 48 and scheduled < now_local:
                scheduled = now_local
            elif scheduled < now_local:
                continue

            send_at = _quiet_hours(scheduled, now_local)
            text = _message(
                str(appointment["customer_name"] or ""),
                starts_at,
                signoff,
                use_sms,
            )
            if text is None:
                continue

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                    "_offset": offset,
                }
            )
            _LOG.info(
                "Reminder planned for %s via %s to %s",
                appointment["customer_name"],
                channel,
                contact,
            )

    reminders.sort(
        key=lambda reminder: (
            reminder["send_at"],
            str(reminder["appointment_id"]),
            reminder["_offset"],
        )
    )
    return [
        {key: value for key, value in reminder.items() if key != "_offset"}
        for reminder in reminders
    ]