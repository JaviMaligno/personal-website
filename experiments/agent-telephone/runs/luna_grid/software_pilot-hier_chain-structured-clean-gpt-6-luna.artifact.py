from datetime import datetime, time, timedelta
from logging import getLogger
from zoneinfo import ZoneInfo

_LOG = getLogger(__name__)
_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNOFF = "Siobhán Ní Dhuibhir"
_POLISH_SIGNOFF = "Grzegorz Szczepański"


def _local_datetime(value, field):
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _masked_contact(channel, contact):
    contact = str(contact or "")
    if channel == "email":
        if "@" in contact:
            local, domain = contact.split("@", 1)
            return f"{local[:1]}***@{domain}"
        return "***"
    return f"***{contact[-2:]}" if contact else "***"


def _message(name, start, signoff):
    appointment_time = start.strftime("%H:%M")
    date_time = start.strftime("%d/%m/%Y %H:%M")
    base = f"Reminder: {date_time}. {signoff}"
    if len(base) <= 160:
        prefix = f"Hi {name}, " if name else ""
        available = 160 - len(base) - len(prefix)
        if available > 0:
            shortened_name = name[:available]
            return f"Hi {shortened_name}, {base}" if shortened_name else base
        return base

    # If date, time, and sign-off cannot fit, preserve the time and sign-off.
    fallback = f"Reminder: {appointment_time}. {signoff}"
    if len(fallback) <= 160:
        return fallback
    return f"{appointment_time} {signoff}"


def plan_reminders(appointments, now):
    """Return planned appointment reminders, with all times interpreted in Dublin."""
    now_local = _local_datetime(now, "now")
    reminders = []

    for appointment in appointments:
        start = _local_datetime(appointment["starts_at"], "starts_at")
        if str(appointment["status"]).casefold() == "cancelled":
            continue

        phone = appointment.get("phone")
        use_sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if use_sms else "email"
        contact = phone if use_sms else appointment.get("email")
        signoff = (
            _POLISH_SIGNOFF
            if str(appointment.get("country", "")).upper() == "PL"
            else _SIGNOFF
        )
        text = _message(str(appointment.get("customer_name") or ""), start, signoff)

        for offset in (timedelta(hours=2), timedelta(hours=48)):
            send_at = start - offset
            if send_at < now_local:
                send_at = now_local

            if send_at.time() >= time(21) or send_at.time() < time(8):
                send_at = datetime.combine(
                    send_at.date() - timedelta(days=1),
                    time(20),
                    tzinfo=_DUBLIN,
                )
            if send_at < now_local:
                continue

            reminders.append(
                {
                    "appointment_id": appointment["id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            _LOG.info(
                "Reminder for appointment %r goes to %s via %s at %s",
                appointment["id"],
                appointment.get("customer_name") or "customer",
                channel,
                _masked_contact(channel, contact),
            )

    reminders.sort(key=lambda item: (item["send_at"], str(item["appointment_id"])))
    return reminders