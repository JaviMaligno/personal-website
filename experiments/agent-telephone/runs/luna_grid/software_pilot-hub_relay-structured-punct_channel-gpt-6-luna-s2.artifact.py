import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE = "Siobhán Ní Dhuibhir"
_PL_SIGNATURE = "Grzegorz Szczepański"
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled in Europe/Dublin time."""
    def quiet_hours(send_at):
        local = send_at.astimezone(_DUBLIN)
        if local.time() >= time(21) or local.time() < time(8):
            return (local - timedelta(days=1)).replace(
                hour=20, minute=0, second=0, microsecond=0
            ).astimezone(send_at.tzinfo)
        return send_at

    def message(name, starts_at, signature, sms):
        local_start = starts_at.astimezone(_DUBLIN)
        when = f"{local_start:%Y-%m-%d} at {local_start:%H:%M}"
        prefix = f"Reminder: your appointment is {when}."
        if sms:
            suffix = f" {signature}"
            name_part = f" Hi {name}," if name else ""
            text = f"{prefix}{name_part}{suffix}"
            if len(text) > 160:
                available = max(0, 160 - len(prefix) - len(suffix) - 5)
                short_name = name[:available]
                text = f"{prefix} Hi {short_name},{suffix}" if short_name else f"{prefix}{suffix}"
            return text[:160]
        greeting = f"Hi {name}, " if name else ""
        return f"{greeting}{prefix} {signature}"

    reminders = []
    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        phone = appointment.get("phone")
        opted_out = appointment.get("optout_sms_v2", False)
        if phone and opted_out:
            channel, contact = "sms", phone
        elif not opted_out and appointment.get("email"):
            channel, contact = "email", "address on file"
        else:
            continue

        signature = (
            _PL_SIGNATURE
            if appointment.get("country") == "PL"
            else _SIGNATURE
        )
        for lead_time in (timedelta(hours=48), timedelta(hours=2)):
            send_at = starts_at - lead_time
            if send_at < now:
                send_at = now
            send_at = quiet_hours(send_at)
            if send_at < now:
                send_at = now

            text = message(
                appointment.get("customer_name", ""),
                starts_at,
                signature,
                channel == "sms",
            )
            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Reminder planned for %s via %s to %s",
                appointment.get("customer_name", "customer"),
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders