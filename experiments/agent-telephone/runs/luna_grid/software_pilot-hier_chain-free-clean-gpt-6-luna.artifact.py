from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


def _parse_appointment(record: Any) -> tuple[Any, datetime, bool, str, str, str, bool, str] | None:
    if not isinstance(record, Mapping):
        _LOG.warning("Skipping appointment: record is not a mapping")
        return None

    required = (
        "id",
        "datetime",
        "cancelled",
        "country",
        "customer_name",
        "phone_number",
        "optout_sms_v2",
        "email_address",
    )
    missing = [key for key in required if key not in record]
    if missing:
        _LOG.warning("Skipping appointment: missing required fields")
        return None

    appointment_id = record["id"]
    appointment_at = record["datetime"]
    if not isinstance(appointment_at, datetime) or appointment_at.tzinfo is None or appointment_at.utcoffset() is None:
        _LOG.warning("Skipping appointment: datetime must be timezone-aware")
        return None

    if not isinstance(record["cancelled"], bool):
        _LOG.warning("Skipping appointment: invalid cancellation status")
        return None

    string_fields = ("country", "customer_name", "phone_number", "email_address")
    if not all(isinstance(record[key], str) for key in string_fields):
        _LOG.warning("Skipping appointment: invalid contact or message field")
        return None
    if appointment_id is None:
        _LOG.warning("Skipping appointment: invalid ID")
        return None
    if not isinstance(record["optout_sms_v2"], bool):
        _LOG.warning("Skipping appointment: invalid SMS opt-out status")
        return None

    return (
        appointment_id,
        appointment_at.astimezone(_DUBLIN),
        record["cancelled"],
        record["country"],
        record["customer_name"],
        record["phone_number"],
        record["optout_sms_v2"],
        record["email_address"],
    )


def _choose_channel(phone: str, sms_opted_out: bool) -> str:
    return "sms" if phone.strip() and not sms_opted_out else "email"


def _format_message(
    customer_name: str,
    appointment_at: datetime,
    country: str,
    channel: str,
) -> str:
    signature = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
    date = appointment_at.strftime("%Y-%m-%d")
    clock = appointment_at.strftime("%H:%M")
    prefix = f"Reminder: {customer_name}, your appointment is "
    suffix = f" on {date} at {clock}. {signature}"
    if channel == "sms":
        available = max(0, 160 - len(prefix) - len(suffix))
        prefix = f"Reminder: {customer_name[:available]}, your appointment is "
        while len(prefix + suffix) > 160 and available:
            available -= 1
            prefix = f"Reminder: {customer_name[:available]}, your appointment is "
    return prefix + suffix


def _calculate_send_time(appointment_at: datetime, lead: timedelta, now: datetime) -> datetime:
    send_at = appointment_at.astimezone(_DUBLIN) - lead
    if send_at.time() >= time(21, 0):
        send_at = send_at.replace(hour=20, minute=0, second=0, microsecond=0)
    elif send_at.time() < time(8, 0):
        send_at = (send_at - timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)

    now_dublin = now.astimezone(_DUBLIN)
    if send_at < now_dublin:
        send_at = now_dublin
    return send_at


def plan_reminders(appointments: Any, now: datetime) -> list[dict[str, Any]]:
    """Plan 48-hour and 2-hour reminders for valid, active appointments."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_dublin = now.astimezone(_DUBLIN)

    planned: list[tuple[datetime, str, int, dict[str, Any]]] = []
    try:
        records = iter(appointments)
    except TypeError:
        _LOG.warning("Skipping appointments: input is not iterable")
        return []

    leads = ((timedelta(hours=2), 2), (timedelta(hours=48), 48))
    for record in records:
        parsed = _parse_appointment(record)
        if parsed is None:
            continue
        appointment_id, appointment_at, cancelled, country, name, phone, optout, email = parsed
        if cancelled:
            continue

        channel = _choose_channel(phone, optout)
        destination = phone.strip() if channel == "sms" else email.strip()
        if not destination:
            _LOG.warning("Skipping reminder: selected channel has no usable destination")
            continue

        for lead, lead_hours in leads:
            send_at = _calculate_send_time(appointment_at, lead, now_dublin)
            message = _format_message(name, appointment_at, country, channel)
            _LOG.info("Planned reminder to %s via %s: %s", name, channel, destination)
            planned.append(
                (
                    send_at,
                    str(appointment_id),
                    lead_hours,
                    {
                        "appointment_id": appointment_id,
                        "channel": channel,
                        "send_at": send_at,
                        "text": message,
                    },
                )
            )

    planned.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in planned]