# Note: this run had no file or shell tools, so this module was not executed and the tests described in the brief were not written or run.
# -*- coding: utf-8 -*-
"""Appointment reminder planning for Brennan Opticians (standard library only)."""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

SMS_MAX_LENGTH = 160
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
TIMEZONE = ZoneInfo("Europe/Dublin")
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
REMINDER_OFFSETS = (timedelta(hours=48), timedelta(hours=2))
TWO_HOURS = timedelta(hours=2)


def _usable_str(value):
    return isinstance(value, str) and value.strip() != ""


def _is_cancelled(appt):
    status = appt.get("status")
    return isinstance(status, str) and status.strip().lower() == "cancelled"


def _is_opted_out(appt):
    value = appt.get("optout_sms_v2")
    if value is None:
        return False
    return bool(value)


def _channel_for(appt):
    if _usable_str(appt.get("phone")) and not _is_opted_out(appt):
        return "sms"
    if _usable_str(appt.get("email")):
        return "email"
    return None


def _signature_for(appt):
    return SIGNATURE_PL if appt.get("country") == "PL" else SIGNATURE_DEFAULT


def _is_quiet(t_utc):
    hour = t_utc.astimezone(TIMEZONE).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _shift_to_previous_evening(t_utc):
    local = t_utc.astimezone(TIMEZONE)
    day = local.date()
    if local.hour < QUIET_END_HOUR:
        day = day - timedelta(days=1)
    evening = datetime(day.year, day.month, day.day, 20, 0, tzinfo=TIMEZONE)
    return evening.astimezone(timezone.utc)


def _next_morning_after(now_utc):
    local = now_utc.astimezone(TIMEZONE)
    day = local.date()
    if local.hour >= QUIET_START_HOUR:
        day = day + timedelta(days=1)
    morning = datetime(day.year, day.month, day.day, QUIET_END_HOUR, 0, tzinfo=TIMEZONE)
    return morning.astimezone(timezone.utc)


def _schedule_point(starts_utc, offset, now_utc):
    s = starts_utc - offset
    if _is_quiet(s):
        s = _shift_to_previous_evening(s)
    if s < now_utc:
        if _is_quiet(now_utc):
            s = _next_morning_after(now_utc)
        elif starts_utc > now_utc:
            s = now_utc
        else:
            return None
    if s < now_utc or s >= starts_utc or _is_quiet(s):
        return None
    return s


def _format_date_time(local_dt):
    date_s = "{} {} {}".format(local_dt.day, MONTH_ABBR[local_dt.month - 1], local_dt.year)
    time_s = "{:02d}:{:02d}".format(local_dt.hour, local_dt.minute)
    return date_s, time_s


def _template(name, date_s, time_s, signature):
    if name:
        return ("Hi {}, reminder: your Brennan Opticians appointment is on {} at {}. {}"
                .format(name, date_s, time_s, signature))
    return ("Reminder: your Brennan Opticians appointment is on {} at {}. {}"
            .format(date_s, time_s, signature))


def _full_name(appt):
    value = appt.get("customer_name")
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _sms_name_options(full):
    if full is None:
        return [None]
    first = full.split()[0]
    return [full, first, first[0] + ".", None]


def _build_text(appt, starts_utc, channel, appt_id):
    local = starts_utc.astimezone(TIMEZONE)
    date_s, time_s = _format_date_time(local)
    signature = _signature_for(appt)
    full = _full_name(appt)
    if channel == "email":
        return _template(full, date_s, time_s, signature)
    for name_part in _sms_name_options(full):
        text = _template(name_part, date_s, time_s, signature)
        if len(text) <= SMS_MAX_LENGTH:
            return text
    raise ValueError("SMS for appointment {} cannot fit within {} characters"
                     .format(appt_id, SMS_MAX_LENGTH))


def _plan_for_appointment(appt, now_utc):
    if "id" not in appt:
        raise ValueError("missing required key: id")
    appt_id = appt["id"]

    if _is_cancelled(appt):
        logger.debug("skipped appointment_id=%s reason=cancelled", appt_id)
        return []

    if "starts_at" not in appt:
        raise ValueError("missing required key: starts_at for appointment {}".format(appt_id))
    starts = appt["starts_at"]
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError("starts_at must be timezone-aware for appointment {}".format(appt_id))
    starts_utc = starts.astimezone(timezone.utc)

    if starts_utc <= now_utc:
        logger.debug("skipped appointment_id=%s reason=past_start", appt_id)
        return []

    channel = _channel_for(appt)
    if channel is None:
        logger.debug("skipped appointment_id=%s reason=no_channel", appt_id)
        return []

    points = []
    for offset in REMINDER_OFFSETS:
        s = _schedule_point(starts_utc, offset, now_utc)
        if s is None:
            logger.debug("skipped appointment_id=%s reason=no_slot_before_start", appt_id)
        else:
            points.append((s, offset))

    if len(points) == 2 and points[0][0] == points[1][0]:
        points = [p for p in points if p[1] == TWO_HOURS]

    if not points:
        return []

    text = _build_text(appt, starts_utc, channel, appt_id)
    return [
        {"appointment_id": appt_id, "channel": channel, "send_at": s, "text": text}
        for s, _offset in points
    ]


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(timezone.utc)

    reminders = []
    for appt in appointments:
        if not isinstance(appt, dict):
            raise ValueError("each appointment must be a dict")
        reminders.extend(_plan_for_appointment(appt, now_utc))

    reminders.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))

    for r in reminders:
        logger.info("reminder appointment_id=%s channel=%s send_at=%s",
                    r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return reminders