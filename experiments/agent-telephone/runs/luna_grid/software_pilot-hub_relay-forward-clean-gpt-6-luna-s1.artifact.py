"""Appointment reminder planner for Brennan Opticians.

Behavior choices: overdue reminders are scheduled for ``now`` if the
appointment is still in the future. A quiet-window adjustment that would
schedule in the past is skipped. Email is used when SMS is opted out or no
phone is available; if the selected channel has no contact detail, the
reminder is skipped. Email addresses are never logged. Scheduling uses
elapsed hours between instants, with all quiet-window checks and message
times in Europe/Dublin.
"""

from datetime import datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
SIGNATURE_IE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
logger = logging.getLogger(__name__)


def _sms_text(name, date_text, time_text, signature):
    fixed = f"Appointment: {date_text} at {time_text}. {signature}"
    if len(fixed) >= 160:
        return fixed
    prefix = f"Hi {name}, " if name else ""
    room = 160 - len(fixed) - len(prefix)
    if room < 0:
        prefix = ""
        room = 160 - len(fixed)
    if name and room >= 1:
        shortened = name if len(name) <= room else name[: max(0, room - 1)] + "…"
        prefix = f"Hi {shortened}, "
        while len(prefix) + len(fixed) > 160:
            shortened = shortened[:-2] + "…" if len(shortened) > 1 else ""
            prefix = f"Hi {shortened}, " if shortened else ""
    return prefix + fixed


def _send_time(target, now):
    local = target.astimezone(DUBLIN)
    if local.time() >= time(21) or local.time() < time(8):
        local = datetime.combine(local.date(), time(20), tzinfo=DUBLIN)
    if local.astimezone(now.tzinfo) < now:
        return None
    return local


def plan_reminders(appointments, now):
    """Return future reminders sorted by their Europe/Dublin ``send_at``."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(ZoneInfo("UTC"))
    results = []

    for appointment in appointments:
        if str(appointment.get("status", "")).lower() == "cancelled":
            continue
        starts_at = appointment["starts_at"]
        if starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise ValueError("starts_at must be timezone-aware")
        start_utc = starts_at.astimezone(ZoneInfo("UTC"))
        if start_utc <= now_utc:
            continue

        opted_out = bool(appointment.get("optout_sms_v2"))
        phone = appointment.get("phone")
        email = appointment.get("email")
        channel = "email" if opted_out or not phone else "sms"
        contact = email if channel == "email" else phone
        if not contact:
            continue

        start_local = start_utc.astimezone(DUBLIN)
        date_text = start_local.strftime("%d/%m/%Y")
        time_text = start_local.strftime("%H:%M")
        signature = SIGNATURE_PL if appointment.get("country") == "PL" else SIGNATURE_IE
        name = str(appointment.get("customer_name") or "")

        for hours_before in (48, 2):
            target_utc = start_utc - timedelta(hours=hours_before)
            if target_utc < now_utc:
                target_utc = now_utc
            send_at = _send_time(target_utc, now_utc)
            if send_at is None:
                continue

            if channel == "sms":
                text = _sms_text(name, date_text, time_text, signature)
            else:
                greeting = f"Hi {name}, " if name else ""
                text = f"{greeting}your appointment is on {date_text} at {time_text}. {signature}"

            results.append({
                "appointment_id": appointment["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            logged_contact = contact if channel == "sms" else "email (address redacted)"
            logger.info(
                "Planned reminder for %s via %s to %s",
                name or appointment["id"],
                channel,
                logged_contact,
            )

    return sorted(results, key=lambda reminder: reminder["send_at"])