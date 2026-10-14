"""Reminder planner for Brennan Opticians.

Public entry point: plan_reminders(appointments, now).
Standard library only. Europe/Dublin needs zoneinfo data; on minimal systems
install the tzdata package (pip install tzdata).

Logging note: the house rule asks for one INFO line per planned reminder naming
the recipient and channel. The client design forbids email addresses, phones
and names in logs, so each line carries the appointment id (the trace key),
the channel and the contact field used ("email" or "phone"), never the value.

The pytest file tests/test_reminders.py was requested but is not part of this
single-module reply, and the tests were not run (no execution tools available).
"""
import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Dublin")
SMS_MAX_CHARS = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
MOVE_BACK = time(20, 0)
LEAD_1 = timedelta(hours=48)
LEAD_2 = timedelta(hours=2)
SIGNATURE_DEFAULT = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CANCELLED = {"cancelled", "canceled"}
KNOWN_ACTIVE = {"active", "confirmed", "booked", "scheduled"}
_TRUE = {"true", "1", "yes"}
_FALSE = {"false", "0", "no", ""}

log = logging.getLogger(__name__)


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _is_quiet(dt):
    t = dt.astimezone(TZ).time()
    return t >= QUIET_START or t < QUIET_END


def _move_back(target):
    local = target.astimezone(TZ)
    d = local.date()
    if local.time() < QUIET_END:
        d -= timedelta(days=1)
    return datetime.combine(d, MOVE_BACK, tzinfo=TZ)


def _next_morning(target):
    local = target.astimezone(TZ)
    d = local.date()
    if local.time() >= QUIET_START:
        d += timedelta(days=1)
    return datetime.combine(d, QUIET_END, tzinfo=TZ)


def _resolve(target, now, deadline):
    if not _is_quiet(target):
        return target
    back = _move_back(target)
    if back >= now:
        return back
    if not _is_quiet(now):
        return now
    fwd = _next_morning(target)
    return fwd if fwd < deadline else None


def _opted_out(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int)):
        s = str(value).strip().lower()
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
    return True  # fail safe


def _usable_phone(v):
    return isinstance(v, str) and bool(v.strip()) and any(c.isdigit() for c in v)


def _usable_email(v):
    return isinstance(v, str) and bool(v.strip()) and "@" in v


def _clean_name(v):
    if not isinstance(v, str):
        return ""
    v = unicodedata.normalize("NFC", v)
    v = "".join(" " if c.isspace() else c for c in v
                if c.isspace() or unicodedata.category(c)[0] != "C")
    return " ".join(v.split())


def _compose(name, date_s, time_s, sig):
    greet = "Hi {},".format(name) if name else "Hi,"
    text = "{} reminder: your Brennan Opticians appointment is on {} at {}.\n{}".format(
        greet, date_s, time_s, sig)
    return unicodedata.normalize("NFC", text)


def _build_text(name, starts_at, sig, channel):
    local = starts_at.astimezone(TZ)
    date_s = "{:02d} {} {}".format(local.day, MONTHS[local.month - 1], local.year)
    time_s = "{:02d}:{:02d}".format(local.hour, local.minute)
    if channel == "email":
        return _compose(name, date_s, time_s, sig)
    parts = name.split()
    ladder = [name]
    if len(parts) > 1:
        ladder.append("{} {}.".format(parts[0], parts[-1][0]))
    if parts:
        ladder.append(parts[0])
        ladder.append(parts[0][0])
    ladder.append("")
    for cand in ladder:
        text = _compose(cand, date_s, time_s, sig)
        if len(text) <= SMS_MAX_CHARS:
            return text
    raise ValueError("SMS text exceeds the maximum length")


def _plan_one(a, now, idx):
    """Return list of (seq, channel, contact_field, send_at, text) or []."""
    aid = a.get("id")
    status = a.get("status")
    if isinstance(status, str):
        s = status.strip().casefold()
        if s in CANCELLED:
            return []
        if s and s not in KNOWN_ACTIVE:
            log.warning("appointment id=%s reason=unknown_status", aid)
    elif status is not None:
        log.warning("appointment id=%s reason=unknown_status", aid)

    starts_at = a["starts_at"]
    if starts_at <= now:
        return []
    start = starts_at.astimezone(timezone.utc)
    t1 = start - LEAD_1
    t2 = start - LEAD_2

    r1 = _resolve(max(t1, now), now, t2)
    r2 = None if t2 < now else _resolve(t2, now, start)
    if r1 is not None and r2 is not None and r1 >= r2:
        r1 = None
    if r1 is None and r2 is None:
        return []

    if _usable_phone(a.get("phone")) and not _opted_out(a.get("optout_sms_v2")):
        channel, field = "sms", "phone"
    elif _usable_email(a.get("email")):
        channel, field = "email", "email"
    else:
        log.debug("appointment id=%s reason=no_channel", aid)
        return []

    country = a.get("country")
    sig = SIGNATURE_PL if isinstance(country, str) and country.strip().upper() == "PL" \
        else SIGNATURE_DEFAULT
    text = _build_text(_clean_name(a.get("customer_name")), starts_at, sig, channel)
    return [(seq, channel, field, r.astimezone(TZ), text)
            for seq, r in ((0, r1), (1, r2)) if r is not None]


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    if not appointments:
        return []
    out = []
    skipped = 0
    for idx, a in enumerate(appointments):
        if not isinstance(a, dict):
            log.warning("item=%d reason=not_a_dict", idx)
            skipped += 1
            continue
        if a.get("id") is None:
            log.warning("item=%d reason=missing_id", idx)
            skipped += 1
            continue
        s = a.get("starts_at")
        if s is None or not isinstance(s, datetime):
            log.warning("appointment id=%s reason=invalid_starts_at", a.get("id"))
            skipped += 1
            continue
        if not _aware(s):
            log.warning("appointment id=%s reason=naive_starts_at", a.get("id"))
            skipped += 1
            continue
        for seq, channel, field, send_at, text in _plan_one(a, now, idx):
            out.append(((send_at.astimezone(timezone.utc), str(a["id"]), seq),
                        {"appointment_id": a["id"], "channel": channel,
                         "send_at": send_at, "text": text}))
    out.sort(key=lambda p: p[0])
    result = [d for _, d in out]
    for d in result:
        log.info("reminder planned appointment_id=%s channel=%s contact_field=%s send_at=%s",
                 d["appointment_id"], d["channel"],
                 "phone" if d["channel"] == "sms" else "email",
                 d["send_at"].isoformat())
    log.info("plan_reminders done appointments=%d skipped=%d reminders=%d",
             len(appointments), skipped, len(result))
    return result