from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import logging

DUBLIN = ZoneInfo("Europe/Dublin")
SIGNATURE = "Chevonne Nee Divver"
POLISH_SIGNATURE = "Grzegorz Szczepański"
logger = logging.getLogger(__name__)


def _dublin(dt):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetimes must be timezone-aware")
    return dt.astimezone(DUBLIN)


def _schedule(send_at, now):
    quiet = send_at.time() >= time(21) or send_at.time() < time(8)
    if quiet:
        send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
        if send_at >= now:
            send_at -= timedelta(days=1)

    if send_at < now:
        send_at = now

    if send_at.time() >= time(21) or send_at.time() < time(8):
        send_at = send_at.replace(hour=8, minute=0, second=0, microsecond=0)
        if send_at < now:
            send_at += timedelta(days=1)

    return send_at


def _text(name, starts_at, signature, channel):
    date_text = starts_at.strftime("%d %B %Y")
    time_text = starts_at.strftime("%H:%M")
    suffix = f"Your appointment is on {date_text} at {time_text}. {signature}"
    prefix = f"Hi {name}, " if name else ""
    message = prefix + suffix
    if channel == "sms" and len(message) > 160:
        available = max(0, 160 - len(suffix) - len("Hi , "))
        short_name = (name or "")[:available].rstrip()
        message = f"Hi {short_name}, {suffix}" if short_name else suffix
    return message


def plan_reminders(appointments, now):
    now = _dublin(now)
    reminders = []

    for appointment in appointments:
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue

        starts_at = _dublin(appointment["starts_at"])
        channel = (
            "sms"
            if appointment.get("phone") and not appointment.get("optout_sms_v2", False)
            else "email"
        )
        signature = (
            POLISH_SIGNATURE if appointment.get("country") == "PL" else SIGNATURE
        )
        name = appointment.get("customer_name", "")
        contact = appointment.get("phone") if channel == "sms" else "[redacted]"

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            target = starts_at - offset
            if target < now:
                if offset == timedelta(hours=48):
                    target = now
                else:
                    continue

            send_at = _schedule(target, now)
            reminder = {
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": _text(name, starts_at, signature, channel),
            }
            reminders.append(reminder)
            logger.info(
                "Reminder recipient=%s channel=%s contact=%s",
                name,
                channel,
                contact,
            )

    reminders.sort(key=lambda reminder: reminder["send_at"].astimezone(DUBLIN))
    return reminders