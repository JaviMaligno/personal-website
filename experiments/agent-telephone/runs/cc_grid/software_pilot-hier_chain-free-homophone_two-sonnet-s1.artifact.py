"""Brennan Opticians appointment reminder planner.

plan_reminders(appointments, now) -> list[dict]

Each reminder dict has exactly: appointment_id, channel, send_at, text.

Rules implemented
- Opt-out is read only from optout_sms_v2 (missing means False).
- status "cancelled" (stripped, case-insensitive) yields nothing. Appointments
  with starts_at <= now are skipped (logged by id).
- Two reminders per appointment: T-48h and T-2h (absolute timedelta on aware
  datetimes); display and quiet-hours checks use Europe/Dublin local time.
- A 48h time before now is set to now. No send_at is ever before now.
- Channel (per appointment, same for both reminders): SMS if phone is non-empty
  and optout_sms_v2 is not true; else email if email is non-empty; else the
  appointment is skipped with a warning (id only).
- Quiet hours are 21:00 <= t or t < 08:00 Dublin local. A send_at in quiet hours
  moves back to 20:00 Dublin local on the evening just before the window
  (>= 21:00: same day; < 08:00: previous day). If the result is < now:
  * 48h reminder (including one clamped to now): if now is outside quiet hours,
    send at now; otherwise defer to the next 08:00 Dublin after now, provided it
    is strictly before the 2h reminder's final send time and before the start;
    else drop it (the 2h reminder covers it).
  * 2h reminder: if now is outside quiet hours, send at now; otherwise defer to
    the next 08:00 only if before starts_at, else drop it (logged).
  A 2h reminder for an 08:00-10:00 appointment lands in quiet hours and moves
  to 20:00 the previous evening (more than 2h before); this is accepted.
- If both reminders end with identical send_at, only the 2h one is kept.
- Text: "Hi {name}, reminder: your Brennan Opticians appointment is on DD/MM/YYYY
  at HH:MM. {signature}" (same for both reminders). Signature is
  "Siobhan Ni Dhuibhir" (with diacritics), or "Grzegorz Szczepanski" (with
  diacritics) when country (stripped, upper) is "PL". SMS is at most 160
  chars: shorten the name (first name, then first name truncated with a single
  "\u2026" down to 1 char, then no name). Date, time and signature are never
  cut. Email uses the full name. Empty/None name gives "Hi, reminder: ...".
- Output is sorted by (send_at, str(appointment_id), channel).
- Privacy: logs contain only appointment ids, counts, channel, exception type
  names and a short one-way digest of the contact (contact_ref) so support can
  trace deliveries without exposing addresses, numbers or names. Malformed
  records are skipped with a warning (id and exception type only).
- now must be timezone-aware, else ValueError("now must be timezone-aware").
"""
import hashlib
import logging
from datetime import datetime, time, timedelta, timezone

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
SIG_DEFAULT = "Siobh\u00e1n N\u00ed Dhuibhir"
SIG_PL = "Grzegorz Szczepa\u0144ski"


def _aware(dt):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("naive datetime")
    return dt


def _quiet(dt):
    h = dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _move_back(dt):
    loc = dt.astimezone(DUBLIN)
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    return datetime.combine(day, time(20, 0), tzinfo=DUBLIN).astimezone(timezone.utc)


def _next_8(now):
    loc = now.astimezone(DUBLIN)
    day = loc.date() if loc.hour < 8 else loc.date() + timedelta(days=1)
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN).astimezone(timezone.utc)


def _text(name, date_s, time_s, sig, sms):
    def build(n):
        greet = f"Hi {n}," if n else "Hi,"
        return (f"{greet} reminder: your Brennan Opticians appointment is on "
                f"{date_s} at {time_s}. {sig}")

    name = (name or "").strip() if isinstance(name, str) or name is None else str(name).strip()
    full = build(name)
    if not sms or len(full) <= SMS_LIMIT or not name:
        return full if not sms or len(full) <= SMS_LIMIT else build("")
    first = name.split()[0]
    candidates = [first] + [first[:k] + "\u2026" for k in range(len(first) - 1, 0, -1)]
    for c in candidates:
        t = build(c)
        if len(t) <= SMS_LIMIT:
            return t
    return build("")


def _ref(contact):
    return hashlib.sha256(contact.encode("utf-8")).hexdigest()[:8]


def _plan_one(a, now):
    aid = a["id"]
    name, email, phone = a["customer_name"], a["email"], a["phone"]
    country, status = a["country"], a["status"]
    start = _aware(a["starts_at"])
    optout = a.get("optout_sms_v2", False)

    if status.strip().lower() == "cancelled":
        return []
    if start <= now:
        logger.info("appointment %s skipped: already started", aid)
        return []

    phone_s = phone.strip() if isinstance(phone, str) else ""
    email_s = email.strip() if isinstance(email, str) else ""
    if phone_s and not optout:
        channel, contact = "sms", phone_s
    elif email_s:
        channel, contact = "email", email_s
    else:
        logger.warning("appointment %s skipped: no usable contact", aid)
        return []

    # 2h reminder
    t2 = start - timedelta(hours=2)
    adj2 = _move_back(t2) if _quiet(t2) else t2
    final2 = adj2
    if adj2 < now:
        if not _quiet(now):
            final2 = now
        else:
            d = _next_8(now)
            if d < start:
                final2 = d
            else:
                final2 = None
                logger.info("appointment %s: 2h reminder dropped", aid)

    # 48h reminder
    t48 = max(start - timedelta(hours=48), now)
    adj48 = _move_back(t48) if _quiet(t48) else t48
    final48 = adj48
    if adj48 < now:
        if not _quiet(now):
            final48 = now
        else:
            d = _next_8(now)
            if d < start and (final2 is None or d < final2):
                final48 = d
            else:
                final48 = None
                logger.info("appointment %s: 48h reminder dropped", aid)

    if final48 is not None and final2 is not None and final48 == final2:
        logger.info("appointment %s: duplicate send_at, keeping 2h reminder only", aid)
        final48 = None

    loc = start.astimezone(DUBLIN)
    sig = SIG_PL if (country or "").strip().upper() == "PL" else SIG_DEFAULT
    text = _text(name, loc.strftime("%d/%m/%Y"), loc.strftime("%H:%M"), sig, channel == "sms")

    out = []
    for when in (final48, final2):
        if when is None:
            continue
        when = when.astimezone(DUBLIN)
        out.append({"appointment_id": aid, "channel": channel, "send_at": when, "text": text})
        logger.info("planned reminder appointment=%s channel=%s contact_ref=%s send_at=%s",
                    aid, channel, _ref(contact), when.isoformat())
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    result = []
    for a in appointments:
        try:
            result.extend(_plan_one(a, now))
        except Exception as exc:
            try:
                aid = a.get("id")
            except Exception:
                aid = None
            logger.warning("appointment %s skipped: malformed record (%s)",
                           aid, type(exc).__name__)
    result.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    logger.info("planned %d reminders for %d appointments", len(result), len(appointments))
    return result