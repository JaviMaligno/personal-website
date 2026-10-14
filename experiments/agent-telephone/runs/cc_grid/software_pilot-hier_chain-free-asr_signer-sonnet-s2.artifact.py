"""plan_reminders: appointment reminder planning for Brennan Opticians.

Status of this delivery: only this module is delivered. test_plan_reminders.py was
not written and pytest was not run (no execution tools were available).

Decisions
- Pure function: `now` is a parameter, nothing reads the clock. Naive `now` raises ValueError.
- Arithmetic is done on absolute UTC time (starts_at - 48h / - 2h). Europe/Dublin is used
  only for quiet-hours checks, text formatting and the output zone. Comparisons are done in
  UTC to avoid same-tzinfo wall-clock comparison pitfalls around DST.
- Opt-out uses only `optout_sms_v2`; the legacy `opt_out` is never read. Missing/None is
  treated as not opted out (warning with id only).
- Channel: sms if phone is a non-blank string and not opted out; else email if the stripped
  email contains "@"; else skip. One channel per appointment, both reminders.
- Cancelled ("cancelled"/"canceled", case/whitespace-insensitive) yields nothing. Unknown
  string statuses are processed as active with a warning.
- Timing: R1 = start - 48h (clamped to now if past), R2 = start - 2h (dropped if past
  and not quiet-shifted). starts_at <= now yields nothing. If R1 and R2 land on the same
  instant, only R2 is kept.
- Quiet hours [21:00, 08:00) Dublin local; shifted back to the previous 20:00 local. If that
  is before now: when now is not quiet, send at now (2h reminder requires at least MIN_LEAD_2H
  before the start, 48h reminder requires now < start); when now is quiet, send at the next
  08:00 local if strictly before start - MIN_LEAD_2H (2h) or before start (48h); else drop.
- MIN_LEAD_2H is applied to the 2h reminder only; the 48h reminder uses the start itself as
  its limit, as the design states.
- SMS is at most 160 chars. Only the name is shortened (with a trailing "."), then the
  greeting name is dropped, then a minimal fallback template is used. Email is never truncated.
  Known limitation: non-GSM-7 characters (e.g. the "n with acute" in the PL signature) can
  force UCS-2 encoding and split the SMS into more segments; len() is not segment-aware.
- Ordering: send_at ascending, then input order, then 48h before 2h.
- Logging (logger "brennan.reminders"): ids, counts, reasons and exception class names only.
  No emails, phones, names or dict reprs are logged.

Deviation from the house rule: the house rule asks for one INFO line per planned reminder
naming the contact, but design rule 11 forbids logging emails/phone numbers. This module logs
the appointment id, channel and send time per reminder, and omits the contact value itself so
that support can trace by id. The conflict should be confirmed with the client.
"""
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
MIN_LEAD_2H = timedelta(minutes=30)
SMS_LIMIT = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)

TEMPLATE = ("Hi {name}, reminder: your Brennan Opticians appointment is on "
            "{date} at {time}. {signature}")
TEMPLATE_NO_NAME = ("Hi, reminder: your Brennan Opticians appointment is on "
                    "{date} at {time}. {signature}")
FALLBACK_TEMPLATE = "Appointment {date} {time}. {signature}"

SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
ACTIVE = {"booked", "confirmed", "scheduled"}
CANCELLED = {"cancelled", "canceled"}


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _prev_20(local):
    d = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    # 20:00 is never ambiguous or nonexistent in Dublin (DST changes happen at 01:00/02:00 local).
    return datetime.combine(d, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)


def _next_08(local):
    d = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    # 08:00 is never ambiguous or nonexistent in Dublin either.
    return datetime.combine(d, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)


def adjust(send_time, now, starts_at, kind):
    """Return a UTC datetime satisfying quiet hours and never in the past, or None to drop.

    kind is "48h" or "2h".
    """
    send_time = send_time.astimezone(UTC)
    now = now.astimezone(UTC)
    starts_at = starts_at.astimezone(UTC)
    quiet = _quiet(send_time.astimezone(DUBLIN))
    t = _prev_20(send_time.astimezone(DUBLIN)) if quiet else send_time
    if t >= now:
        return t
    if not quiet:
        return None  # plain past reminder (the 2h one) is dropped, never moved forward
    now_local = now.astimezone(DUBLIN)
    if kind == "2h":
        latest, strict_now = starts_at - MIN_LEAD_2H, False
    else:
        latest, strict_now = starts_at, True
    if not _quiet(now_local):
        ok = now < latest if strict_now else now <= latest
        return now if ok else None
    n8 = _next_08(now_local)
    return n8 if n8 < latest else None


def _clean_name(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Customer"


def _build_text(channel, name, country, starts_local, aid):
    sig = SIG_PL if isinstance(country, str) and country.strip().casefold() == "pl" else SIG_DEFAULT
    date = f"{starts_local.day:02d} {MONTHS[starts_local.month - 1]} {starts_local.year}"
    hhmm = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    kw = dict(date=date, time=hhmm, signature=sig)
    text = TEMPLATE.format(name=name, **kw)
    if channel == "email" or len(text) <= SMS_LIMIT:
        return text
    avail = SMS_LIMIT - (len(TEMPLATE.format(name="x", **kw)) - 1)
    if avail >= 2:
        short = name[:avail - 1].rstrip() + "."
        text = TEMPLATE.format(name=short, **kw)
    else:
        text = TEMPLATE_NO_NAME.format(**kw)
    if len(text) > SMS_LIMIT:
        log.warning("appointment %s: sms text over limit, using fallback", aid)
        text = FALLBACK_TEMPLATE.format(**kw)
    return text


def _plan_one(a, idx, now, aid):
    """Return a list of (send_utc, idx, order, dict) for one appointment."""
    status = a.get("status")
    if isinstance(status, str):
        s = status.strip().casefold()
        if s in CANCELLED:
            return []
        if s not in ACTIVE:
            log.warning("appointment %s: unknown status %r, treating as active", aid, s[:40])
    elif status is not None:
        log.warning("appointment %s: non-string status of type %s, treating as active",
                    aid, type(status).__name__)

    starts = a.get("starts_at")
    if not _aware(starts):
        log.warning("appointment %s: missing or naive starts_at, skipped", aid)
        return []
    starts = starts.astimezone(UTC)
    if starts <= now:
        return []

    optout = a.get("optout_sms_v2")
    if optout is None:
        log.warning("appointment %s: optout_sms_v2 missing, treating as not opted out", aid)
    phone, email = a.get("phone"), a.get("email")
    if isinstance(phone, str) and phone.strip() and not optout:
        channel = "sms"
    elif isinstance(email, str) and email.strip() and "@" in email.strip():
        channel = "email"
    else:
        log.warning("appointment %s: no usable contact channel, skipped", aid)
        return []

    r1 = max(starts - timedelta(hours=48), now)
    r2 = starts - timedelta(hours=2)
    t1 = adjust(r1, now, starts, "48h")
    t2 = adjust(r2, now, starts, "2h")
    if t1 is not None and t2 is not None and t1 == t2:
        t1 = None  # keep only the 2h reminder

    starts_local = starts.astimezone(DUBLIN)
    text = _build_text(channel, _clean_name(a.get("customer_name")),
                       a.get("country"), starts_local, aid)
    out = []
    for order, t in ((0, t1), (1, t2)):
        if t is not None:
            out.append((t, idx, order, {
                "appointment_id": a.get("id"),
                "channel": channel,
                "send_at": t.astimezone(DUBLIN),
                "text": text,
            }))
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    planned = []
    seen = set()
    for idx, a in enumerate(appointments):
        aid = None
        try:
            if not isinstance(a, dict):
                log.warning("item %d is not a dict, skipped", idx)
                continue
            aid = a.get("id")
            if aid is None:
                log.warning("item %d has no id, skipped", idx)
                continue
            if aid in seen:
                log.warning("duplicate appointment id %s, processing independently", aid)
            seen.add(aid)
            planned.extend(_plan_one(a, idx, now, aid))
        except Exception as exc:  # one bad record must not break the batch
            log.error("appointment %s: processing failed (%s), skipped",
                      aid if isinstance(aid, (str, int)) else "?", type(exc).__name__)
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    for t, _, _, d in planned:
        log.info("planned reminder appointment=%s channel=%s send_at=%s",
                 d["appointment_id"], d["channel"], d["send_at"].isoformat())
    log.info("planned %d reminders from %d appointments", len(planned), len(appointments))
    return [p[3] for p in planned]