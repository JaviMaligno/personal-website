"""Brennan Opticians appointment reminder planner.

Single public function: plan_reminders(appointments, now). It is pure and
stateless, and returns dicts with exactly appointment_id, channel, send_at
(aware, UTC) and text.

Windows note: zoneinfo needs the third-party "tzdata" package on Windows.

Delivery note: this deliverable is the module only. The pytest suite and the
separate report were not produced, because this run had no file or shell tools
and was limited to a single code-only module. The test suite still has to be
written and run. The decisions and open questions are recorded here.

Logging note: the house rule asks for one INFO line per planned reminder
naming the channel and contact. The architect's privacy rule forbids raw
phone numbers and email addresses in logs. Both are met by logging a MASKED
contact (phone: last two digits; email: first character only). Raw contact
data is never logged. Skips are logged at DEBUG with a reason code and the id
only. Malformed records are logged at WARNING with the id or index only.

Named decisions (constant or function that isolates each):
  OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT  (Q1) is_opted_out
  MISSING_OPTOUT_TREATED_AS_OPTED_OUT (Q2)
  EMAIL_FALLBACK_WHEN_NO_PHONE, choose_channel (Q3)
  PAST_SHIFT_POLICY (Q4), default DEFER_TO_OPENING (architect's
      recommendation). The product manager's proposal,
      DROP_UNLESS_ONLY_REMINDER, is implemented and selectable.
  SMS_MAX_CHARS (Q5)
  build_reminder_dict (Q6)
  CANCELLED_STATUSES (Q8)
  CLAMP_LATE_SECOND_REMINDER (Q10)
  NAIVE_STARTS_AT_RAISES (Q11)

Open questions and recommendations:
 1. Polarity of optout_sms_v2. The client's sentence says SMS is sent if it
    is true, but the name suggests true means opted out. The client must
    confirm. Safe default: true means opted out.
 2. Missing, None or non-bool optout_sms_v2 is treated as opted out
    (privacy-conservative). Records lacking the field get no reminders until
    the CRM populates it.
 3. Email only for customers with no phone, a usable email, and not opted
    out. The SMS-named flag applies to all channels.
 4. A reminder in the past after the quiet-hours shift while now is in quiet
    hours: recommend DEFER_TO_OPENING (next 08:00). It never sends in the
    past or in quiet hours and loses no reminder. If the shifted time is past
    but now is outside quiet hours, the reminder is sent at now.
 5. Whether 160 means characters or SMS segments. Accented letters force
    UCS-2 (70 characters per single segment, 67 per concatenated segment),
    so 160 characters may be billed as 3 to 4 segments. The client must
    confirm. No segment logic is implemented.
 6. No recipient in the output. Downstream should look up the contact by
    appointment_id.
 7. No idempotency. A reminder pulled to now is re-emitted on every call.
    The caller should keep a sent-ledger keyed by (appointment_id, reminder
    number), and a reminder number field may be added later.
 8. Statuses other than cancelled (no-show, completed and so on) are all
    treated as active. Ask the client for the status vocabulary.
 9. The 2h reminder for an 08:00 to 10:00 appointment lands at 20:00 the
    previous evening, up to 14 hours early. Confirm this is intended.
10. A late kind 2 reminder is clamped to now (CLAMP_LATE_SECOND_REMINDER).
11. A naive starts_at aborts the whole batch, while other malformed records
    are skipped. Switch with NAIVE_STARTS_AT_RAISES.
12. send_at is returned in UTC. Confirm with the dashboard owner.
13. 48h and 2h are absolute elapsed hours, so across a DST change the local
    wall-clock time differs by an hour.
14. The 20:00 shift and the 08:00 deferral can put two reminders for one
    appointment close together. Only exact equality is collapsed.
15. Duplicate appointment ids are not deduplicated.
16. The "canceled" spelling is also treated as cancelled.
17. The text avoids relative phrases such as "in 2 hours" on purpose.
"""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Optional
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

logger = logging.getLogger("brennan_opticians.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc


class PastShiftPolicy(Enum):
    """What to do when the shifted time is past and now is in quiet hours."""

    DEFER_TO_OPENING = "defer_to_opening"
    DROP = "drop"
    DROP_UNLESS_ONLY_REMINDER = "drop_unless_only_reminder"


CANCELLED_STATUSES = {"cancelled", "canceled"}
OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT = True
MISSING_OPTOUT_TREATED_AS_OPTED_OUT = True
EMAIL_FALLBACK_WHEN_NO_PHONE = True
PAST_SHIFT_POLICY = PastShiftPolicy.DEFER_TO_OPENING
CLAMP_LATE_SECOND_REMINDER = True
NAIVE_STARTS_AT_RAISES = True
SMS_MAX_CHARS = 160

# Absolute elapsed offsets (timedelta on UTC instants, not wall-clock
# arithmetic), so across a DST change the local hour of the 48h point can
# differ by one hour.
OFFSETS = {1: timedelta(hours=48), 2: timedelta(hours=2)}

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = unicodedata.normalize("NFC", "Siobhán Ní Dhuibhir")
_SIG_PL = unicodedata.normalize("NFC", "Grzegorz Szczepański")

_FINAL, _DEFERRED, _DROPPED = "final", "deferred", "dropped"


class _NaiveStartsAt(ValueError):
    """Raised for a naive starts_at; must propagate out of the batch."""


@dataclass(frozen=True)
class _Resolution:
    state: str
    when: Optional[datetime] = None


# --------------------------------------------------------------- time helpers

def to_dublin(dt: datetime) -> datetime:
    """Convert an aware datetime to Europe/Dublin."""
    return dt.astimezone(DUBLIN)


def in_quiet_hours(dt: datetime) -> bool:
    """True from 21:00 up to but excluding 08:00 Dublin local time."""
    hour = to_dublin(dt).hour
    return hour >= 21 or hour < 8


def _local_to_utc(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=DUBLIN).astimezone(UTC)


def shift_back_to_2000(dt: datetime) -> datetime:
    """20:00 Dublin on the previous (00:00-07:59) or same (21:00+) local date."""
    local = to_dublin(dt)
    day = local.date() - timedelta(days=1) if local.hour < 8 else local.date()
    return _local_to_utc(day, time(20, 0))


def next_0800_at_or_after(dt: datetime) -> datetime:
    """Earliest 08:00 Dublin local instant that is >= dt (UTC)."""
    day = to_dublin(dt).date()
    candidate = _local_to_utc(day, time(8, 0))
    if candidate < dt:
        candidate = _local_to_utc(day + timedelta(days=1), time(8, 0))
    return candidate


# ------------------------------------------------------------ channel decision

def is_opted_out(appt: Mapping[str, Any]) -> bool:
    """Read only optout_sms_v2; non-bool values follow the missing policy."""
    value = appt.get("optout_sms_v2")
    if not isinstance(value, bool):
        return MISSING_OPTOUT_TREATED_AS_OPTED_OUT
    return value if OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT else (not value)


def has_usable_phone(appt: Mapping[str, Any]) -> bool:
    phone = appt.get("phone")
    return (isinstance(phone, str) and bool(phone.strip())
            and any(ch.isdigit() for ch in phone))


def has_usable_email(appt: Mapping[str, Any]) -> bool:
    email = appt.get("email")
    if not isinstance(email, str):
        return False
    email = email.strip()
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and bool(domain)


def choose_channel(appt: Mapping[str, Any]) -> Optional[str]:
    """Return "sms", "email" or None. Opted-out customers get nothing."""
    if is_opted_out(appt):
        return None
    if has_usable_phone(appt):
        return "sms"
    if EMAIL_FALLBACK_WHEN_NO_PHONE and has_usable_email(appt):
        return "email"
    return None


def _mask_contact(channel: str, appt: Mapping[str, Any]) -> str:
    """Masked contact for the trace log; never the raw value."""
    if channel == "sms":
        digits = [c for c in str(appt.get("phone")) if c.isdigit()]
        return "***" + "".join(digits[-2:])
    return str(appt.get("email")).strip()[:1] + "***@***"


# ------------------------------------------------------------------------ text

def _format_when(starts_utc: datetime) -> str:
    d = to_dublin(starts_utc)
    return (f"{_WEEKDAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]} "
            f"{d.year} at {d.hour:02d}:{d.minute:02d}")


def _signature(country: Any) -> str:
    return _SIG_PL if str(country).strip().casefold() == "pl" else _SIG_DEFAULT


def _clean_name(name: Any) -> Optional[str]:
    if not isinstance(name, str):
        return None
    name = unicodedata.normalize("NFC", name)
    name = "".join(ch for ch in name
                   if ch.isspace() or unicodedata.category(ch) != "Cc")
    name = " ".join(name.split())
    return name or None


def _compose(greeting: str, number: int, when: str, sig: str) -> str:
    if number == 1:
        body = f"this is a reminder of your appointment at Brennan Opticians on {when}. {sig}"
    else:
        body = f"a further reminder: your appointment at Brennan Opticians is on {when}. {sig}"
    if greeting:
        return greeting + body
    return body[0].upper() + body[1:]


def build_text(appt: Mapping[str, Any], number: int, channel: str,
               starts_utc: datetime) -> str:
    """Build the message; SMS picks the fullest greeting that fits."""
    when = _format_when(starts_utc)
    sig = _signature(appt.get("country"))
    name = _clean_name(appt.get("customer_name"))
    if name is None:
        return _compose("", number, when, sig)
    if channel == "email":
        return _compose(f"Hello {name}, ", number, when, sig)
    first = name.split()[0]
    for label in (name, first, first[0] + "."):
        text = _compose(f"Hello {label}, ", number, when, sig)
        if len(text) <= SMS_MAX_CHARS:
            return text
    return _compose("", number, when, sig)


def build_reminder_dict(appointment_id: Any, channel: str,
                        send_at: datetime, text: str) -> dict:
    """The only place the output shape is defined (no recipient, see Q6)."""
    return {"appointment_id": appointment_id, "channel": channel,
            "send_at": send_at.astimezone(UTC), "text": text}


# -------------------------------------------------------------------- planning

def _resolve(starts_utc: datetime, number: int, now: datetime) -> _Resolution:
    """Resolve one reminder to a final time, a deferred marker, or dropped."""
    nominal = starts_utc - OFFSETS[number]
    if nominal < now:
        if number == 2 and not CLAMP_LATE_SECOND_REMINDER:
            return _Resolution(_DROPPED)
        nominal = now
    shifted = shift_back_to_2000(nominal) if in_quiet_hours(nominal) else nominal
    if shifted >= now:
        return _Resolution(_FINAL, shifted)
    if not in_quiet_hours(now):
        return _Resolution(_FINAL, now)
    if PAST_SHIFT_POLICY is PastShiftPolicy.DEFER_TO_OPENING:
        return _Resolution(_FINAL, next_0800_at_or_after(now))
    if PAST_SHIFT_POLICY is PastShiftPolicy.DROP:
        return _Resolution(_DROPPED)
    return _Resolution(_DEFERRED, next_0800_at_or_after(now))


def _ident(appt: Any, index: int) -> str:
    try:
        return str(appt["id"])
    except Exception:
        return f"index:{index}"


def _plan_one(appt: Mapping[str, Any], now: datetime, index: int) -> list:
    """Plan reminders for one appointment: (send_at, str(id), number, dict)."""
    ident = appt["id"]
    starts = appt["starts_at"]
    if not isinstance(starts, datetime):
        raise TypeError("starts_at")
    if starts.tzinfo is None or starts.utcoffset() is None:
        if NAIVE_STARTS_AT_RAISES:
            raise _NaiveStartsAt(
                f"starts_at must be timezone-aware (appointment index {index})")
        raise TypeError("naive starts_at")
    status = str(appt["status"]).strip().casefold()
    if status in CANCELLED_STATUSES:
        logger.debug("reminder skipped appointment=%s reason=cancelled", ident)
        return []
    starts_utc = starts.astimezone(UTC)
    if starts_utc <= now:
        logger.debug("reminder skipped appointment=%s reason=started", ident)
        return []
    channel = choose_channel(appt)
    if channel is None:
        logger.debug("reminder skipped appointment=%s reason=no_channel", ident)
        return []

    resolved = {n: _resolve(starts_utc, n, now) for n in (1, 2)}
    times = {n: r.when for n, r in resolved.items()
             if r.state == _FINAL and r.when < starts_utc}
    if not times and PAST_SHIFT_POLICY is PastShiftPolicy.DROP_UNLESS_ONLY_REMINDER:
        for n in (2, 1):
            r = resolved[n]
            if r.state == _DEFERRED and r.when < starts_utc:
                times[n] = r.when
                break
    if not times:
        logger.debug("reminder skipped appointment=%s reason=dropped_past_quiet", ident)
    for n in list(times):
        if times[n] < now:
            logger.debug("reminder dropped appointment=%s reason=before_now", ident)
            del times[n]
    if 1 in times and 2 in times and times[1] == times[2]:
        del times[1]

    contact = _mask_contact(channel, appt)
    out = []
    for n, when in times.items():
        text = build_text(appt, n, channel, starts_utc)
        logger.info("reminder planned appointment=%s number=%d channel=%s "
                    "contact=%s send_at=%s", ident, n, channel, contact,
                    when.astimezone(UTC).isoformat())
        out.append((when.astimezone(UTC), str(ident), n,
                    build_reminder_dict(ident, channel, when, text)))
    return out


def plan_reminders(appointments: Iterable[Mapping[str, Any]],
                   now: datetime) -> list[dict]:
    """Plan SMS/email reminders (48h and 2h before) for the appointments."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    planned: list = []
    for index, appt in enumerate(appointments):
        try:
            planned.extend(_plan_one(appt, now_utc, index))
        except _NaiveStartsAt:
            raise
        except Exception:
            logger.warning("reminder skipped appointment=%s reason=malformed",
                           _ident(appt, index))
    planned.sort(key=lambda p: p[:3])
    return [p[3] for p in planned]