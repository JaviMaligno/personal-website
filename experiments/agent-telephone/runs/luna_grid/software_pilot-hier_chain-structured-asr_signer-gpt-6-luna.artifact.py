import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _aware_datetime(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _contact_hint(channel, contact):
    if channel == "sms":
        digits = "".join(char for char in str(contact) if char.isdigit())
        return f"phone ending {digits[-2:]}" if digits else "phone ending **"
    return "email"


def _quiet_hours(send_at):
    local = send_at.astimezone(_DUBLIN)
    if local.hour >= 21 or local.hour < 8:
        return local.replace(hour=20, minute=0, second=0, microsecond=0)
    return local


def _message(name, starts_at, signature, sms):
    local_start = starts_at.astimezone(_DUBLIN)
    date = f"{local_start.day} {local_start.strftime('%B %Y')}"
    time = local_start.strftime("%H:%M")
    base = f"Appointment: {date} {time}. {signature}"
    if not sms:
        return f"{name}, {base}" if name else base

    prefix = f"{name}, " if name else ""
    available = 160 - len(base)
    if available <= 0:
        return base[:160]
    return f"{prefix[:available]}{base}"


def plan_reminders(appointments, now):
    """Return deliverable appointment reminders, ordered by send time."""
    if not _aware_datetime(now):
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(_DUBLIN)
    planned = []

    for index, appointment in enumerate(appointments):
        try:
            if not isinstance(appointment, dict):
                raise ValueError("appointment is not a dictionary")
            for field in ("id", "customer_name", "country", "status", "starts_at"):
                if field not in appointment:
                    raise ValueError(f"missing {field}")
            starts_at = appointment["starts_at"]
            if not _aware_datetime(starts_at):
                raise ValueError("starts_at is not timezone-aware")
            if appointment["status"] == "cancelled":
                continue

            phone = appointment.get("phone")
            opted_out = bool(appointment.get("optout_sms_v2", False))
            if phone and not opted_out:
                channel, contact = "sms", phone
            else:
                contact = appointment.get("email")
                if not contact or not str(contact).strip():
                    continue
                channel = "email"

            signature = (
                "Grzegorz Szczepański"
                if appointment["country"] == "PL"
                else "Chevonne Nee Divver"
            )
            local_start = starts_at.astimezone(_DUBLIN)
            for lead_hours in (2, 48):
                send_at = local_start - timedelta(hours=lead_hours)
                if lead_hours == 48 and send_at < now:
                    send_at = now
                send_at = _quiet_hours(send_at)
                if send_at < now:
                    continue

                text = _message(
                    str(appointment["customer_name"]),
                    starts_at,
                    signature,
                    channel == "sms",
                )
                planned.append(
                    (
                        send_at,
                        index,
                        lead_hours,
                        {
                            "appointment_id": appointment["id"],
                            "channel": channel,
                            "send_at": send_at,
                            "text": text,
                        },
                        contact,
                    )
                )
        except (TypeError, ValueError, OverflowError):
            _LOG.warning("Skipping appointment at input index %d due to invalid or missing data", index)

    planned.sort(key=lambda item: (item[0], item[1], item[2]))
    reminders = []
    for _, _, _, reminder, contact in planned:
        _LOG.info(
            "Planned reminder for appointment %s via %s to %s",
            reminder["appointment_id"],
            reminder["channel"],
            _contact_hint(reminder["channel"], contact),
        )
        reminders.append(reminder)
    return reminders