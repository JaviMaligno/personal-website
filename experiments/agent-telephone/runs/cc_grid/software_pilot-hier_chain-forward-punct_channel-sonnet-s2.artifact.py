"""Appointment reminder planner for Brennan Opticians.

Assumptions:
- optout_sms_v2 polarity: per the brief ("text them if ... optout_sms_v2 is true"),
  True means SMS is permitted. This lives in one function, _sms_permitted().
  Only the literal True counts; missing, None or strings like "true" do not.
- No phone or SMS not permitted: no reminders at all. There is no email fallback,
  so the email channel is never emitted, and the email field is never read.
- Quiet hours (21:00-08:00 Europe/Dublin): shift back to the preceding 20:00. If that
  is already in the past, use now when now is not quiet, otherwise drop the reminder.
  Nothing is ever sent in quiet hours or in the past.
- Collision: if the 48h reminder resolves at or after the 2h one, only the 2h one is kept.
  Appointments within 2h get only the 2h reminder.
- Length is counted in Python characters (max 160). GSM-7/UCS-2 segmenting is not
  modelled. Diacritics force UCS-2 (70 chars per segment), a real cost risk.
- send_at is returned tz-aware in Europe/Dublin, equal to the UTC instant.
- Appointments with starts_at <= now get no reminders.
- Privacy: only appointment ids and decisions are logged. The brief and task forbid
  logging email, phone or name, so the "contact" is identified by appointment id and
  channel only, never by the raw phone number.
- Tests (test_reminders.py) were not produced because this run had no file or
  execution tools.
"""
import logging
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
DUB = ZoneInfo("Europe/Dublin")
MAX_SMS = 160


def _sms_permitted(appt):
    return appt.get("optout_sms_v2") is True


def _is_quiet(local_dt):
    return local_dt.hour >= 21 or local_dt.hour < 8


def _shift_back_to_20(local_dt):
    d = local_dt.date()
    if local_dt.hour < 8:
        d -= timedelta(days=1)
    return datetime.combine(d, time(20, 0), tzinfo=DUB)


def _signature(country):
    if str(country or "").strip().upper() == "PL":
        return "Grzegorz Szczepański"
    return "Siobhán Ní Dhuibhir"


def _clean_name(name):
    if not name:
        return ""
    s = "".join(c if c.isprintable() else " " for c in str(name))
    return re.sub(r"\s+", " ", s).strip()


def _shorten_name(name):
    """Return progressively shorter name variants; last is '' (generic greeting)."""
    parts = name.split()
    out = [name]
    if len(parts) > 1:
        out.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        out.append(parts[0])
        out.append(f"{parts[0][0]}.")
    out.append("")
    return out


def _build_text(appt, appt_id):
    local = appt["starts_at"].astimezone(DUB)
    when = f"{local:%d/%m/%Y} at {local:%H:%M}"
    sig = _signature(appt.get("country"))
    name = _clean_name(appt.get("customer_name"))
    for i, cand in enumerate(_shorten_name(name)):
        greet = f"Hi {cand}," if cand else "Hi,"
        text = f"Brennan Opticians: {greet} reminder of your appointment on {when}. {sig}"
        if len(text) <= MAX_SMS:
            if i > 0 and name:
                logger.info("Appointment %s: customer name shortened", appt_id)
            return text
    raise AssertionError("text too long even without name")  # pragma: no cover


def _resolve(target, now):
    t = max(target, now)
    if not _is_quiet(t.astimezone(DUB)):
        return t
    s = _shift_back_to_20(t.astimezone(DUB))
    if s >= now:
        return s
    if not _is_quiet(now.astimezone(DUB)):
        return now
    return None


def plan_reminders(appointments, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("naive 'now'")
    items = []  # (send_at, id_str, order, dict)
    for appt in appointments:
        aid = appt.get("id")
        start = appt.get("starts_at")
        if start is None or start.tzinfo is None or start.utcoffset() is None:
            raise ValueError(f"naive starts_at for appointment {aid}")
        if str(appt.get("status") or "").strip().lower() == "cancelled":
            logger.info("Appointment %s: skipped, cancelled", aid)
            continue
        if not str(appt.get("phone") or "").strip() or not _sms_permitted(appt):
            logger.info("Appointment %s: skipped, SMS not possible or not permitted", aid)
            continue
        if start <= now:
            logger.info("Appointment %s: skipped, already started", aid)
            continue

        r2 = _resolve(start - timedelta(hours=2), now)
        r48 = None
        if start - now > timedelta(hours=2):
            r48 = _resolve(start - timedelta(hours=48), now)
        if r2 is None:
            logger.info("Appointment %s: 2h reminder dropped (quiet hours)", aid)
        if r48 is None and start - now > timedelta(hours=2):
            logger.info("Appointment %s: 48h reminder dropped (quiet hours)", aid)
        if r2 is not None and r48 is not None and r48 >= r2:
            logger.info("Appointment %s: 48h reminder dropped, collides with 2h", aid)
            r48 = None

        text = _build_text(appt, aid)
        for order, when in ((0, r48), (1, r2)):
            if when is None or when > start or when < now:
                continue
            logger.info(
                "Planned %s reminder for appointment %s via sms",
                "48h" if order == 0 else "2h", aid,
            )
            items.append((when, str(aid), order, {
                "appointment_id": aid,
                "channel": "sms",
                "send_at": when.astimezone(DUB),
                "text": text,
            }))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in items]