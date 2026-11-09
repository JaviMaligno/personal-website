"""Appointment reminder planner for Brennan Opticians.

Single self-contained module, standard library only. Tests from the spec are not
included here, and this file has not been executed.

Contact details (email, phone) are never logged (R13). The log line for each
planned reminder carries the appointment id, ordinal, channel and action only.
"""
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

logger = logging.getLogger("brennan_reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED_KEYS = ("id", "customer_name", "email", "phone", "country",
                 "status", "starts_at", "optout_sms_v2")
HOURS_48 = timedelta(hours=48)
HOURS_2 = timedelta(hours=2)
ONE_DAY = timedelta(days=1)


# ---------------------------------------------------------------- schedule

def _in_quiet_window(local):
    """True for local times 21:00 <= t < 08:00 (Q1)."""
    return local.hour >= 21 or local.hour < 8


def _local_to_utc(day, hour):
    """20:00 or 08:00 on a Dublin-local calendar date, as aware UTC."""
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN).astimezone(UTC)


def _place(candidate, now, starts):
    """Apply Q1 to Q3. Returns (send_utc, action) or (None, reason)."""
    local = candidate.astimezone(DUBLIN)
    if not _in_quiet_window(local):
        return candidate, None

    # Q1: move to 20:00 on the evening the window began.
    evening_day = local.date() if local.hour >= 21 else local.date() - ONE_DAY
    evening = _local_to_utc(evening_day, 20)
    if evening >= now:
        return evening, "moved_to_20:00"

    # Q2 (a) handled above. Q2 (b): now is outside the window, send now.
    now_local = now.astimezone(DUBLIN)
    if not _in_quiet_window(now_local):
        return now, "sent_at_now"

    # Q2 (c) and Q3: earliest legal instant is 08:00 on the morning the window ends.
    morning_day = now_local.date() if now_local.hour < 8 else now_local.date() + ONE_DAY
    morning = _local_to_utc(morning_day, 8)
    if morning < starts:
        return morning, "moved_to_08:00"
    return None, "dropped_unplaceable"


def _settle(candidate, now, starts, replaced):
    """Place a candidate and apply the Q8 drop rules. Returns (send_utc, action) or (None, reason)."""
    send, action = _place(candidate, now, starts)
    if send is None:
        return None, action
    if send < now:
        return None, "dropped_past"
    if send >= starts:
        return None, "dropped_too_late"
    if _in_quiet_window(send.astimezone(DUBLIN)):
        return None, "dropped_unplaceable"
    if action is None:
        action = "sent_at_now" if replaced else "on_schedule"
    return send, action


# -------------------------------------------------------------------- text

def _clean_name(value):
    return " ".join(str(value or "").split())


def _signature(country):
    return SIG_PL if str(country or "").strip().upper() == "PL" else SIG_DEFAULT


def _name_steps(name):
    """Q4 order: full name, 'First L.', first token, then omitted (None)."""
    tokens = name.split()
    if not tokens:
        return [None]
    steps = [" ".join(tokens)]
    if len(tokens) > 1:
        steps.append(f"{tokens[0]} {tokens[-1][0]}.")
    steps.append(tokens[0])
    steps.append(None)
    return steps


def _sms_body(name, date_str, time_str, sig):
    if name:
        return (f"Brennan Opticians: Hi {name}, you have an appointment on "
                f"{date_str} at {time_str}. {sig}")
    return (f"Brennan Opticians: you have an appointment on "
            f"{date_str} at {time_str}. {sig}")


def _sms_text(name, date_str, time_str, sig):
    """Returns the first SMS body within 160 characters, or None."""
    for step in _name_steps(name):
        body = _sms_body(step, date_str, time_str, sig)
        if len(body) <= SMS_LIMIT:
            return body
    return None


def _email_text(name, date_str, time_str, sig):
    greet = f"Hi {name}," if name else "Hi,"
    return (f"{greet}\n\nThis is a reminder of your appointment at Brennan "
            f"Opticians on {date_str} at {time_str}.\n\n{sig}")


# ----------------------------------------------------------------- planner

def _has(value):
    return value is not None and str(value).strip() != ""


def _choose_channel(appt):
    """Q6: sms when phone present and not opted out, else email when email present."""
    if _has(appt["phone"]) and not bool(appt["optout_sms_v2"]):
        return "sms"
    if _has(appt["email"]):
        return "email"
    return None


def _plan_one(appt, now):
    """Returns a list of (send_utc, sid, ordinal, reminder_dict) for one appointment."""
    if not isinstance(appt, Mapping):
        logger.warning("skipping malformed appointment: not a mapping")
        return []
    aid = appt.get("id")
    sid = str(aid)

    missing = [k for k in REQUIRED_KEYS if k not in appt]
    if missing:
        logger.warning("skipping malformed appointment id=%s missing=%s",
                       sid, ",".join(missing))
        return []
    starts = appt["starts_at"]
    if not (isinstance(starts, datetime) and starts.utcoffset() is not None):
        logger.warning("skipping malformed appointment id=%s: starts_at is not aware", sid)
        return []

    status = str(appt["status"] or "").strip().lower()
    if status in ("cancelled", "canceled"):
        logger.info("dropped id=%s reason=dropped_cancelled", sid)
        return []

    channel = _choose_channel(appt)
    if channel is None:
        logger.info("dropped id=%s reason=dropped_no_contact", sid)
        return []

    starts_utc = starts.astimezone(UTC)
    starts_local = starts.astimezone(DUBLIN)
    scheduled = []  # (ordinal, send_utc, action)

    # Build the 2-hour reminder first (R18).
    c2 = starts_utc - HOURS_2
    if c2 < now:
        logger.info("dropped id=%s ordinal=2 reason=dropped_past", sid)
    else:
        send, action = _settle(c2, now, starts_utc, replaced=False)
        if send is None:
            logger.info("dropped id=%s ordinal=2 reason=%s", sid, action)
        else:
            scheduled.append((2, send, action))

    # 48-hour reminder, R6 replaces a past point with now.
    c1 = starts_utc - HOURS_48
    replaced = c1 < now
    if replaced:
        c1 = now
    send, action = _settle(c1, now, starts_utc, replaced)
    if send is None:
        logger.info("dropped id=%s ordinal=1 reason=%s", sid, action)
    else:
        scheduled.append((1, send, action))

    # R9: never two reminders with the same channel and time.
    if len(scheduled) == 2 and scheduled[0][1] == scheduled[1][1]:
        logger.info("dropped id=%s ordinal=1 reason=dropped_duplicate", sid)
        scheduled = scheduled[:1]
    if not scheduled:
        return []

    name = _clean_name(appt["customer_name"])
    sig = _signature(appt["country"])
    date_str = f"{starts_local.day} {MONTHS[starts_local.month - 1]} {starts_local.year}"
    time_str = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    if channel == "sms":
        body = _sms_text(name, date_str, time_str, sig)
        if body is None:
            logger.warning("dropped id=%s reason=sms_too_long", sid)
            return []
    else:
        body = _email_text(name, date_str, time_str, sig)

    out = []
    for ordinal, send, action in scheduled:
        logger.info("planned id=%s ordinal=%d channel=%s action=%s",
                    sid, ordinal, channel, action)
        out.append((send, sid, ordinal, {
            "appointment_id": aid,
            "channel": channel,
            "send_at": send.astimezone(DUBLIN),
            "text": body,
        }))
    return out


def plan_reminders(appointments, now):
    """Plan reminders for a list of appointment dicts.

    Returns a list of dicts with keys appointment_id, channel, send_at, text,
    sorted by send_at, then appointment id, then ordinal (1 = 48h, 2 = 2h).
    """
    if not (isinstance(now, datetime) and now.utcoffset() is not None):
        raise ValueError("now must be a timezone-aware datetime")
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list")

    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda p: (p[0], p[1], p[2]))

    result = []
    for send, sid, _ordinal, reminder in planned:
        if send < now_utc:  # R7 final guard
            logger.warning("dropped id=%s reason=guard_past_now", sid)
            continue
        result.append(reminder)
    return result