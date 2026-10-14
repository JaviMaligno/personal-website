import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
_KNOWN_ACTIVE = {"confirmed", "booked", "scheduled", "active", "pending"}
_TRUE = {"true", "1", "yes", "y", "t"}
_FALSE = {"false", "0", "no", "n", "f", ""}


def _aware(dt) -> bool:
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _opted_out(value) -> bool:
    """Strict bool parser. Missing -> not opted out; unparseable -> opted out (safe)."""
    if value is None or isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUE:
            return True
        if v in _FALSE:
            return False
    return True


def _channel(appt) -> str | None:
    phone = appt.get("phone")
    if isinstance(phone, str) and phone.strip() and not _opted_out(appt.get("optout_sms_v2")):
        return "sms"
    email = appt.get("email")
    if isinstance(email, str) and email.strip() and "@" in email:
        return "email"
    return None


def _signature(country) -> str:
    if isinstance(country, str) and country.strip().upper() == "PL":
        return "Grzegorz Szczepański"
    return "Chevonne Nee Divver"


def _shorten_name(name: str):
    """Yield progressively shorter name variants, ending with the empty string."""
    parts = name.split()
    if not parts:
        yield ""
        return
    first, last = parts[0], parts[-1]
    seen = set()
    cands = [" ".join(parts)]
    if len(parts) > 1:
        cands += [f"{first} {last[0]}.", f"{first[0]}{last[0]}"]
    cands += [first[0], ""]
    for c in cands:
        if c not in seen:
            seen.add(c)
            yield c


def _build_text(appt, starts_local: datetime, channel: str) -> str:
    date_s = starts_local.strftime("%d/%m/%Y")
    time_s = starts_local.strftime("%H:%M")
    sig = _signature(appt.get("country"))
    raw = appt.get("customer_name")
    name = " ".join(raw.split()) if isinstance(raw, str) else ""

    def render(n: str) -> str:
        greet = f"Hi {n}," if n else "Hi,"
        return f"{greet} your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"

    if channel == "email":
        return render(name)
    text = ""
    for cand in _shorten_name(name):
        text = render(cand)
        if len(text) <= SMS_LIMIT:
            return text
    # Hard fallback: date, time and signature always kept.
    return f"Brennan Opticians: {date_s} at {time_s}. {sig}"[:SMS_LIMIT] if False else \
        f"Brennan Opticians: {date_s} {time_s}. {sig}"


def _apply_quiet_hours(dt_utc: datetime, now: datetime, starts_at: datetime) -> datetime | None:
    """Return an allowed UTC send time, or None if the reminder must be dropped."""
    local = dt_utc.astimezone(DUBLIN)
    if not (local.time() >= time(21) or local.time() < time(8)):
        return dt_utc
    day = local.date() if local.time() >= time(21) else local.date() - timedelta(days=1)
    shifted = datetime.combine(day, time(20), DUBLIN).astimezone(UTC)
    if shifted >= now:
        return shifted
    # Shifting back would be in the past: go forward to the next 08:00 local instead.
    day = local.date() if local.time() < time(8) else local.date() + timedelta(days=1)
    forward = datetime.combine(day, time(8), DUBLIN).astimezone(UTC)
    if now <= forward < starts_at:
        return forward
    return None


def _plan_one(appt, now: datetime) -> list[dict]:
    aid = appt["id"]
    if aid is None or (isinstance(aid, str) and not aid.strip()):
        raise ValueError("missing id")
    status = appt.get("status")
    norm = status.strip().lower() if isinstance(status, str) else None
    if norm in ("cancelled", "canceled"):
        return []
    if norm not in _KNOWN_ACTIVE:
        log.warning("appointment %s has unknown status %r; treating as active", aid, status if isinstance(status, str) else None)
    starts_at = appt.get("starts_at")
    if not _aware(starts_at):
        raise ValueError("starts_at must be timezone-aware")
    start = starts_at.astimezone(UTC)
    if start <= now:
        return []
    channel = _channel(appt)
    if channel is None:
        log.warning("appointment %s has no usable contact; no reminders planned", aid)
        return []

    sends = {}
    for order, delta in ((0, timedelta(hours=48)), (1, timedelta(hours=2))):
        t = max(start - delta, now)
        s = _apply_quiet_hours(t, now, start)
        if s is None:
            log.warning("appointment %s: reminder %s dropped (quiet hours, no valid slot)", aid, "2h" if order else "48h")
            continue
        sends[order] = s
    if 0 in sends and 1 in sends and sends[0] >= sends[1]:
        del sends[0]

    text = _build_text(appt, start.astimezone(DUBLIN), channel)
    return [
        {"appointment_id": aid, "channel": channel, "send_at": s, "text": text, "_order": o}
        for o, s in sends.items()
    ]


def plan_reminders(appointments, now: datetime) -> list[dict]:
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    out = []
    for appt in appointments:
        aid = appt.get("id") if isinstance(appt, dict) else None
        try:
            out.extend(_plan_one(appt, now_utc))
        except Exception as exc:  # never crash the batch; log id and error type only
            log.warning("skipping appointment %s: %s", aid, type(exc).__name__)
    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["_order"]))
    for r in out:
        # Recipient is identified by appointment id and channel only: the DPC audit
        # forbids logging email addresses, so contact details are deliberately omitted.
        log.info(
            "planned reminder appointment=%s channel=%s send_at=%s",
            r["appointment_id"], r["channel"], r["send_at"].isoformat(),
        )
        del r["_order"]
    return out