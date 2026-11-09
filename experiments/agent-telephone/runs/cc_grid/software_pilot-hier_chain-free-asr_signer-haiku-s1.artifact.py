import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_LENGTH = 160

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

SIGNATURE_DEFAULT = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"

SMS_TEMPLATE_NAMED = "Hi {name}, your Brennan Opticians appointment is on {date} at {time}. {signature}"
SMS_TEMPLATE_PLAIN = "Reminder: your Brennan Opticians appointment is on {date} at {time}. {signature}"
EMAIL_TEMPLATE_NAMED = ("Dear {name},\n\nThis is a reminder of your appointment at Brennan Opticians "
                        "on {date} at {time}.\n\n{signature}")
EMAIL_TEMPLATE_PLAIN = ("Hello,\n\nThis is a reminder of your appointment at Brennan Opticians "
                        "on {date} at {time}.\n\n{signature}")

_QUIET_START = time(21, 0)
_QUIET_END = time(8, 0)
_EVENING = time(20, 0)
_MORNING = time(8, 0)


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _is_quiet(local):
    t = local.time()
    return t >= _QUIET_START or t < _QUIET_END


def _quiet_evening_before(local):
    day = local.date()
    if local.hour < 8:
        day = day - timedelta(days=1)
    return datetime.combine(day, _EVENING, tzinfo=DUBLIN)


def _quiet_morning_end(local):
    day = local.date()
    if local.hour >= 21:
        day = day + timedelta(days=1)
    return datetime.combine(day, _MORNING, tzinfo=DUBLIN)


def _apply_quiet_hours(t0, now):
    local = t0.astimezone(DUBLIN)
    if not _is_quiet(local):
        return t0
    cand = _quiet_evening_before(local)
    if cand >= now:
        return cand
    now_local = now.astimezone(DUBLIN)
    if not _is_quiet(now_local):
        return now
    return _quiet_morning_end(now_local)


def _slot_send_time(starts_utc, offset, now_utc):
    t = starts_utc - offset
    t0 = t if t >= now_utc else now_utc
    final = _apply_quiet_hours(t0, now_utc)
    if final >= starts_utc:
        return None
    return final


def _is_cancelled(status):
    return isinstance(status, str) and status.strip().lower() == "cancelled"


def _format_date(local):
    return f"{WEEKDAY_NAMES[local.weekday()]} {local.day} {MONTH_NAMES[local.month - 1]} {local.year}"


def _format_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def _sms_text(name, date_text, time_text, signature):
    base = dict(date=date_text, time=time_text, signature=signature)
    candidates = []
    if name:
        candidates.append(SMS_TEMPLATE_NAMED.format(name=name, **base))
        first = name.split()[0]
        if first != name:
            candidates.append(SMS_TEMPLATE_NAMED.format(name=first, **base))
    candidates.append(SMS_TEMPLATE_PLAIN.format(name="", **base))
    for text in candidates:
        if len(text) <= SMS_MAX_LENGTH:
            return text
    return None


def _email_text(name, date_text, time_text, signature):
    base = dict(date=date_text, time=time_text, signature=signature)
    if name:
        return EMAIL_TEMPLATE_NAMED.format(name=name, **base)
    return EMAIL_TEMPLATE_PLAIN.format(name="", **base)


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be timezone-aware")
    appointments = list(appointments)
    for appt in appointments:
        if not _is_aware(appt.get("starts_at")):
            raise ValueError(
                f"starts_at must be timezone-aware (appointment id {appt.get('id')})"
            )

    now_utc = now.astimezone(UTC)
    results = []

    for appt in appointments:
        aid = appt.get("id")

        if _is_cancelled(appt.get("status")):
            logger.debug("skipped: cancelled (appointment %s)", aid)
            continue

        starts_utc = appt["starts_at"].astimezone(UTC)
        if starts_utc <= now_utc:
            logger.debug("skipped: appointment not in the future (appointment %s)", aid)
            continue

        # Channel decision.
        phone = appt.get("phone")
        phone_present = isinstance(phone, str) and phone.strip() != ""
        opted_out = appt.get("optout_sms_v2") is not False
        use_sms = phone_present and not opted_out

        email = appt.get("email")
        has_email = isinstance(email, str) and email.strip() != ""

        # Text ingredients (contact values are never logged or embedded in logs).
        raw_name = appt.get("customer_name")
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        country = appt.get("country")
        country_norm = country.strip().upper() if isinstance(country, str) else ""
        signature = SIGNATURE_PL if country_norm == "PL" else SIGNATURE_DEFAULT

        local_start = starts_utc.astimezone(DUBLIN)
        date_text = _format_date(local_start)
        time_text = _format_time(local_start)

        s48 = _slot_send_time(starts_utc, timedelta(hours=48), now_utc)
        s2 = _slot_send_time(starts_utc, timedelta(hours=2), now_utc)
        if s48 is None or s2 is None:
            logger.debug("dropped: send time not before start (appointment %s)", aid)

        if s48 is not None and s2 is not None and s48 >= s2:
            logger.debug("collapsed duplicate slot (appointment %s)", aid)
            s48 = None

        for send_at in (s48, s2):
            if send_at is None:
                continue

            channel = None
            text = None
            if use_sms:
                text = _sms_text(name, date_text, time_text, signature)
                if text is not None:
                    channel = "sms"
                elif has_email:
                    logger.warning("fell back to email: sms too long (appointment %s)", aid)
                else:
                    logger.warning(
                        "skipped: sms too long and no email address (appointment %s)", aid
                    )
                    continue

            if channel is None:
                if not has_email:
                    logger.warning("skipped: no email address (appointment %s)", aid)
                    continue
                channel = "email"
                text = _email_text(name, date_text, time_text, signature)

            send_local = send_at.astimezone(DUBLIN)
            # Contact values are withheld by the privacy rule; support traces the
            # delivery through the appointment id and channel.
            logger.info(
                "planned %s reminder for appointment %s at %s",
                channel, aid, send_local.isoformat(),
            )
            results.append({
                "appointment_id": aid,
                "channel": channel,
                "send_at": send_local,
                "text": text,
            })

    results.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    logger.info(
        "planned %d reminder(s) for %d appointment(s)",
        len(results), len(appointments),
    )
    return results