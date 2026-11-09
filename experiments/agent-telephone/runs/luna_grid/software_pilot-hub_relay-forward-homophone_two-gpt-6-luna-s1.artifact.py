from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE = "Grzegorz Szczepański"
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
_LOG = logging.getLogger(__name__)


def plan_reminders(appointments, now):
    """Return appointment reminders scheduled at or after now."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    planned = []
    for appointment in appointments:
        if appointment["status"].lower() == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("appointment starts_at must be timezone-aware")

        local_start = starts_at.astimezone(_DUBLIN)
        signature = (
            _SIGNATURE if appointment["country"] == "PL"
            else _DEFAULT_SIGNATURE
        )
        name = appointment["customer_name"]
        channel = (
            "sms"
            if appointment.get("phone") and not appointment.get("optout_sms_v2", False)
            else "email"
        )
        contact = appointment.get("phone") if channel == "sms" else "redacted"

        for lead_time in (timedelta(hours=48), timedelta(hours=2)):
            send_at = max(now, starts_at - lead_time)
            local_send = send_at.astimezone(_DUBLIN)

            if local_send.hour >= 21:
                local_send = local_send.replace(hour=20, minute=0, second=0, microsecond=0)
            elif local_send.hour < 8:
                local_send = (local_send - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            send_at = local_send.astimezone(send_at.tzinfo)
            if send_at < now:
                send_at = now

            date_text = local_start.strftime("%d/%m/%Y")
            time_text = local_start.strftime("%H:%M")
            text = f"Hello {name}, your appointment is on {date_text} at {time_text}. {signature}"
            if channel == "sms" and len(text) > 160:
                fixed = f"Hello , your appointment is on {date_text} at {time_text}. {signature}"
                available = max(0, 160 - len(fixed))
                text = f"Hello {name[:available]}, your appointment is on {date_text} at {time_text}. {signature}"

            _LOG.info(
                "Planned reminder for %s via %s to %s",
                name,
                channel,
                contact,
            )
            planned.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })

    return sorted(planned, key=lambda reminder: reminder["send_at"])