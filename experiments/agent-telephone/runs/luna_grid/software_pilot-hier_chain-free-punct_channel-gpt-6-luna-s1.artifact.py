from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import logging

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)

# The client has not confirmed whether True or False means SMS is allowed.
# Keep this unset until they do; channel selection cannot safely be inferred.
_SMS_ALLOWED_WHEN: bool | None = None


def plan_reminders(appointments: Any, now: datetime) -> list[dict[str, Any]]:
    """Plan reminders, raising ValueError for missing or malformed required data."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    if _SMS_ALLOWED_WHEN is None:
        raise RuntimeError(
            "Cannot plan reminders until the meaning of optout_sms_v2 is confirmed"
        )

    planned: list[dict[str, Any]] = []
    now_local = now.astimezone(_DUBLIN)

    for index, appointment in enumerate(appointments):
        if not isinstance(appointment, dict):
            raise ValueError(f"appointment at index {index} must be a dictionary")
        if appointment.get("cancelled") or appointment.get("status") == "cancelled":
            continue

        for field in ("appointment_id", "starts_at", "optout_sms_v2", "name", "country"):
            if field not in appointment:
                raise ValueError(f"appointment at index {index} is missing {field!r}")

        starts_at = appointment["starts_at"]
        if (
            not isinstance(starts_at, datetime)
            or starts_at.tzinfo is None
            or starts_at.utcoffset() is None
        ):
            raise ValueError(
                f"appointment at index {index}: starts_at must be a timezone-aware datetime"
            )
        if not isinstance(appointment["optout_sms_v2"], bool):
            raise ValueError(
                f"appointment at index {index}: optout_sms_v2 must be a boolean"
            )

        channel = "sms" if appointment["optout_sms_v2"] is _SMS_ALLOWED_WHEN else "email"
        contact_field = "phone" if channel == "sms" else "email"
        contact = appointment.get(contact_field)
        if not isinstance(contact, str) or not contact.strip():
            raise ValueError(
                f"appointment at index {index} requires a non-empty {contact_field}"
            )

        start_local = starts_at.astimezone(_DUBLIN)
        date_time = start_local.strftime("%Y-%m-%d %H:%M")
        signoff = (
            "Grzegorz Szczepański"
            if appointment["country"] == "PL"
            else "Siobhán Ní Dhuibhir"
        )
        name = appointment["name"]
        if not isinstance(name, str):
            raise ValueError(f"appointment at index {index}: name must be a string")

        text = f"{name}, appointment on {date_time}. {signoff}"
        if channel == "sms":
            fixed = f", appointment on {date_time}. {signoff}"
            if len(fixed) > 160:
                raise ValueError(
                    f"appointment at index {index}: required SMS date and sign-off exceed 160 characters"
                )
            text = f"{name[:160 - len(fixed)]}{fixed}"

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            send_at = (start_local - offset).astimezone(_DUBLIN)
            if send_at < now_local:
                send_at = now_local
            if time(21, 0) <= send_at.timetz().replace(tzinfo=None) or send_at.hour < 8:
                send_at = datetime.combine(
                    send_at.date() - timedelta(days=1), time(20, 0), tzinfo=_DUBLIN
                )
                if send_at < now_local:
                    send_at = now_local

            planned.append(
                {
                    "appointment_id": appointment["appointment_id"],
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )
            logged_contact = (
                "email address withheld" if channel == "email" else contact
            )
            _LOG.info(
                "Reminder for appointment %s via %s to %s",
                appointment["appointment_id"],
                channel,
                logged_contact,
            )

    return sorted(planned, key=lambda reminder: reminder["send_at"])