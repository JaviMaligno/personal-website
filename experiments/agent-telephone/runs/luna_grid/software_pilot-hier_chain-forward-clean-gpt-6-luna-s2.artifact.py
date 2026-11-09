from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _dublin(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("All datetimes must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _delivery_time(send_at, now):
    local = _dublin(send_at)
    if local.hour >= 21:
        local = local.replace(hour=20, minute=0, second=0, microsecond=0)
    elif local.hour < 8:
        local = (local - timedelta(days=1)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
    return max(local, now)


def _text(appointment, signature, limit=None):
    when = _dublin(appointment["starts_at"])
    details = f"{when:%d/%m/%Y} at {when:%H:%M}"
    prefix = f"Hi {{name}}, your appointment is on {details}. "
    suffix = f"Regards, {signature}"
    name = str(appointment["customer_name"])
    message = prefix.format(name=name) + suffix
    if limit is None or len(message) <= limit:
        return message

    available = limit - len(prefix.format(name="")) - len(suffix)
    name = name[:max(0, available)].rstrip()
    return prefix.format(name=name) + suffix


def plan_reminders(appointments, now):
    now = _dublin(now)
    reminders = []

    for appointment_order, appointment in enumerate(appointments):
        starts_at = _dublin(appointment["starts_at"])
        if str(appointment["status"]).lower() == "cancelled":
            continue

        use_sms = bool(appointment.get("phone")) and not appointment.get(
            "optout_sms_v2", False
        )
        channel = "sms" if use_sms else "email"
        contact = "phone (redacted)" if use_sms else "email (redacted)"
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Siobhán Ní Dhuibhir"
        )

        for reminder_order, offset in enumerate((timedelta(hours=48), timedelta(hours=2))):
            target = starts_at - offset
            if reminder_order == 0 and target < now:
                target = now
            elif target < now:
                continue

            send_at = _delivery_time(target, now)
            reminders.append(
                (
                    send_at,
                    appointment_order,
                    reminder_order,
                    {
                        "appointment_id": appointment["id"],
                        "channel": channel,
                        "send_at": send_at,
                        "text": _text(appointment, signature, 160 if use_sms else None),
                    },
                    str(appointment.get("customer_name", "")),
                    contact,
                )
            )

    reminders.sort(key=lambda item: (item[0], item[1], item[2]))
    planned = []
    for _, _, _, reminder, recipient, contact in reminders:
        _LOG.info(
            "Planned appointment reminder for %s via %s (%s)",
            recipient,
            reminder["channel"],
            contact,
        )
        planned.append(reminder)
    return planned