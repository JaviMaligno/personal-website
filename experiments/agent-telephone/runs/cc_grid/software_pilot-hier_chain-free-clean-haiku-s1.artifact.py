"""Brennan Opticians appointment reminder planner.

Standard library only (Python 3.9+). Uses zoneinfo for Europe/Dublin; the production host needs system tz data or the tzdata package installed.

Status: this module has not been executed. The test module
(brennan_reminders/tests/test_reminders.py) was not written in this session, so no test results exist.

Deviations from the design:
1. House rule asks for INFO lines that name the contact channel and contact. The design forbids logging email, phone, or name. This module logs only the appointment id and channel. The sending layer should look up contact details by appointment_id.
2. Sort key adds the text as a fourth tie-breaker. The specified key (send_at, str(id), channel) can tie when the same id appears twice in a batch, which would make output depend on input order.

Caveats:
- SMS with accented names (Siobhán, Szczepański) is sent as UCS-2 by most gateways, where one segment holds 70 characters, not 160. The 160 limit is implemented as specified.
- Returned dicts carry no recipient address. The sending layer must resolve contact details by appointment_id. This is an open integration point.
- Quiet-hour deferral to 08:00 (when an immediate send falls in quiet hours and the evening anchor has passed) is a proposal awaiting client confirmation.
"""

import logging
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("brennan_reminders")

DUBLIN_TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
REMINDER_FAR_OFFSET = timedelta(hours=48)
REMINDER_NEAR_OFFSET = timedelta(hours=2)
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
ANCHOR_HOUR = 20
MORNING_HOUR = 8
SMS_MAX_LENGTH = 160
SIGNATURE_PL = "Grzegorz Szczepa\u0144ski"
SIGNATURE_IE = "Siobh\u00e1n N\u00ed Dhuibhir"
MONTH_ABBREVIATIONS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})

_Record = namedtuple("_Record", "id start cancelled channel name signature")


class _Invalid(Exception):
    """Internal skip signal. Carries a reason code only."""


def _validate_now(now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")


def _present(value):
    return isinstance(value, str) and value.strip() != ""


def _is_cancelled(status):
    return isinstance(status, str) and status.strip().lower() in CANCELLED_STATUSES


def _is_opted_out(value):
    # False, None and an absent key mean not opted out. True and any other type mean opted out.
    return not (value is None or value is False)


def _choose_channel(raw):
    if _present(raw.get("phone")) and not _is_opted_out(raw.get("optout_sms_v2")):
        return "sms"
    if _present(raw.get("email")):
        return "email"
    return None


def _clean_name(value):
    if not isinstance(value, str):
        return None
    collapsed = " ".join(value.split())
    return collapsed or None


def _signature_for(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIGNATURE_PL
    return SIGNATURE_IE


def _to_dublin(dt_utc):
    return dt_utc.astimezone(DUBLIN_TZ)


def _dublin_wall_to_utc(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN_TZ).astimezone(UTC)


def _is_quiet(dt_utc):
    hour = _to_dublin(dt_utc).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _quiet_anchor(candidate):
    local = _to_dublin(candidate)
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    return _dublin_wall_to_utc(day, ANCHOR_HOUR)


def _deferral(now):
    local = _to_dublin(now)
    day = local.date()
    if local.hour >= QUIET_START_HOUR:
        day = day + timedelta(days=1)
    return _dublin_wall_to_utc(day, MORNING_HOUR)


def _apply_quiet_hours(candidate, now):
    if not _is_quiet(candidate):
        return candidate
    anchor = _quiet_anchor(candidate)
    if anchor >= now:
        return anchor
    if not _is_quiet(now):
        return now
    return _deferral(now)


def _candidate_send_times(start, now):
    candidates = [max(start - REMINDER_FAR_OFFSET, now)]
    near = start - REMINDER_NEAR_OFFSET
    if near > now:
        candidates.append(near)
    return candidates


def _schedule(record, now):
    sends = []
    for candidate in _candidate_send_times(record.start, now):
        final = _apply_quiet_hours(candidate, now)
        if final < record.start:
            sends.append(final)
    return sends


def _format_date(start_utc):
    local = _to_dublin(start_utc)
    return f"{local.day} {MONTH_ABBREVIATIONS[local.month - 1]} {local.year}"


def _format_time(start_utc):
    local = _to_dublin(start_utc)
    return f"{local.hour:02d}:{local.minute:02d}"


def _build_text(record, max_length):
    date_text = _format_date(record.start)
    time_text = _format_time(record.start)
    if max_length is None:
        options = [record.name]
    else:
        options = []
        if record.name:
            options.append(record.name)
            options.append(record.name.split(" ")[0])
        options.append(None)
    for name in options:
        greeting = f"Hi {name}," if name else "Hello,"
        text = (f"{greeting} reminder of your Brennan Opticians appointment "
                f"on {date_text} at {time_text}. {record.signature}")
        if max_length is None or len(text) <= max_length:
            return text
    return None


def _normalise_appointment(raw):
    if not isinstance(raw, dict):
        raise _Invalid("not_a_dict")
    appt_id = raw.get("id")
    if appt_id is None or (isinstance(appt_id, str) and not appt_id.strip()):
        raise _Invalid("missing_id")
    if isinstance(appt_id, bool) or not isinstance(appt_id, (str, int)):
        raise _Invalid("invalid_id")
    starts = raw.get("starts_at")
    if not isinstance(starts, datetime):
        raise _Invalid("invalid_starts_at")
    if starts.utcoffset() is None:
        raise _Invalid("naive_starts_at")
    return _Record(
        id=appt_id,
        start=starts.astimezone(UTC),
        cancelled=_is_cancelled(raw.get("status")),
        channel=_choose_channel(raw),
        name=_clean_name(raw.get("customer_name")),
        signature=_signature_for(raw.get("country")),
    )


def _id_label(raw):
    if isinstance(raw, dict):
        value = raw.get("id")
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            if isinstance(value, int) or value.strip():
                return str(value)
    return "<unknown>"


def _dedupe_and_sort(pending):
    seen = set()
    unique = []
    for index, item in pending:
        key = (index, item["send_at"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return sorted(unique, key=lambda r: (r["send_at"], str(r["appointment_id"]),
                                         r["channel"], r["text"]))


def plan_reminders(appointments, now):
    _validate_now(now)
    now_utc = now.astimezone(UTC)
    pending = []
    skipped = {"malformed": 0, "cancelled": 0, "not_in_future": 0,
               "no_channel": 0, "no_send_time": 0, "sms_too_long": 0,
               "out_of_range": 0}

    for index, raw in enumerate(appointments):
        try:
            record = _normalise_appointment(raw)
        except _Invalid as exc:
            logger.warning("skipped appointment id=%s reason=%s",
                           _id_label(raw), exc.args[0])
            skipped["malformed"] += 1
            continue

        if record.cancelled:
            skipped["cancelled"] += 1
            continue
        if record.start <= now_utc:
            skipped["not_in_future"] += 1
            continue
        if record.channel is None:
            logger.info("no reminder channel appointment_id=%s reason=no_channel",
                        record.id)
            skipped["no_channel"] += 1
            continue

        try:
            sends = _schedule(record, now_utc)
            if not sends:
                skipped["no_send_time"] += 1
                continue
            max_length = SMS_MAX_LENGTH if record.channel == "sms" else None
            text = _build_text(record, max_length)
        except OverflowError:
            logger.warning("skipped appointment id=%s reason=out_of_range", record.id)
            skipped["out_of_range"] += 1
            continue

        if text is None:
            logger.warning("skipped appointment id=%s reason=sms_too_long", record.id)
            skipped["sms_too_long"] += 1
            continue

        for send_at in sends:
            pending.append((index, {
                "appointment_id": record.id,
                "channel": record.channel,
                "send_at": send_at,
                "text": text,
            }))

    results = _dedupe_and_sort(pending)
    # Contact details are deliberately not logged; the sender resolves them by appointment_id.
    for item in results:
        logger.info("planned reminder appointment_id=%s channel=%s",
                    item["appointment_id"], item["channel"])
    logger.info("brennan reminders summary planned=%d malformed=%d cancelled=%d "
                "not_in_future=%d no_channel=%d no_send_time=%d sms_too_long=%d "
                "out_of_range=%d",
                len(results), skipped["malformed"], skipped["cancelled"],
                skipped["not_in_future"], skipped["no_channel"],
                skipped["no_send_time"], skipped["sms_too_long"],
                skipped["out_of_range"])
    return results