"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now) -> list[dict]

Each returned dict has exactly the keys appointment_id, channel ("sms" or
"email"), send_at and text. send_at is an aware datetime in Europe/Dublin.
The result is sorted by (send_at as UTC, str(appointment_id), rank), where
rank 0 is the 2h reminder and 1 is the 48h one. Inputs are never mutated.
A naive `now` raises ValueError.

Design decisions
- DUBLIN = ZoneInfo("Europe/Dublin"). The 48h and 2h points are computed
  with absolute timedelta arithmetic on UTC-aware values. Dublin local time
  is used only for quiet-hours checks, building 20:00 / 08:00, and for the
  date (DD/MM/YYYY) and time (HH:MM) in the text, taken from starts_at.
- Skips, logged with the id and reason only: status "cancelled"
  (case-insensitive, stripped), starts_at <= now, starts_at missing or
  naive, and no usable contact. Each appointment is wrapped in try/except.
  On error only the exception type name and the id are logged, with no
  exc_info.
- Quiet hours: Dublin hour >= 21 or hour < 8. Resolution of one reminder:
  1. s = max(target, now).
  2. If s is quiet, back = the preceding 20:00 Dublin. If back >= now,
     s = back. Otherwise defer FORWARD to the next 08:00 Dublin.
  3. If s >= starts_at, the reminder is dropped.
- Two reminders: the 2h one has priority. The 48h one is dropped if its
  send_at >= the 2h send_at, or if the appointment starts within 2h of
  now. If the 2h one resolves to nothing, the 48h one is evaluated
  independently. Two reminders never share a send_at.
- Channel (one per appointment): SMS if the phone is a string with at least
  one digit and optout_sms_v2 is not the boolean True. Only optout_sms_v2
  is read; the legacy opt_out is ignored. The string "true" is NOT honoured
  as an opt-out; only the boolean True is. Otherwise email if the address
  has exactly one "@" with non-empty parts after strip. Otherwise skip.
  The address is used only to choose the channel and is never returned.
- Text: "Brennan Opticians: {name}, your appointment is on {DD/MM/YYYY} at
  {HH:MM}. {signature}". The signature is "Siobhán Ní Dhuibhir", or
  "Grzegorz Szczepański" when country.strip().upper() == "PL". The text is
  NFC-normalised and measured in code points. The SMS limit is 160. Name
  ladder: full name, first name + last initial, first name, initials,
  then no name. Email uses the full name with no length limit. Whitespace
  in names is collapsed, and a blank or missing name gives the no-name form.
- Logging: logger "brennan.reminders" logs ids, counts, reasons, channel
  and send time. The house rule asks for "channel and contact" on each
  planned-reminder INFO line. The contact detail (email, phone) is not
  logged, because the Data Protection Commission audit flagged logged
  email addresses. The appointment id identifies the recipient, so support
  can still trace deliveries. Names are never logged, and there is no
  logger.exception and no exc_info.
"""

import logging
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
logger = logging.getLogger("brennan.reminders")

SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"


def _safe_id(appt):
    try:
        return appt.get("id")
    except Exception:
        return None


def _is_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _at(d, hour):
    return datetime.combine(d, time(hour, 0), tzinfo=DUBLIN).astimezone(UTC)


def _resolve(target, now, starts):
    """Return the resolved send time (UTC) or None if the reminder is dropped."""
    s = max(target, now)
    local = s.astimezone(DUBLIN)
    if _is_quiet(local):
        d = local.date()
        back_day = d if local.hour >= 21 else d - timedelta(days=1)
        back = _at(back_day, 20)
        if back >= now:
            s = back
        else:
            fwd_day = d if local.hour < 8 else d + timedelta(days=1)
            s = _at(fwd_day, 8)
    if s >= starts:
        return None
    return s


def _channel(appt):
    phone = appt.get("phone")
    if (
        isinstance(phone, str)
        and any(c.isdigit() for c in phone)
        and appt.get("optout_sms_v2") is not True
    ):
        return "sms"
    email = appt.get("email")
    if isinstance(email, str):
        e = email.strip()
        if e.count("@") == 1:
            local, domain = e.split("@")
            if local and domain:
                return "email"
    return None


def _name_ladder(name):
    parts = " ".join(name.split()).split() if isinstance(name, str) else []
    if not parts:
        return [None]
    full = " ".join(parts)
    cands = [full]
    if len(parts) >= 2:
        cands.append(f"{parts[0]} {parts[-1][0]}.")
    cands.append(parts[0])
    cands.append("".join(p[0].upper() + "." for p in parts))
    cands.append(None)
    return cands


def _render(name, date_s, time_s, sig):
    if name:
        t = f"Brennan Opticians: {name}, your appointment is on {date_s} at {time_s}. {sig}"
    else:
        t = f"Brennan Opticians: your appointment is on {date_s} at {time_s}. {sig}"
    return unicodedata.normalize("NFC", t)


def _build_text(appt, channel, starts):
    local = starts.astimezone(DUBLIN)
    date_s = local.strftime("%d/%m/%Y")
    time_s = local.strftime("%H:%M")
    country = appt.get("country")
    sig = SIG_PL if isinstance(country, str) and country.strip().upper() == "PL" else SIG_DEFAULT
    ladder = _name_ladder(appt.get("customer_name"))
    if channel == "email":
        return _render(ladder[0], date_s, time_s, sig)
    for cand in ladder:
        text = _render(cand, date_s, time_s, sig)
        if len(text) <= SMS_LIMIT:
            break
    assert len(text) <= SMS_LIMIT
    return text


def _plan_one(appt, now):
    aid = appt.get("id")
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        logger.info("skip appointment %s: cancelled", aid)
        return []
    raw = appt.get("starts_at")
    if raw is None:
        logger.info("skip appointment %s: starts_at missing", aid)
        return []
    if isinstance(raw, datetime) and raw.utcoffset() is None:
        logger.info("skip appointment %s: starts_at naive", aid)
        return []
    starts = raw.astimezone(UTC)  # raises for non-datetime types (caught by caller)
    if starts <= now:
        logger.info("skip appointment %s: already started", aid)
        return []
    channel = _channel(appt)
    if channel is None:
        logger.info("skip appointment %s: no usable contact", aid)
        return []

    r2 = _resolve(starts - timedelta(hours=2), now, starts)
    r48 = None
    if starts - now > timedelta(hours=2):
        r48 = _resolve(starts - timedelta(hours=48), now, starts)
        if r48 is not None and r2 is not None and r48 >= r2:
            r48 = None
    if r48 is None and r2 is None:
        logger.info("skip appointment %s: no reminder fits before start", aid)
        return []

    text = _build_text(appt, channel, starts)
    out = []
    for rank, when in ((0, r2), (1, r48)):
        if when is None:
            continue
        logger.info(
            "planned reminder for appointment %s via %s at %s",
            aid, channel, when.astimezone(DUBLIN).isoformat(),
        )
        out.append((when, str(aid), rank, {
            "appointment_id": aid,
            "channel": channel,
            "send_at": when.astimezone(DUBLIN),
            "text": text,
        }))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        try:
            planned.extend(_plan_one(appt, now_utc))
        except Exception as exc:
            logger.error(
                "error planning appointment %s: %s", _safe_id(appt), type(exc).__name__
            )
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    logger.info("planned %d reminders from %d appointments", len(planned), len(appointments))
    return [p[3] for p in planned]