from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging


_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _quiet_hours(send_at: datetime, now: datetime) -> datetime:
    local = send_at.astimezone(_DUBLIN)
    if local.time() < time(8) or local.time() >= time(21):
        local = datetime.combine(
            local.date() - timedelta(days=1), time(20), tzinfo=_DUBLIN
        )
        if local < now.astimezone(_DUBLIN):
            local = now.astimezone(_DUBLIN)
    return local


def _message(name: str, starts_at: datetime, country: str, sms: bool) -> str:
    signature = (
        "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
    )
    date_time = starts_at.strftime("%Y-%m-%d %H:%M")
    prefix = f"Reminder for {date_time}: "
    suffix = f". {signature}"
    name = name or "customer"
    if sms:
        name = name[: max(1, 160 - len(prefix) - len(suffix))]
    return f"{prefix}{name}{suffix}"


def plan_reminders(appointments, now):
    """Return planned, timezone-aware reminders sorted by send time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    reminders = []
    for appointment in appointments:
        if appointment["status"] == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")

        phone = appointment.get("phone")
        if phone and not appointment.get("optout_sms_v2", False):
            channel, contact, sms = "sms", phone, True
        else:
            email = appointment.get("email")
            if not email:
                continue
            channel, contact, sms = "email", "email address on file", False

        for lead in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead
            if send_at < now:
                send_at = now
            send_at = _quiet_hours(send_at, now)
            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": _message(
                    appointment.get("customer_name", ""),
                    starts_at,
                    appointment.get("country", ""),
                    sms,
                ),
            }
            reminders.append(reminder)
            _LOG.info(
                "Planned reminder for %s via %s to %s",
                appointment.get("customer_name", "customer"),
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders