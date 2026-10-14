"""Brennan Opticians appointment reminder planner.

Pure function. The only side effect is logging, and logs carry appointment IDs and channels only.

Open items for the client (defaults implemented, not decided here):
Q1 (R25): immediate reminders that fall in quiet hours are deferred to 08:00 Europe/Dublin.
Q2 (R29): the Polish signature contains "n with acute", which is outside GSM-7. The 160-character limit is applied by character count as stated. Real segmentation would be UCS-2 at 70 characters per segment.
Q3 (R22 step 4): customers with no usable phone and no opt-out get an email fallback.
Q4 (R21): the extra "recipient" key is included in each reminder.
Q5 (R31): no email subject is added.
Q6 (R22): phones are only trimmed and checked for non-empty. No E.164 validation is applied.

Conflict to resolve: the house logging rule asks each INFO line to name the contact, but R14 and R33 forbid logging emails and phone numbers. The implementation logs the appointment ID and channel only.

The tests were not executed in this environment.
"""

import logging
from datetime import datetime, time, timedelta, timezone

from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"


def _usable_phone(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _usable_email(value):
    if not isinstance(value, str):
        return None
    e = value.strip()
    left, sep, right = e.partition("@")
    if sep and left and right:
        return e
    return None


def _quiet(local):
    return local.hour >= 21 or local.hour < 8


def _at(day, hour):
    """Europe/Dublin local time at `hour`:00 on `day`, returned as aware UTC."""
    return datetime.combine(day, time(hour, 0), tzinfo=DUBLIN).astimezone(UTC)


def _next_allowed(x):
    """x is aware UTC. Returns x if outside quiet hours, else the next 08:00 local."""
    local = x.astimezone(DUBLIN)
    if not _quiet(local):
        return x
    day = local.date()
    if local.hour >= 21:
        day = day + timedelta(days=1)
    return _at(day, 8)


def _adjust(t, now):
    """Apply R24 past clamp is done by caller. This applies R25 quiet hours."""
    local = t.astimezone(DUBLIN)
    if _quiet(local):
        d = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
        t = _at(d, 20)
    if t < now:
        t = _next_allowed(now)
    return t


def _message(name, date_s, time_s, sig, level):
    """level 0: full name, 1: first name, 2: no greeting."""
    parts = name.split()
    if level == 0:
        who = " ".join(parts)
    elif level == 1:
        who = parts[0] if parts else ""
    else:
        who = ""
    body = f"reminder of your Brennan Opticians appointment on {date_s} at {time_s}. {sig}"
    if who:
        return f"Hi {who}, {body}"
    return body[:1].upper() + body[1:]


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    out = []

    for a in appointments:
        aid = a.get("id")

        if str(a.get("status") or "").strip().lower() == "cancelled":
            continue

        starts = a.get("starts_at")
        if starts is None:
            log.info("skip appointment_id=%s reason=missing_starts_at", aid)
            continue
        if not isinstance(starts, datetime) or starts.tzinfo is None or starts.utcoffset() is None:
            log.info("skip appointment_id=%s reason=naive_starts_at", aid)
            continue
        starts_utc = starts.astimezone(UTC)

        phone = _usable_phone(a.get("phone"))
        email = _usable_email(a.get("email"))
        optout = bool(a.get("optout_sms_v2"))

        if phone and not optout:
            channel, recipient = "sms", phone
        elif optout:
            if not email:
                log.info("skip appointment_id=%s reason=optout_no_email", aid)
                continue
            channel, recipient = "email", email
        elif email:
            channel, recipient = "email", email
        else:
            log.info("skip appointment_id=%s reason=no_usable_contact", aid)
            continue

        starts_local = starts_utc.astimezone(DUBLIN)
        date_s = starts_local.strftime("%d/%m/%Y")
        time_s = starts_local.strftime("%H:%M")
        sig = SIG_PL if str(a.get("country") or "").strip().lower() == "pl" else SIG_DEFAULT
        name = str(a.get("customer_name") or "").strip()

        text = ""
        for level in (0, 1, 2):
            text = _message(name, date_s, time_s, sig, level)
            if channel != "sms" or len(text) <= SMS_LIMIT:
                break

        seen = set()
        for offset in (timedelta(hours=48), timedelta(hours=2)):
            t = starts_utc - offset
            if t < now_utc:
                t = now_utc
            send_at = _adjust(t, now_utc)
            if send_at >= starts_utc:
                continue
            if send_at in seen:
                continue
            seen.add(send_at)
            out.append({
                "appointment_id": aid,
                "channel": channel,
                "recipient": recipient,
                "send_at": send_at,
                "text": text,
            })
            log.info("planned appointment_id=%s channel=%s", aid, channel)

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return out