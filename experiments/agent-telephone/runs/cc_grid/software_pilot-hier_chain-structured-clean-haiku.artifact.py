"""Appointment reminder planning for Brennan Opticians.

plan_reminders(appointments, now) returns a list of dicts with exactly the keys
appointment_id, channel, send_at (UTC-aware datetime) and text.

Addresses are never returned or logged (A4). The sender resolves the recipient
from the caller's own record using appointment_id: channel "sms" -> phone,
channel "email" -> email. Log lines carry appointment_id and channel only (R12).
The house logging rule asks for the contact in each INFO line, which conflicts
with R12, so support traces a contact through appointment_id instead.

Only id and starts_at are required keys. Missing customer_name, email, phone,
country and status are treated as absent (N2, A10, A11). Missing optout_sms_v2
is treated as False (A13).

Decisions marked [CONFIRM] are provisional and owned by the product owner:
A1, A2, A3, A5, A6, A7, A8, A9, A10, A11, A12, A13, N1, N2, N3, N4.

Open product question (A6): non-GSM characters (for example i-acute, a-acute,
n-acute) make the carrier encoding UCS-2 with a 70-character single-segment
limit. This module only checks len(text) against SMS_MAX_CHARS and does not
model GSM-7 or UCS-2.

The accompanying pytest suite is not included in this output and has not been
executed.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
QUIET_START_HOUR = 21  # [CONFIRM] A1, inclusive
QUIET_END_HOUR = 8  # [CONFIRM] A1, exclusive
EVENING_HOUR = 20  # [CONFIRM] A1
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
SMS_MAX_CHARS = 160  # [CONFIRM] A6
SIG_IE = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})  # [CONFIRM] A11
CHANNEL_ORDER = {"email": 0, "sms": 1}  # [CONFIRM] A12
TEXT_FIELDS = ("customer_name", "email", "phone", "country", "status")
UNKNOWN_ID = "unknown"

_SMS_FULL = "Hi {name}, reminder of your appointment at Brennan Opticians on {date} at {time}. {sig}"
_SMS_NO_NAME = "Reminder of your appointment at Brennan Opticians on {date} at {time}. {sig}"
_EMAIL_BODY = (
    "This is a reminder of your appointment at Brennan Opticians on {date} at {time}.\n\n{sig}"
)


class _Invalid(Exception):
    """Carries a reason code only, never record data."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _validate_now(now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise TypeError("now must be a timezone-aware datetime")
    return now.astimezone(UTC)


def _opt_str(rec, key):
    value = rec.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _Invalid("bad_type_" + key)
    value = value.strip()
    return value or None


def _validate_record(rec):
    if not isinstance(rec, dict):
        raise _Invalid("not_a_mapping")
    if "id" not in rec or "starts_at" not in rec:
        raise _Invalid("missing_key")
    rid = rec["id"]
    if not isinstance(rid, str) or not rid.strip():
        raise _Invalid("bad_id")
    starts = rec["starts_at"]
    if not isinstance(starts, datetime):
        raise _Invalid("bad_starts_at")
    if starts.utcoffset() is None:
        raise _Invalid("naive_starts_at")
    optout = rec.get("optout_sms_v2")
    if optout is None:
        optout = False
    elif not isinstance(optout, bool):
        raise _Invalid("bad_optout")
    fields = {key: _opt_str(rec, key) for key in TEXT_FIELDS}
    if fields["customer_name"]:
        fields["customer_name"] = " ".join(fields["customer_name"].split())
    return {"id": rid, "starts_at": starts, "optout": optout, **fields}


def _select_channel(fields):
    # R8 and A5: sms only when a phone exists and the customer has not opted out;
    # otherwise email if an address exists; otherwise nothing.
    if fields["phone"] and not fields["optout"]:
        return "sms"
    if fields["email"]:
        return "email"
    return None


def _signature(country):
    # A10: Polish signature only for country "pl" (casefold, stripped).
    return SIG_PL if country and country.casefold() == "pl" else SIG_IE


def _dublin_at(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN).astimezone(UTC)


def _in_quiet_window(local):
    return local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR


def _apply_quiet_window(send_at, now_utc, starts_utc):
    # A1 and A2. Returns None when the reminder must be dropped.
    local = send_at.astimezone(DUBLIN)
    if not _in_quiet_window(local):
        return send_at
    if local.hour >= QUIET_START_HOUR:
        evening = local.date()
    else:
        evening = local.date() - timedelta(days=1)
    target = _dublin_at(evening, EVENING_HOUR)
    if target >= now_utc:  # A2(a)
        return target
    now_local = now_utc.astimezone(DUBLIN)
    if not _in_quiet_window(now_local):  # A2(b)
        return now_utc
    # A2(c): next 08:00 Dublin after now, used only if strictly before starts_at.
    if now_local.hour >= QUIET_START_HOUR:
        morning = now_local.date() + timedelta(days=1)
    else:
        morning = now_local.date()
    morning_utc = _dublin_at(morning, QUIET_END_HOUR)
    return morning_utc if morning_utc < starts_utc else None


def _adjust(send_at, now_utc, starts_utc):
    if send_at is None:
        return None
    adjusted = _apply_quiet_window(send_at, now_utc, starts_utc)
    if adjusted is None or not (now_utc <= adjusted < starts_utc):
        return None
    return adjusted


def _schedule(starts_utc, now_utc):
    # R5, R6, A3, N1. Returns the surviving UTC send times for one appointment.
    p48 = starts_utc - FIRST_OFFSET
    first = p48 if p48 >= now_utc else now_utc
    p2 = starts_utc - SECOND_OFFSET
    second = p2 if p2 >= now_utc else None
    first = _adjust(first, now_utc, starts_utc)
    second = _adjust(second, now_utc, starts_utc)
    if first is not None and second is not None and first >= second:  # N1, R17
        first = None
    return [s for s in (first, second) if s is not None]


def _render_sms(name, date_s, time_s, sig):
    # R9 and A7: shorten the name only; date, time and signature are never cut.
    if name:
        parts = name.split()
        for shown in (name, parts[0], parts[0][0] + "."):
            text = _SMS_FULL.format(name=shown, date=date_s, time=time_s, sig=sig)
            if len(text) <= SMS_MAX_CHARS:
                return text
    text = _SMS_NO_NAME.format(date=date_s, time=time_s, sig=sig)
    return text if len(text) <= SMS_MAX_CHARS else None


def _render_email(name, date_s, time_s, sig):
    greeting = "Hello {},".format(name) if name else "Hello,"
    return greeting + "\n\n" + _EMAIL_BODY.format(date=date_s, time=time_s, sig=sig)


def _sort_key(reminder):
    return (
        reminder["send_at"],
        str(reminder["appointment_id"]),
        CHANNEL_ORDER[reminder["channel"]],
    )


def plan_reminders(appointments, now):
    """Return reminder dicts sorted by send_at (UTC).

    Each dict has exactly: appointment_id, channel ("sms" or "email"),
    send_at (UTC-aware datetime), text (str). Invalid, cancelled, past and
    duplicate-id records are skipped. Raises TypeError for a naive or
    non-datetime now.
    """
    now_utc = _validate_now(now)
    items = list(appointments)

    id_counts = {}
    for rec in items:
        rid = rec.get("id") if isinstance(rec, dict) else None
        if isinstance(rid, str) and rid.strip():
            id_counts[rid] = id_counts.get(rid, 0) + 1

    planned = []
    for rec in items:
        raw_id = rec.get("id") if isinstance(rec, dict) else None
        aid = raw_id if isinstance(raw_id, str) and raw_id.strip() else UNKNOWN_ID
        if aid != UNKNOWN_ID and id_counts.get(aid, 0) > 1:  # N3
            logger.warning("skipping appointment_id=%s reason=duplicate_id", aid)
            continue
        try:
            fields = _validate_record(rec)
        except _Invalid as exc:  # A13
            logger.warning("skipping appointment_id=%s reason=%s", aid, exc.reason)
            continue

        status = fields["status"]
        if status is not None and status.casefold() in CANCELLED_STATUSES:  # R11, A11
            continue

        starts_utc = fields["starts_at"].astimezone(UTC)  # A9
        if starts_utc <= now_utc:  # A3
            logger.info("skipping appointment_id=%s reason=starts_not_in_future", aid)
            continue

        channel = _select_channel(fields)
        if channel is None:
            logger.info("skipping appointment_id=%s reason=no_channel", aid)
            continue

        local = starts_utc.astimezone(DUBLIN)  # R4, A8, R14
        date_s = local.strftime("%d/%m/%Y")
        time_s = local.strftime("%H:%M")
        sig = _signature(fields["country"])
        if channel == "sms":
            text = _render_sms(fields["customer_name"], date_s, time_s, sig)
            if text is None:
                logger.warning("dropping appointment_id=%s reason=sms_too_long", aid)
                continue
        else:
            text = _render_email(fields["customer_name"], date_s, time_s, sig)

        for send_at in _schedule(starts_utc, now_utc):
            planned.append(
                {
                    "appointment_id": aid,
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }
            )

    planned.sort(key=_sort_key)  # R15, A12
    for reminder in planned:
        logger.info(
            "planned reminder appointment_id=%s channel=%s send_at=%s",
            reminder["appointment_id"],
            reminder["channel"],
            reminder["send_at"].isoformat(),
        )
    return planned