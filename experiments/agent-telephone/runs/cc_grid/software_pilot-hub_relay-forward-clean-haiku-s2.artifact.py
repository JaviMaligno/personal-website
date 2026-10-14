import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"
QUIET_START = 21
QUIET_END = 8
EVENING_TARGET = 20


class _Skip(Exception):
    """Appointment yields no reminders. The message is a reason code only."""


class _Malformed(_Skip):
    """Record is malformed. The message is a reason code only."""


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _id_for_log(appt):
    if isinstance(appt, dict):
        return _text(appt.get("id")) or "missing"
    return "invalid"


def _is_quiet(dt):
    hour = dt.astimezone(DUBLIN).hour
    return hour >= QUIET_START or hour < QUIET_END


def _dublin_at(base, hour, day_offset=0):
    day = base.astimezone(DUBLIN).date() + timedelta(days=day_offset)
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=DUBLIN).astimezone(UTC)


def _resolve(t, now):
    """Apply quiet hours to candidate time t. Precedence: never in the past,
    then quiet hours, then move back to 20:00 when that target is still ahead."""
    if not _is_quiet(t):
        return t
    local_hour = t.astimezone(DUBLIN).hour
    target = _dublin_at(t, EVENING_TARGET, 0 if local_hour >= QUIET_START else -1)
    if target >= now:
        return target
    if not _is_quiet(now):
        return now
    morning_offset = 0 if now.astimezone(DUBLIN).hour < QUIET_END else 1
    return _dublin_at(now, QUIET_END, morning_offset)


def _signature(country):
    return PL_SIGNATURE if _text(country).upper() == "PL" else DEFAULT_SIGNATURE


def _compose(name, date_s, time_s, signature):
    greeting = f"Hello {name}," if name else "Hello,"
    return f"{greeting} your appointment at Brennan Opticians on {date_s} at {time_s}.\n{signature}"


def _plan_one(appt, now):
    if not isinstance(appt, dict):
        raise _Malformed("not_a_mapping")
    appt_id = appt.get("id")
    if _text(appt_id) == "":
        raise _Malformed("missing_id")
    starts = appt.get("starts_at")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise _Malformed("bad_starts_at")
    starts_utc = starts.astimezone(UTC)

    if _text(appt.get("status")).lower() in ("cancelled", "canceled"):
        raise _Skip("cancelled")
    if starts_utc <= now:
        raise _Skip("already_started")

    h48 = starts_utc - timedelta(hours=48)
    h2 = starts_utc - timedelta(hours=2)
    if h2 <= now:
        candidates = [("2h", now)]
    elif h48 <= now:
        candidates = [("48h", now), ("2h", h2)]
    else:
        candidates = [("48h", h48), ("2h", h2)]

    # Collapse: when both resolve to the same instant, keep the 2-hour-derived one.
    by_time = {}
    for kind, t in candidates:
        send = _resolve(t, now)
        if send >= starts_utc:
            continue
        if send not in by_time or kind == "2h":
            by_time[send] = kind
    if not by_time:
        raise _Skip("no_valid_send_time")

    phone = _text(appt.get("phone"))
    email = _text(appt.get("email"))
    opted_out = appt.get("optout_sms_v2") is not False
    if phone and not opted_out:
        channel = "sms"
    elif email:
        channel = "email"
    else:
        raise _Skip("no_eligible_channel")

    local = starts_utc.astimezone(DUBLIN)
    date_s = local.strftime("%d/%m/%Y")
    time_s = local.strftime("%H:%M")
    signature = _signature(appt.get("country"))
    name = _text(appt.get("customer_name"))
    first = name.split()[0] if name else ""

    # Email uses the full name. SMS shortens the name in steps to fit the limit.
    full_text = _compose(name, date_s, time_s, signature)
    sms_text = None
    for candidate in (full_text, _compose(first, date_s, time_s, signature),
                      _compose("", date_s, time_s, signature)):
        if len(candidate) <= SMS_LIMIT:
            sms_text = candidate
            break

    if channel == "sms" and sms_text is None:
        if not email:
            raise _Skip("sms_too_long")
        logger.warning("sms too long, falling back to email appointment_id=%s reason=sms_too_long",
                       appt_id)
        channel = "email"

    text = sms_text if channel == "sms" else full_text
    return [
        {"appointment_id": appt_id, "channel": channel, "send_at": send, "text": text}
        for send in by_time
    ]


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)

    reminders = []
    for appt in appointments:
        try:
            planned = _plan_one(appt, now_utc)
        except _Malformed as exc:
            logger.warning("skipped malformed record id=%s reason=%s", _id_for_log(appt), exc)
        except _Skip as exc:
            logger.debug("no reminders id=%s reason=%s", _id_for_log(appt), exc)
        except Exception as exc:
            logger.warning("skipped record id=%s reason=unexpected_%s",
                           _id_for_log(appt), type(exc).__name__)
        else:
            for r in planned:
                # The contact value itself is never logged; only which field was used.
                logger.info(
                    "reminder planned appointment_id=%s channel=%s contact_field=%s send_at=%s",
                    r["appointment_id"], r["channel"],
                    "phone" if r["channel"] == "sms" else "email",
                    r["send_at"].isoformat(),
                )
                reminders.append(r)

    reminders.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    return reminders