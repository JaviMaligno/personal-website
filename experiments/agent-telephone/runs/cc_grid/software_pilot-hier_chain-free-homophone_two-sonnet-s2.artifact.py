"""Appointment reminder planning for Brennan Opticians.

Entry point: plan_reminders(appointments, now).

Assumptions and open questions for the client:
- The 2h reminder offset is an assumption (REMINDER_OFFSETS); please confirm.
- Appointments with no usable channel are skipped with a warning, not raised.
- SMS limit is 160 Python characters. Accented characters (the signatures
  contain some) force UCS-2 encoding, where a segment holds only 70
  characters. Should the limit be 70 for such messages?
- House rule asks to log the contact per reminder, but the privacy
  requirement forbids logging email or phone. The INFO line therefore
  carries appointment id and channel only. Please confirm.
- Reminders are dropped if they would land within MIN_LEAD (30 min) of the
  start, or after it, following quiet-hours adjustment.
- optout_sms_v2 is read by truthiness; the legacy opt_out field is ignored.
- No tests are included in this module; the test file was not produced
  because no tools were available to write or run it.
"""
import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("reminders")

TZ = ZoneInfo("Europe/Dublin")
# (label, offset before start). The 2h offset is an ASSUMPTION to confirm.
REMINDER_OFFSETS = (("48h", timedelta(hours=48)), ("2h", timedelta(hours=2)))
QUIET_START = time(21, 0)   # inclusive
QUIET_END = time(8, 0)      # exclusive
EVENING_SEND = time(20, 0)
SMS_MAX_LEN = 160
MIN_LEAD = timedelta(minutes=30)

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _local(dt):
    """Convert an aware datetime to Europe/Dublin."""
    return dt.astimezone(TZ)


def _wall(day, t):
    """Build a Europe/Dublin datetime from a local date and wall-clock time."""
    return datetime.combine(day, t, tzinfo=TZ)


def _in_quiet_hours(local_dt):
    """True if the local time is in [21:00, 08:00)."""
    t = local_dt.timetz().replace(tzinfo=None)
    return t >= QUIET_START or t < QUIET_END


def _adjust_for_quiet_hours(send_at, now):
    """Move send_at out of quiet hours: back to 20:00 local, else forward to 08:00."""
    local = _local(send_at)
    if not _in_quiet_hours(local):
        return send_at
    day = local.date()
    if local.timetz().replace(tzinfo=None) < QUIET_END:
        day -= timedelta(days=1)
    moved = _wall(day, EVENING_SEND)
    if moved >= now:  # aware comparison across different tzinfo uses instants
        return moved.astimezone(timezone.utc)
    local_now = _local(now)
    cand = _wall(local_now.date(), QUIET_END)
    if cand.astimezone(timezone.utc) <= now:
        cand = _wall(local_now.date() + timedelta(days=1), QUIET_END)
    return cand.astimezone(timezone.utc)


def _signature(country):
    """Signature by country (NFC normalised)."""
    pl = str(country or "").strip().upper() == "PL"
    sig = "Grzegorz Szczepański" if pl else "Siobhán Ní Dhuibhir"
    return unicodedata.normalize("NFC", sig)


def _format_when(starts_local):
    return (f"{_DAYS[starts_local.weekday()]} {starts_local.day:02d} "
            f"{_MONTHS[starts_local.month - 1]} {starts_local.year} "
            f"at {starts_local:%H:%M}")


def _compose(name, starts_local, signature):
    greeting = f"Hi {name}," if name else "Hi,"
    return f"{greeting} your appointment is on {_format_when(starts_local)}. {signature}"


def _build_sms_text(name, starts_local, signature):
    """Build an SMS of at most SMS_MAX_LEN chars, shortening only the name."""
    parts = str(name or "").split()
    candidates = [" ".join(parts)]
    if len(parts) > 1:
        candidates.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        candidates += [parts[0], parts[0][0]]
    candidates.append("")
    for cand in candidates:
        text = unicodedata.normalize("NFC", _compose(cand, starts_local, signature))
        if len(text) <= SMS_MAX_LEN:
            return text
    raise ValueError("SMS text exceeds limit even without a name")


def _clean(value):
    return str(value or "").strip()


def _channel_for(appt):
    """Return 'sms', 'email' or None. Uses only optout_sms_v2."""
    if _clean(appt.get("phone")) and not appt.get("optout_sms_v2"):
        return "sms"
    if _clean(appt.get("email")):
        return "email"
    return None


def _plan_one(appt, now):
    """Plan reminders for one appointment; returns (send_at_utc, rank, dict) tuples.

    Each reminder is built independently so one failure cannot affect the other.
    """
    if _clean(appt.get("status")).lower() == "cancelled":
        return []
    appt_id = appt.get("id")
    starts = appt.get("starts_at")
    if not _aware(starts):
        logger.warning("Skipping appointment %s: missing or naive starts_at", appt_id)
        return []
    channel = _channel_for(appt)
    if channel is None:
        logger.warning("Skipping appointment %s: no usable channel", appt_id)
        return []
    starts_utc = starts.astimezone(timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    starts_local = _local(starts)
    signature = _signature(appt.get("country"))
    name = _clean(appt.get("customer_name"))

    built = []
    # Build 2h first: it has priority.
    for rank, (label, offset) in sorted(
            enumerate(REMINDER_OFFSETS), key=lambda p: p[1][1]):
        try:
            send_at = max(starts_utc - offset, now_utc)
            send_at = _adjust_for_quiet_hours(send_at, now_utc)
            if send_at >= starts_utc or starts_utc - send_at < MIN_LEAD:
                logger.info("Dropped %s reminder for appointment %s: too close to start",
                            label, appt_id)
                continue
            if channel == "sms":
                text = _build_sms_text(name, starts_local, signature)
            else:
                text = _compose(name, starts_local, signature)
            built.append((send_at, label, rank, text))
        except Exception as exc:  # message omitted: could contain personal data
            logger.warning("Failed to build %s reminder for appointment %s (%s)",
                           label, appt_id, type(exc).__name__)
    # Dedupe identical instants: keep the 2h reminder (smallest offset).
    seen = {}
    for item in built:
        if item[0] not in seen:
            seen[item[0]] = item  # 2h is built first, so it wins
    out = []
    for send_at, label, rank, text in seen.values():
        logger.info("Planned %s reminder for appointment %s via %s",
                    label, appt_id, channel)
        out.append((send_at, rank, {
            "appointment_id": appt_id,
            "channel": channel,
            "send_at": _local(send_at),
            "text": text,
        }))
    return out


def plan_reminders(appointments, now):
    """Plan reminders for appointments as of `now` (aware datetime).

    Returns dicts {appointment_id, channel, send_at, text} sorted by send_at,
    then appointment id, then 2h before 48h. Inputs are not mutated.
    """
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    items = []
    for appt in appointments:
        try:
            items.extend(_plan_one(appt, now))
        except Exception as exc:
            logger.warning("Failed to plan appointment %s (%s)",
                           appt.get("id") if hasattr(appt, "get") else None,
                           type(exc).__name__)
    items.sort(key=lambda i: (i[0], str(i[2]["appointment_id"]), -i[1]))
    return [i[2] for i in items]