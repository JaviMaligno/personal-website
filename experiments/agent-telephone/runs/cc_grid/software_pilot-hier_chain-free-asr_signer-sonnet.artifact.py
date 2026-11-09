"""Reminder planner for Brennan Opticians.

Public entry point: plan_reminders(appointments, now).

Returns a list of dicts {appointment_id, channel, send_at, text}, sorted by
(send_at, appointment_id, earlier-before-later reminder). All send_at values are
tz-aware datetimes expressed in Europe/Dublin. Naive datetimes raise ValueError.

Rules summary:
- Cancelled appointments (case-insensitive, stripped) and started/past ones are skipped.
- Reminders are due at T-48h and T-2h (absolute/UTC arithmetic). Due times in the past
  become "now". Never returns send_at < now.
- Quiet hours are Dublin local 21:00-08:00. A time in quiet hours moves back to 20:00
  local on the evening before the window (see _resolve_send_time for the precedence
  rule when that would be in the past).
- Channel is chosen per appointment: SMS if phone has digits and optout_sms_v2 is not
  true, otherwise email if it contains "@", otherwise the appointment is skipped with
  a warning (id only). The legacy "opt_out" field is never read.
- Dedup: same send_at or 48h >= 2h means the 48h one is dropped; any reminder at or
  after the start is dropped.

Flagged notes:
- SMS is limited to 160 Python characters as specified. Text signed by
  "Grzegorz Szczepanski" (with n-acute) is not GSM-7, so such SMS may be sent as
  UCS-2 (70 chars per segment) and could be split into several segments. 160 is
  still what is enforced.
- Logging deviation: the house rule asks for the contact in each INFO line, but the
  client rule is that name, email and phone are never logged. This module logs the
  appointment id and channel only, so support traces deliveries by id.
"""
import logging
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _in_quiet(dt):
    h = dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _back_to_20(dt):
    """Dublin 20:00 on the evening before the quiet window containing dt."""
    loc = dt.astimezone(DUBLIN)
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    return datetime.combine(day, time(20, 0), tzinfo=DUBLIN)


def _next_0800(dt):
    """Next Dublin 08:00 at or after dt (dt is expected to be in quiet hours)."""
    loc = dt.astimezone(DUBLIN)
    day = loc.date() + timedelta(days=1) if loc.hour >= 21 else loc.date()
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN)


def _resolve_send_time(due, now):
    """Return the send time for a reminder due at `due`, honouring quiet hours.

    Deliberate precedence: never-in-past beats the move-back rule, and quiet hours
    are honoured by deferring forward rather than sending at night.
      1. due < now becomes now.
      2. Not in quiet hours: use it.
      3. In quiet hours: move back to 20:00 local; if that is >= now, use it.
      4. Otherwise (move-back would be in the past): if now is outside quiet hours,
         send now; if inside, defer to the next 08:00 local.
    The caller drops the result if a deferral lands at/after the appointment start
    (or, for the 48h reminder, at/after the 2h reminder).
    """
    if due < now:
        due = now
    if not _in_quiet(due):
        return due
    moved = _back_to_20(due)
    if moved >= now:
        return moved
    if not _in_quiet(now):
        return now
    return _next_0800(now)


def _usable_phone(p):
    return isinstance(p, str) and any(c.isdigit() for c in p)


def _usable_email(e):
    return isinstance(e, str) and bool(e.strip()) and "@" in e.strip()


def _build_text(name, local_start, signature, limit):
    date = f"{local_start.day} {_MONTHS[local_start.month - 1]} {local_start.year}"
    hhmm = f"{local_start.hour:02d}:{local_start.minute:02d}"
    tail = f"reminder: your Brennan Opticians appointment is on {date} at {hhmm}. {signature}"
    name = " ".join(name.split()) if isinstance(name, str) else ""
    for n in range(len(name), 0, -1):
        text = f"Hi {name[:n].rstrip()}, {tail}"
        if limit is None or len(text) <= limit:
            return text
    return f"Hi, {tail}"


def _require_aware(dt, what):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")


def plan_reminders(appointments, now):
    """Plan reminders; see module docstring. Does not mutate its input."""
    _require_aware(now, "now")
    now = now.astimezone(timezone.utc)
    results = []
    skipped = 0

    for a in appointments:
        _require_aware(a.get("starts_at"), "starts_at")
        appt_id = a.get("id")
        if str(a.get("status") or "").strip().lower() == "cancelled":
            continue
        start = a["starts_at"].astimezone(timezone.utc)
        if start <= now:
            continue

        if _usable_phone(a.get("phone")) and a.get("optout_sms_v2") is not True:
            channel = "sms"
        elif _usable_email(a.get("email")):
            channel = "email"
        else:
            logger.warning("No usable contact channel, skipping appointment %s", appt_id)
            skipped += 1
            continue

        country = str(a.get("country") or "").strip().upper()
        signature = "Grzegorz Szczepański" if country == "PL" else "Chevonne Nee Divver"
        text = _build_text(a.get("customer_name"), start.astimezone(DUBLIN),
                           signature, SMS_LIMIT if channel == "sms" else None)

        # 2h reminder first (it has priority).
        r2 = _resolve_send_time(start - timedelta(hours=2), now)
        if r2 >= start:
            logger.warning("Dropping 2h reminder for appointment %s", appt_id)
            r2 = None
        r48 = _resolve_send_time(start - timedelta(hours=48), now)
        limit = r2 if r2 is not None else start
        if r48 >= limit:
            if r48 >= start:
                logger.warning("Dropping 48h reminder for appointment %s", appt_id)
            r48 = None

        for order, when in ((0, r48), (1, r2)):
            if when is None:
                continue
            when = when.astimezone(DUBLIN)
            results.append((when, str(appt_id), order, {
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": when,
                "text": text,
            }))
            logger.info("Planned %s reminder for appointment %s at %s",
                        channel, appt_id, when.isoformat())

    results.sort(key=lambda r: r[:3])
    logger.info("Planned %d reminders, skipped %d appointments", len(results), skipped)
    return [r[3] for r in results]