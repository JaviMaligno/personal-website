from datetime import datetime, time, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_TWO_HOUR_LEAD = timedelta(hours=2)
_SIGNATURE = "Siobhán Ní Dhuibhir"
_POLISH_SIGNATURE = "Grzegorz Szczepański"
_LOGGER = logging.getLogger(__name__)


def _to_dublin(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now and starts_at must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _channel_and_contact(appointment):
    phone = appointment["phone"].strip()
    email = appointment["email"].strip()
    if phone and not appointment["optout_sms_v2"]:
        return "sms", phone
    if email:
        return "email", email
    return None, None


def _mask_contact(channel, contact):
    if channel == "sms":
        digits = "".join(char for char in contact if char.isdigit())
        return f"***{digits[-2:]}" if digits else "***"
    local, separator, domain = contact.partition("@")
    return f"{local[:1]}***@{domain}" if separator else "***"


def _message(appointment, starts_at, channel):
    signature = (
        _POLISH_SIGNATURE
        if appointment["country"].strip().upper() == "PL"
        else _SIGNATURE
    )
    date_time = f"{starts_at:%Y-%m-%d %H:%M}"
    name = appointment["customer_name"].strip()
    if channel == "email":
        greeting = f"{name}, " if name else ""
        return f"Reminder: {greeting}your appointment is on {date_time}. {signature}"

    fixed = f"Reminder: {date_time}. {signature}"
    if len(fixed) > 160:
        return None
    if not name:
        return fixed
    prefix = f"Reminder: {date_time}. "
    suffix = f" — {signature}"
    room = 160 - len(prefix) - len(suffix)
    return prefix + name[:room] + suffix if room > 0 else fixed


def _quiet_hours_adjust(send_at, now):
    local = send_at.astimezone(_DUBLIN)
    if 8 <= local.hour < 21:
        return local

    candidate = datetime.combine(local.date(), time(20), _DUBLIN)
    if candidate.astimezone(timezone.utc) < now.astimezone(timezone.utc):
        candidate = datetime.combine(local.date() + timedelta(days=1), time(20), _DUBLIN)
        while candidate.astimezone(timezone.utc) < now.astimezone(timezone.utc):
            candidate = datetime.combine(candidate.date() + timedelta(days=1), time(20), _DUBLIN)
    return candidate


def _validate(appointments, now):
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list")
    _to_dublin(now)
    required = (
        "id", "customer_name", "email", "phone", "country", "status",
        "starts_at", "optout_sms_v2",
    )
    for index, appointment in enumerate(appointments):
        if not isinstance(appointment, dict):
            raise TypeError(f"appointment at index {index} must be a dictionary")
        missing = [key for key in required if key not in appointment]
        if missing:
            raise ValueError(f"appointment at index {index} is missing required fields")
        for key in ("customer_name", "email", "phone", "country", "status"):
            if not isinstance(appointment[key], str):
                raise TypeError(f"appointment field {key} must be a string")
        if not isinstance(appointment["optout_sms_v2"], bool):
            raise TypeError("appointment field optout_sms_v2 must be a boolean")
        if not isinstance(appointment["starts_at"], datetime):
            raise TypeError("appointment field starts_at must be a datetime")
        _to_dublin(appointment["starts_at"])
        if isinstance(appointment["id"], (dict, list, set)) or appointment["id"] is None:
            raise TypeError("appointment field id must be a scalar value")


def plan_reminders(appointments, now):
    """Plan reminders; malformed records raise TypeError or ValueError."""
    _validate(appointments, now)
    now_dublin = _to_dublin(now)
    now_utc = now.astimezone(timezone.utc)
    planned = []

    for appointment in appointments:
        if appointment["status"].strip().casefold() == "cancelled":
            continue

        channel, contact = _channel_and_contact(appointment)
        if channel is None:
            continue

        starts_at = _to_dublin(appointment["starts_at"])
        starts_utc = starts_at.astimezone(timezone.utc)
        signature = (
            _POLISH_SIGNATURE
            if appointment["country"].strip().upper() == "PL"
            else _SIGNATURE
        )
        for lead in (timedelta(hours=48), _TWO_HOUR_LEAD):
            send_utc = starts_utc - lead
            if send_utc < now_utc:
                send_utc = now_utc
            send_at = _quiet_hours_adjust(send_utc.astimezone(_DUBLIN), now_dublin)
            text = _message(appointment, starts_at, channel)
            if text is None:
                continue
            planned.append(
                (
                    send_at,
                    str(appointment["id"]),
                    lead.total_seconds(),
                    {
                        "appointment_id": appointment["id"],
                        "channel": channel,
                        "send_at": send_at,
                        "text": text,
                    },
                    contact,
                )
            )

    planned.sort(key=lambda item: (item[0].astimezone(timezone.utc), item[1], item[2]))
    results = []
    for send_at, _, _, reminder, contact in planned:
        _LOGGER.info(
            "Planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
            reminder["appointment_id"],
            reminder["channel"],
            _mask_contact(reminder["channel"], contact),
            send_at.isoformat(),
        )
        results.append(reminder)
    return results