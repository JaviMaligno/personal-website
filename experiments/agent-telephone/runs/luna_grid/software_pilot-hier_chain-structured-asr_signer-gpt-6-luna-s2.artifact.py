from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

_DUBLIN = ZoneInfo("Europe/Dublin")
_LOG = logging.getLogger(__name__)


class InvalidAppointmentError(ValueError):
    """An appointment is missing a required field or has an invalid value."""


class ProductClarificationRequired(RuntimeError):
    """A reminder policy needs product clarification before it can be applied."""


@dataclass
class _Candidate:
    appointment_id: Any
    offset: timedelta
    channel: str
    contact: str
    send_at: datetime
    text: str


def _two_hour_policy(send_at: datetime, now: datetime) -> datetime | None:
    """Product decision point: send overdue two-hour reminders now or omit them."""
    if send_at < now:
        raise ProductClarificationRequired(
            "Clarify whether a passed two-hour reminder should be sent immediately or omitted."
        )
    return send_at


def _required(appointment: dict[str, Any], field: str) -> Any:
    value = appointment.get(field)
    if value is None or value == "":
        raise InvalidAppointmentError(f"Missing required field: {field}")
    return value


def _as_dublin(value: Any, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise InvalidAppointmentError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidAppointmentError(f"{field} must be timezone-aware")
    return value.astimezone(_DUBLIN)


def _channel(appointment: dict[str, Any]) -> tuple[str, str]:
    opted_out = appointment.get("optout_sms_v2", False)
    if not isinstance(opted_out, bool):
        raise InvalidAppointmentError("optout_sms_v2 must be a boolean")

    if opted_out:
        email = _required(appointment, "email")
        if not isinstance(email, str):
            raise InvalidAppointmentError("email must be a string")
        return "email", "email"

    phone = appointment.get("phone")
    if phone:
        if not isinstance(phone, str):
            raise InvalidAppointmentError("phone must be a string")
        return "sms", phone

    raise ProductClarificationRequired(
        "Clarify channel selection when SMS is allowed but phone is missing."
    )


def _message(name: str, starts_at: datetime, country: Any, channel: str) -> str:
    signature = "Grzegorz Szczepański" if country == "PL" else "Chevonne Nee Divver"
    appointment_time = starts_at.strftime("%Y-%m-%d %H:%M")
    if channel == "email":
        return f"Reminder for your appointment on {appointment_time}. {signature}"

    prefix = f"Reminder: appointment {appointment_time}"
    suffix = f". {signature}"
    available = 160 - len(prefix) - len(suffix)
    customer = f" for {name}" if name else ""
    if len(customer) > available:
        customer = ""
    return f"{prefix}{customer}{suffix}"


def _quiet_hours(send_at: datetime) -> datetime:
    clock = send_at.timetz().replace(tzinfo=None)
    if clock >= time(21, 0):
        return send_at.replace(hour=20, minute=0, second=0, microsecond=0)
    if clock < time(8, 0):
        previous_day = send_at - timedelta(days=1)
        return previous_day.replace(hour=20, minute=0, second=0, microsecond=0)
    return send_at


def plan_reminders(
    appointments: list[dict[str, Any]], now: datetime
) -> list[dict[str, Any]]:
    """Plan appointment reminders, returning dictionaries with the four specified fields."""
    if not isinstance(appointments, list):
        raise InvalidAppointmentError("appointments must be a list")
    current = _as_dublin(now, "now")
    seen_ids: set[Any] = set()
    candidates: list[_Candidate] = []

    for appointment in appointments:
        if not isinstance(appointment, dict):
            raise InvalidAppointmentError("Each appointment must be a dictionary")

        appointment_id = _required(appointment, "id")
        try:
            if appointment_id in seen_ids:
                raise InvalidAppointmentError("Duplicate appointment id")
            seen_ids.add(appointment_id)
        except TypeError as exc:
            raise InvalidAppointmentError("Appointment id must be hashable") from exc

        status = _required(appointment, "status")
        if status == "cancelled":
            continue

        name = _required(appointment, "customer_name")
        if not isinstance(name, str):
            raise InvalidAppointmentError("customer_name must be a string")
        starts_at = _as_dublin(_required(appointment, "starts_at"), "starts_at")
        country = _required(appointment, "country")
        channel, contact = _channel(appointment)

        for offset in (timedelta(hours=48), timedelta(hours=2)):
            proposed = starts_at - offset
            if offset == timedelta(hours=48) and proposed < current:
                proposed = current
            elif offset == timedelta(hours=2):
                proposed = _two_hour_policy(proposed, current)

            send_at = _quiet_hours(proposed)
            if send_at < current:
                continue

            text = _message(name, starts_at, country, channel)
            candidates.append(
                _Candidate(appointment_id, offset, channel, contact, send_at, text)
            )

    candidates.sort(key=lambda candidate: candidate.send_at)
    result = []
    for candidate in candidates:
        if candidate.channel == "sms":
            contact = f"phone ending {candidate.contact[-2:]}"
        else:
            contact = "email"
        _LOG.info(
            "Planned reminder for appointment %s via %s to %s",
            candidate.appointment_id,
            candidate.channel,
            contact,
        )
        result.append(
            {
                "appointment_id": candidate.appointment_id,
                "channel": candidate.channel,
                "send_at": candidate.send_at,
                "text": candidate.text,
            }
        )
    return result