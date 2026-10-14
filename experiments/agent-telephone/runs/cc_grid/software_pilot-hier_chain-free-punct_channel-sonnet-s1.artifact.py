"""Brennan Opticians appointment reminder planner.

Delivery notes for the architect:
- Only this module is delivered. test_reminders.py and the pytest run were not
  produced: this session has no tools and was limited to a single module.
- Deviation from the brief: the house logging rule asks for "who and how
  (channel and contact)" per planned reminder. The brief forbids logging
  phone, email or name, so the INFO line carries appointment id, channel and
  tier only, with no contact detail.
- Assumptions are marked inline. Unknown string statuses are treated as active.
  Truncation is applied to the first token of the name.
"""
import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

OPTOUT_V2_TRUE_MEANS_CAN_TEXT = True
EMAIL_FALLBACK_ENABLED = False
MAX_SMS_CHARS = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_SHIFT_TO = time(20, 0)
DISPLAY_TZ = ZoneInfo("Europe/Dublin")
PL_DISPLAY_TZ = ZoneInfo("Europe/Dublin")
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"

# Quiet hours are always evaluated in Dublin local time. 20:00 and 08:00 can
# never be nonexistent or ambiguous there (DST changes happen 01:00-02:00),
# and containment is tested by converting the instant to local time.
_QUIET_TZ = ZoneInfo("Europe/Dublin")
_UTC = timezone.utc
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_CANCELLED = {"cancelled", "canceled"}
_KNOWN_ACTIVE = {"booked", "confirmed", "scheduled"}

log = logging.getLogger("brennan.reminders")


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def is_cancelled(status):
    return isinstance(status, str) and status.strip().casefold() in _CANCELLED


def can_text(appt):
    """The single opt-out interpretation point.

    !!! OPEN CLIENT QUESTION (highest risk) !!!
    Literal client reading: optout_sms_v2 == True means the customer MAY be
    texted, which is counterintuitive for a field called "optout". Flip
    OPTOUT_V2_TRUE_MEANS_CAN_TEXT to invert behaviour everywhere. Only a real
    bool counts; missing, None or non-bool values fail closed (no text).
    The legacy opt_out field is deliberately ignored.
    """
    v = appt.get("optout_sms_v2")
    if not isinstance(v, bool):
        return False
    return v == OPTOUT_V2_TRUE_MEANS_CAN_TEXT


def choose_channel(appt):
    phone = appt.get("phone")
    if isinstance(phone, str) and phone.strip() and can_text(appt):
        return "sms"
    if EMAIL_FALLBACK_ENABLED:
        return "email"  # unreachable while the flag is False; no further behaviour defined
    return None


def compute_candidates(start_utc, now_utc):
    """Absolute-instant arithmetic (UTC), so 48h is a true duration across DST."""
    return [
        ("48h", max(start_utc - timedelta(hours=48), now_utc)),
        ("2h", max(start_utc - timedelta(hours=2), now_utc)),
    ]


def apply_quiet_hours(c, now):
    local = c.astimezone(_QUIET_TZ)
    t = local.time()
    if not (t >= QUIET_START or t < QUIET_END):
        return c
    day = local.date()
    back_day = day if t >= QUIET_START else day - timedelta(days=1)
    back = datetime.combine(back_day, QUIET_SHIFT_TO, tzinfo=_QUIET_TZ).astimezone(_UTC)
    if back >= now:
        return back
    # Shifting back would be in the past: defer forward to the next 08:00.
    fwd_day = day if t < QUIET_END else day + timedelta(days=1)
    return datetime.combine(fwd_day, QUIET_END, tzinfo=_QUIET_TZ).astimezone(_UTC)


def _signature(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return PL_SIGNATURE
    return DEFAULT_SIGNATURE


def _display_tz(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return PL_DISPLAY_TZ
    return DISPLAY_TZ


def _clean_name(name):
    if not isinstance(name, str):
        return ""
    s = "".join(" " if ch.isspace() else ch for ch in name
                if ch.isspace() or not unicodedata.category(ch).startswith("C"))
    return unicodedata.normalize("NFC", " ".join(s.split()))


def _render(name, date_s, time_s, sig):
    greeting = f"Hi {name}," if name else "Hi,"
    text = f"{greeting} reminder: your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"
    return unicodedata.normalize("NFC", text)


def fit_name(name, date_s, time_s, sig):
    """Return the longest name variant that keeps the text within the limit."""
    if len(_render(name, date_s, time_s, sig)) <= MAX_SMS_CHARS:
        return name
    first = name.split(" ")[0] if name else ""
    if first and len(_render(first, date_s, time_s, sig)) <= MAX_SMS_CHARS:
        return first
    avail = MAX_SMS_CHARS - len(_render("", date_s, time_s, sig)) - 1
    if first and avail > 1:
        cut = first[:avail - 1]
        while cut and unicodedata.combining(cut[-1]):
            cut = cut[:-1]
        if cut:
            cand = unicodedata.normalize("NFC", cut + ".")
            if len(_render(cand, date_s, time_s, sig)) <= MAX_SMS_CHARS:
                return cand
    return ""


def build_text(name, start_utc, country):
    local = start_utc.astimezone(_display_tz(country))
    date_s = f"{local.day} {_MONTHS[local.month - 1]} {local.year}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    sig = _signature(country)
    text = _render(fit_name(_clean_name(name), date_s, time_s, sig), date_s, time_s, sig)
    if len(text) <= MAX_SMS_CHARS:
        return text
    minimal = unicodedata.normalize("NFC", f"{date_s} {time_s} {sig}")
    return minimal if len(minimal) <= MAX_SMS_CHARS else None


def resolve_pair(start_utc, items):
    """items: list of (tier, send_at). Drop sends at/after start; 2h wins over 48h.

    If the 2h reminder is dropped (>= start) but the 48h survives, keep the 48h.
    """
    kept = [(tier, s) for tier, s in items if s < start_utc]
    d = dict(kept)
    if "48h" in d and "2h" in d and d["48h"] >= d["2h"]:
        kept = [(tier, s) for tier, s in kept if tier != "48h"]
    return kept


def plan_one(appt, ref, now):
    """Return a list of (tier, reminder dict) for one appointment."""
    status = appt.get("status")
    if not isinstance(status, str):
        log.warning("%s skipped: missing_status", ref)
        return []
    if is_cancelled(status):
        log.info("%s skipped: cancelled", ref)
        return []
    if status.strip().casefold() not in _KNOWN_ACTIVE:
        log.warning("%s treated active: unknown_status", ref)

    starts = appt.get("starts_at")
    if not _aware(starts):
        log.warning("%s skipped: bad_starts_at", ref)
        return []

    if not isinstance(appt.get("optout_sms_v2"), bool):
        log.warning("%s: optout_missing_or_invalid, treated as not permitted", ref)

    channel = choose_channel(appt)
    if channel is None:
        log.info("%s skipped: no_channel", ref)
        return []

    start_utc = starts.astimezone(_UTC)
    if start_utc <= now:
        log.info("%s skipped: already_started", ref)
        return []

    items = [(tier, apply_quiet_hours(c, now))
             for tier, c in compute_candidates(start_utc, now)]
    items = resolve_pair(start_utc, items)
    if not items:
        log.info("%s skipped: no_valid_slot", ref)
        return []

    text = build_text(appt.get("customer_name"), start_utc, appt.get("country"))
    if text is None:
        log.error("%s skipped: text_too_long", ref)
        return []

    out = []
    for tier, send_at in items:
        log.info("%s planned: channel=%s tier=%s send_at=%s",
                 ref, channel, tier, send_at.isoformat())
        out.append((tier, {"appointment_id": appt.get("id"), "channel": channel,
                           "send_at": send_at, "text": text}))
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(_UTC)
    entries = []
    seen = set()
    for idx, appt in enumerate(appointments):
        try:
            if not hasattr(appt, "get"):
                log.warning("index %d skipped: bad_appointment", idx)
                continue
            aid = appt.get("id")
            if isinstance(aid, bool) or not isinstance(aid, (str, int)) or aid == "":
                log.warning("index %d skipped: missing_id", idx)
                continue
            if aid in seen:
                log.warning("%s: duplicate_id", aid)
            seen.add(aid)
            for tier, rem in plan_one(appt, aid, now_utc):
                entries.append(((rem["send_at"], idx, 0 if tier == "48h" else 1), rem))
        except Exception as exc:  # per-appointment isolation; class name only
            log.warning("index %d skipped: exception %s", idx, type(exc).__name__)
    entries.sort(key=lambda e: e[0])
    return [rem for _, rem in entries]