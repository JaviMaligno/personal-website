"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now).

Interpretation notes
- Two reminders per appointment: 48h and 2h before starts_at (computed in UTC, so DST
  never skews the offsets). A send time earlier than `now` is clamped to `now`. Both
  reminders may therefore be returned at `now`.
- Skipped: cancelled (strip/casefold), starts_at <= now, no usable contact.
  Invalid appointments (missing id/starts_at, naive or non-datetime starts_at) are
  skipped with a warning that carries the id only.
- Channel: SMS if phone is non-empty and optout_sms_v2 is not True, else email if an
  email is non-empty, else skipped. A missing optout_sms_v2 means "not opted out"
  (flag to client). The legacy opt_out field is never read. Never both channels.
- Quiet window: 21:00 to 08:00 Dublin wall clock (21:00 inclusive, 08:00 exclusive).
  A send time in the window moves to 20:00 Dublin the evening before (00:00-07:59 goes
  to the previous day, 21:00-23:59 to the same day). If that shifted time is before
  `now` (which also happens for clamped sends), it is deferred forward to the next
  08:00 Dublin after `now`. If that is >= starts_at the reminder is dropped. A
  send_at is never in the past and never after starts_at, so the never-past rule
  wins over the "move back" rule only by deferring, never by sending in the window.
- Duplicate ids: every entry is processed, with no dedupe. Output order is
  deterministic: (send instant, str(id), 48h before 2h), ties keep input order.
- Logging: one INFO line per planned reminder with appointment id, channel and
  send_at. The house rule asks for the contact too, but the DPC audit forbids logging
  emails, so no email, phone or name is ever logged. The id lets support trace the
  delivery in the CRM.
- Polish diacritics in the PL signature force UCS-2 SMS encoding (70 chars per
  segment), so the 160-character limit can still mean several billed segments.
"""
import logging
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
OFFSETS = ((timedelta(hours=48), 0), (timedelta(hours=2), 1))


def _text(v):
    return v.strip() if isinstance(v, str) else ""


def _channel(appt):
    if _text(appt.get("phone")) and appt.get("optout_sms_v2") is not True:
        return "sms"
    if _text(appt.get("email")):
        return "email"
    return None


def _signature(appt):
    if _text(appt.get("country")).casefold() == "pl":
        return "Grzegorz Szczepański"
    return "Chevonne Nee Divver"


def _compute_send_time(starts_at, offset, now):
    """Return send time (Dublin tz-aware) or None if the reminder must be dropped."""
    send = starts_at.astimezone(timezone.utc) - offset
    if send < now:
        send = now
    local = send.astimezone(DUBLIN)
    if 8 <= local.hour < 21:
        return local
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    shifted = datetime.combine(day, time(20, 0), tzinfo=DUBLIN)
    if shifted >= now:
        return shifted
    nl = now.astimezone(DUBLIN)
    day = nl.date() if nl.hour < 8 else nl.date() + timedelta(days=1)
    deferred = datetime.combine(day, time(8, 0), tzinfo=DUBLIN)
    if deferred >= starts_at:
        return None
    return deferred


def _shorten_name(name, level):
    """level 0 full name, 1 first name, 2 initial, 3 no name (None)."""
    parts = name.split()
    if not parts or level >= 3:
        return None
    if level == 0:
        return " ".join(parts)
    if level == 1:
        return parts[0]
    return parts[0][0] + "."


def _body(kind, greeting, when, sig):
    label = "reminder" if kind == 0 else "final reminder"
    lead = f"{greeting}, {label}" if greeting else label.capitalize()
    return f"{lead}: your Brennan Opticians appointment is on {when}. {sig}"


def _when(starts_at):
    local = starts_at.astimezone(DUBLIN)
    return f"{local:%d/%m/%Y} at {local:%H:%M}"


def _build_sms(name, starts_at, kind, sig):
    when = _when(starts_at)
    text = ""
    for level in range(4):
        n = _shorten_name(name, level)
        text = _body(kind, f"Hi {n}" if n else ("Hi" if level < 3 else ""), when, sig)
        if len(text) <= SMS_LIMIT:
            break
    return text


def _build_email(name, starts_at, kind, sig):
    n = _shorten_name(name, 0)
    return _body(kind, f"Hi {n}" if n else "Hi", _when(starts_at), sig)


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    out = []
    for appt in appointments:
        aid = appt.get("id") if isinstance(appt, dict) else None
        starts = appt.get("starts_at") if isinstance(appt, dict) else None
        if (aid is None or not isinstance(starts, datetime)
                or starts.tzinfo is None or starts.utcoffset() is None):
            log.warning("Skipping invalid appointment id=%s", "<missing>" if aid is None else aid)
            continue
        status = appt.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            continue
        if starts <= now:
            continue
        channel = _channel(appt)
        if channel is None:
            continue
        name = _text(appt.get("customer_name"))
        sig = _signature(appt)
        build = _build_sms if channel == "sms" else _build_email
        for offset, kind in OFFSETS:
            send_at = _compute_send_time(starts, offset, now)
            if send_at is None:
                continue
            out.append((send_at.astimezone(timezone.utc), str(aid), kind, {
                "appointment_id": aid,
                "channel": channel,
                "send_at": send_at,
                "text": build(name, starts, kind, sig),
            }))
    out.sort(key=lambda t: t[:3])
    for _, _, _, r in out:
        log.info("Planned reminder appointment_id=%s channel=%s send_at=%s",
                 r["appointment_id"], r["channel"], r["send_at"].isoformat())
    log.info("Planned %d reminders from %d appointments", len(out), len(appointments))
    return [t[3] for t in out]