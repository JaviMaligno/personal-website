from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE = "Chevonne Nee Divver"
_POLISH_SIGNATURE = "Grzegorz Szczepański"
_SMS_LIMIT = 160


def _required_text(appointment, field):
    value = appointment.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"appointment field {field!r} must be a non-empty string")
    return value.strip()


def _local_instant(value, field):
    if not isinstance(value, datetime):
        raise ValueError(f"appointment field {field!r} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"appointment field {field!r} must be timezone-aware")
    return value.astimezone(timezone.utc).astimezone(_DUBLIN)


def _make_text(name, starts_at, signature, sms):
    date = starts_at.strftime("%Y-%m-%d")
    clock = starts_at.strftime("%H:%M")
    fixed = f"Your appointment is on {date} at {clock}. {signature}"
    if not sms:
        return f"Hi {name}, {fixed}"
    prefix = f"Hi {name}, "
    text = prefix + fixed
    if len(text) <= _SMS_LIMIT:
        return text
    available = _SMS_LIMIT - len("Hi , ") - len(fixed)
    if available > 0:
        return f"Hi {name[:available]}, {fixed}"
    # This compact fallback preserves the date, time, and complete signature.
    return fixed


def plan_reminders(appointments, now) -> list[dict]:
    """Plan Dublin-time reminders.

    Naive datetimes and invalid required fields raise ValueError. Cancelled
    records are skipped before other fields are validated. Each record needs
    appointment_id, starts_at, name, country, and a usable email unless SMS
    is available. SMS is selected only for a non-empty phone when
    optout_sms_v2 is not true; legacy opt-out fields are ignored.
    """
    current = _local_instant(now, "now")
    planned = []

    for appointment in appointments:
        if not isinstance(appointment, dict):
            raise ValueError("each appointment must be a dictionary")
        if appointment.get("cancelled") is True:
            continue

        appointment_id = appointment.get("appointment_id")
        if appointment_id is None:
            raise ValueError("appointment field 'appointment_id' is required")
        starts_at = _local_instant(appointment.get("starts_at"), "starts_at")
        name = _required_text(appointment, "name")
        country = _required_text(appointment, "country")
        signature = _POLISH_SIGNATURE if country == "PL" else _SIGNATURE

        phone = appointment.get("phone")
        use_sms = (
            isinstance(phone, str)
            and bool(phone.strip())
            and appointment.get("optout_sms_v2") is not True
        )
        if use_sms:
            channel = "sms"
            contact = phone.strip()
        else:
            channel = "email"
            contact = _required_text(appointment, "email")

        for offset in (48, 2):
            send_at = (starts_at.astimezone(timezone.utc) - timedelta(hours=offset))
            send_at = send_at.astimezone(_DUBLIN)
            if send_at < current:
                send_at = current

            if send_at.timetz().replace(tzinfo=None) >= time(21) or send_at.timetz().replace(tzinfo=None) < time(8):
                send_at = datetime.combine(
                    send_at.date() - timedelta(days=1), time(20), tzinfo=_DUBLIN
                )
                if send_at < current:
                    send_at = current

            text = _make_text(name, starts_at, signature, channel == "sms")
            planned.append(
                (
                    send_at,
                    str(appointment_id),
                    offset,
                    {
                        "appointment_id": appointment_id,
                        "channel": channel,
                        "send_at": send_at,
                        "text": text,
                    },
                    contact,
                )
            )

    planned.sort(key=lambda item: (item[0], item[1], item[2]))
    results = []
    for _, _, _, reminder, contact in planned:
        logged_contact = contact if reminder["channel"] == "sms" else "[email]"
        _LOG.info(
            "Planned reminder for appointment %s via %s to %s",
            reminder["appointment_id"],
            reminder["channel"],
            logged_contact,
        )
        results.append(reminder)
    return results