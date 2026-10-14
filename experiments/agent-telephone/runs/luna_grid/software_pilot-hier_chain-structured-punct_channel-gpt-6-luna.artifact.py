from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
_SIGNATURE_PL = "Grzegorz Szczepański"

# Product-owner confirmation is required before setting this to True or False.
# True means optout_sms_v2 == True permits SMS; False means it opts the customer out.
_SMS_TRUE_MEANS_ELIGIBLE = None


def _sms_eligible(value):
    if _SMS_TRUE_MEANS_ELIGIBLE is None:
        raise ValueError("sms_policy_unconfirmed")
    return bool(value) is _SMS_TRUE_MEANS_ELIGIBLE


def _masked_contact(channel, contact):
    if channel == "sms":
        digits = "".join(c for c in contact if c.isdigit())
        return f"phone ending {digits[-2:]}" if digits else "phone"
    return "email"


def _message(name, starts_at, signature, channel):
    local_start = starts_at.astimezone(_DUBLIN)
    when = local_start.strftime("%d %B %Y at %H:%M")
    prefix = f"Hi {name.strip()}, " if isinstance(name, str) and name.strip() else "Hello, "
    text = f"{prefix}your appointment is on {when}. {signature}"
    if channel == "sms" and len(text) > 160:
        prefix = "Hello, "
        text = f"{prefix}your appointment is on {when}. {signature}"
        if len(text) > 160:
            text = f"{when}. {signature}"
    return text


def plan_reminders(appointments, now):
    """Plan reminders; send_at values are timezone-aware UTC datetimes."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(timezone.utc)
    reminders = []

    for index, appointment in enumerate(appointments):
        try:
            required = (
                "id", "customer_name", "email", "phone", "country", "status",
                "starts_at", "optout_sms_v2",
            )
            if not isinstance(appointment, dict) or any(k not in appointment for k in required):
                raise ValueError("missing_fields")
            appointment_id = appointment["id"]
            if appointment_id is None or not str(appointment_id).strip():
                raise ValueError("invalid_id")
            starts_at = appointment["starts_at"]
            if not isinstance(starts_at, datetime) or starts_at.tzinfo is None or starts_at.utcoffset() is None:
                raise ValueError("invalid_starts_at")
            if isinstance(appointment["status"], str) and appointment["status"] == "cancelled":
                continue

            try:
                use_sms = _sms_eligible(appointment["optout_sms_v2"])
            except ValueError:
                logging.warning("Reminder skipped reason=sms_policy_unconfirmed")
                continue

            if use_sms:
                contact = appointment["phone"]
                if not isinstance(contact, str) or not contact.strip():
                    logging.warning("Reminder skipped reason=invalid_contact")
                    continue
                channel = "sms"
            else:
                contact = appointment["email"]
                if not isinstance(contact, str) or not contact.strip():
                    logging.warning("Reminder skipped reason=invalid_contact")
                    continue
                channel = "email"

            signature = _SIGNATURE_PL if appointment["country"] == "PL" else _SIGNATURE_DEFAULT
            start_utc = starts_at.astimezone(timezone.utc)
            for lead in (timedelta(hours=2), timedelta(hours=48)):
                candidate = start_utc - lead
                if lead == timedelta(hours=48) and candidate < now_utc:
                    candidate = now_utc

                local_candidate = candidate.astimezone(_DUBLIN)
                if local_candidate.hour >= 21 or local_candidate.hour < 8:
                    local_candidate = datetime.combine(
                        local_candidate.date(), time(20, 0), tzinfo=_DUBLIN
                    )
                send_at = local_candidate.astimezone(timezone.utc)
                if send_at < now_utc:
                    continue

                text = _message(
                    appointment["customer_name"], starts_at, signature, channel
                )
                reminders.append((
                    send_at, index, lead.total_seconds(),
                    {
                        "appointment_id": appointment_id,
                        "channel": channel,
                        "send_at": send_at,
                        "text": text,
                    },
                    _masked_contact(channel, contact),
                ))
        except Exception:
            logging.warning("Reminder skipped reason=invalid_appointment")

    reminders.sort(key=lambda item: (item[0], item[1], item[2]))
    result = []
    for _, _, _, reminder, masked_contact in reminders:
        logging.info(
            "Reminder planned appointment_id=%s channel=%s contact=%s",
            reminder["appointment_id"], reminder["channel"], masked_contact,
        )
        result.append(reminder)
    return result