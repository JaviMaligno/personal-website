from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)
_SIGNATURE = "Grzegorz Szczepański"
_DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"


def plan_reminders(appointments, now):
    """Return sorted appointment reminders scheduled in Europe/Dublin time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    now = now.astimezone(_DUBLIN)
    reminders = []

    for appointment in appointments:
        if appointment.get("status") == "cancelled":
            continue

        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        starts_at = starts_at.astimezone(_DUBLIN)

        channel = (
            "sms"
            if appointment.get("phone") and not appointment.get("optout_sms_v2")
            else "email"
        )
        signature = (
            _SIGNATURE if appointment.get("country") == "PL" else _DEFAULT_SIGNATURE
        )
        date_time = starts_at.strftime("%Y-%m-%d %H:%M")
        name = str(appointment.get("customer_name") or "")
        base = f"Your appointment is on {date_time}. {signature}"
        text = f"Hello {name}, your appointment is on {date_time}. {signature}"

        if channel == "sms" and len(text) > 160:
            available = max(0, 160 - len(f"Hello , {base}"))
            text = f"Hello {name[:available]}, {base}"
            if len(text) > 160:
                text = base

        for index, lead in enumerate((timedelta(hours=48), timedelta(hours=2))):
            original = starts_at - lead
            if original < now:
                if index == 0:
                    original = now
                else:
                    continue

            send_at = original
            if send_at.hour >= 21 or send_at.hour < 8:
                preceding_20 = send_at.replace(
                    hour=20, minute=0, second=0, microsecond=0
                )
                if preceding_20 < send_at and preceding_20 > now:
                    send_at = preceding_20
                else:
                    next_day = send_at.date() + timedelta(days=1)
                    send_at = datetime(
                        next_day.year, next_day.month, next_day.day, 8, 0,
                        tzinfo=_DUBLIN,
                    )

            if send_at < now or send_at >= starts_at:
                continue

            reminders.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            _LOG.info(
                "Planned reminder for %s via %s (%s)",
                name,
                channel,
                "phone" if channel == "sms" else "email",
            )

    reminders.sort(key=lambda reminder: reminder["send_at"])
    return reminders