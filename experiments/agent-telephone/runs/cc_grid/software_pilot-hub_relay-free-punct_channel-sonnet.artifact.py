"""Brennan Opticians appointment reminders.

Public entry point: plan_reminders(appointments, now).

Assumptions that need client confirmation:
  * optout_sms_v2 polarity: the brief ("text them if optout_sms_v2 is true")
    contradicts the field name. This module treats True as opted out, so SMS
    is allowed only when the flag is explicitly False (missing or None falls
    back to email). The rule lives in _sms_permitted() and can be flipped there.
  * Email is used as a fallback channel when SMS is not possible.
  * Europe/Dublin is used for all customers, including Polish ones.
  * SMS text with accented characters is UCS-2, so a 160-character text may
    be billed as several segments.
  * The function is stateless: the caller must avoid re-sending reminders
    on repeated runs.

Logging note: the house rule asks for one INFO line per planned reminder saying
who it goes to and how. Privacy rules forbid logging email addresses, so the
line records the appointment id, channel and contact kind ("email on file" or
"phone on file") but never the address, phone number or name.

Not done: test_reminders.py was not written and no tests were run, because
this task had no file or execution tools.
"""
import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
_UTC = timezone.utc
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = "Siobh\u00e1n N\u00ed Dhuibhir"
_SIG_PL = "Grzegorz Szczepa\u0144ski"
_SMS_MAX = 160


def _sms_permitted(flag) -> bool:
    # ASSUMPTION (needs client confirmation): optout_sms_v2 True means the
    # customer opted OUT. SMS is allowed only when the flag is explicitly False;
    # missing/None counts as not permitted. Flip the polarity here only.
    return flag is False


def _aware(dt) -> bool:
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _clean(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _in_quiet(local: datetime) -> bool:
    return local.hour >= 21 or local.hour < 8


def _at_local(day, hour: int) -> datetime:
    return datetime.combine(day, time(hour, 0), tzinfo=DUBLIN).astimezone(_UTC)


def _schedule(nominal: datetime, now: datetime, starts: datetime):
    """Return the send instant (UTC) or None if the reminder is dropped."""
    t = max(nominal, now)
    local = t.astimezone(DUBLIN)
    if _in_quiet(local):
        day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
        t = _at_local(day, 20)
    if t < now:
        now_local = now.astimezone(DUBLIN)
        if not _in_quiet(now_local):
            t = now
        else:
            day = now_local.date()
            if now_local.hour >= 21:
                day += timedelta(days=1)
            t = _at_local(day, 8)
    if t >= starts:
        return None
    return t


def _greeting_candidates(name_raw):
    tokens = name_raw.split() if isinstance(name_raw, str) else []
    if not tokens:
        return []
    first, last = tokens[0], tokens[-1]
    out = [" ".join(tokens)]
    if len(tokens) > 1:
        out.append(f"{first} {last[0]}.")
    out.append(first)
    out.append(f"{first[0]}.")
    return out


def _build_text(appt, starts_local: datetime, channel: str) -> str:
    date = f"{starts_local.day} {_MONTHS[starts_local.month - 1]} {starts_local.year}"
    hhmm = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    country = _clean(appt.get("country")).upper()
    sig = _SIG_PL if country == "PL" else _SIG_DEFAULT

    def render(greeting: str) -> str:
        return unicodedata.normalize(
            "NFC",
            f"{greeting}, reminder of your Brennan Opticians appointment on {date} at {hhmm}. {sig}")

    cands = _greeting_candidates(unicodedata.normalize("NFC", appt.get("customer_name") or "")
                                 if isinstance(appt.get("customer_name"), str) else None)
    if channel == "email":
        return render(f"Hi {cands[0]}" if cands else "Hi")
    for c in cands:
        text = render(f"Hi {c}")
        if len(text) <= _SMS_MAX:
            return text
    return render("Hi")


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(_UTC)
    planned = []  # (send_utc, index, order, reminder)

    for idx, appt in enumerate(appointments or []):
        appt_id = appt.get("id") if isinstance(appt, dict) else None
        starts = appt.get("starts_at") if isinstance(appt, dict) else None
        if appt_id is None or not _aware(starts):
            logger.warning("Skipping malformed appointment id=%s",
                           appt_id if appt_id is not None else "<missing>")
            continue

        status = _clean(appt.get("status")).lower()
        if status in ("cancelled", "canceled"):
            continue
        starts_utc = starts.astimezone(_UTC)
        if starts_utc <= now_utc:
            continue

        phone = _clean(appt.get("phone"))
        email = _clean(appt.get("email"))
        if phone and _sms_permitted(appt.get("optout_sms_v2")):
            channel, contact = "sms", "phone on file"
        elif email:
            channel, contact = "email", "email on file"
        else:
            continue

        times = [
            _schedule(starts_utc - timedelta(hours=48), now_utc, starts_utc),
            _schedule(starts_utc - timedelta(hours=2), now_utc, starts_utc),
        ]
        t48, t2 = times
        if t48 is not None and t2 is not None and t48 >= t2:
            t48 = None
        text = _build_text(appt, starts_utc.astimezone(DUBLIN), channel)

        for order, (kind, t) in enumerate((("48h", t48), ("2h", t2))):
            if t is None:
                continue
            send_at = t.astimezone(DUBLIN)
            logger.info("Planned reminder appointment_id=%s kind=%s channel=%s contact=%s send_at=%s",
                        appt_id, kind, channel, contact, send_at.isoformat())
            planned.append((t, idx, order, {
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            }))

    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    return [p[3] for p in planned]