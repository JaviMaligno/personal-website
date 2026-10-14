"""Plan appointment reminders using UTC instants and Dublin local quiet hours.

Aware ``starts_at`` and ``now`` values are converted to UTC for arithmetic and
comparisons, avoiding wall-time arithmetic across DST changes. Candidate sends
are then converted to Europe/Dublin. Local times from 21:00 inclusive until
08:00 exclusive are moved to 20:00: sends at or after 21:00 move to 20:00 on
the same date, and sends before 08:00 move to 20:00 on the previous date.
Both instances of a repeated local hour are in quiet hours; no real instant
converts to a nonexistent local time. Converting an aware input through UTC
also gives a definite instant if its supplied timezone representation has a
nonexistent wall time. Finally, sends are clamped to ``now`` after quiet-hour
adjustment so the result is never in the past. If ``now`` is in quiet hours,
that clamp takes precedence.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging


def plan_reminders(appointments, now):
    """Return the 48-hour and 2-hour reminders for non-cancelled appointments."""
    dublin = ZoneInfo("Europe/Dublin")
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for appointment in appointments:
        if appointment.get("cancelled", False):
            continue

        starts_at = appointment["starts_at"]
        starts_utc = starts_at.astimezone(timezone.utc)
        starts_local = starts_utc.astimezone(dublin)
        name = str(appointment.get("customer_name") or appointment.get("name") or "")
        phone = appointment.get("phone")
        sms = bool(phone) and not appointment.get("optout_sms_v2", False)
        channel = "sms" if sms else "email"
        contact = str(phone) if sms else "email address on file"
        signature = (
            "Grzegorz Szczepański"
            if appointment.get("country") == "PL"
            else "Chevonne Nee Divver"
        )
        date_text = starts_local.strftime("%d %B %Y")
        time_text = starts_local.strftime("%H:%M")

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            candidate_utc = starts_utc - offset
            if candidate_utc < now_utc:
                candidate_utc = now_utc

            send_at = candidate_utc.astimezone(dublin)
            if send_at.hour >= 21:
                send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
            elif send_at.hour < 8:
                send_at = (send_at - timedelta(days=1)).replace(
                    hour=20, minute=0, second=0, microsecond=0
                )

            send_utc = send_at.astimezone(timezone.utc)
            if send_utc < now_utc:
                send_at = now_utc.astimezone(dublin)

            text = f"Hi {name}, appointment: {date_text} {time_text}. {signature}"
            if sms and len(text) > 160:
                fixed = f"Hi , appointment: {date_text} {time_text}. {signature}"
                name_limit = max(0, 160 - len(fixed))
                text = f"Hi {name[:name_limit]}, appointment: {date_text} {time_text}. {signature}"

            reminders.append(
                {
                    "appointment_id": appointment["appointment_id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            logging.getLogger(__name__).info(
                "Planned reminder for %s via %s to %s", name, channel, contact
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(timezone.utc))
    return reminders