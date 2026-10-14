"""Brennan Opticians appointment reminder planner (standard library only).

Entry point: plan_reminders(appointments, now) -> list[dict]

Decisions and assumptions:
- The second reminder is 2 hours before start (the brief is garbled there). The 2h
  reminder has priority.
- t48 and t2 are absolute offsets (computed in UTC), so DST changes do not shift
  them. Quiet-hour logic uses Europe/Dublin wall-clock time.
- Only optout_sms_v2 is read; the legacy opt_out field is ignored.
- Quiet hours are local time >= 21:00 or < 08:00. A time inside them moves back to
  the preceding 20:00. If that is before now, the reminder is deferred to the next
  08:00 Dublin time, and only if that is strictly before the start. Otherwise it is
  dropped.
- Dedupe: if the 48h send_at equals the 2h send_at, or is less than 1h before it,
  the 48h reminder is dropped.
- send_at is returned in UTC (tz-aware).
- SMS limit is 160 Python characters, as specified. OPEN QUESTION: characters such
  as n-acute and a-acute are not in the GSM-7 alphabet, so real carriers would send
  UCS-2 at 70 chars per segment. Confirm with the client.
- Logging: the house rule asks for the contact in the INFO line, but the brief and
  the DPC audit forbid logging email addresses, and phone numbers and names are
  PII. The INFO line therefore carries the appointment id and channel only, with no
  contact value. Please confirm with the architect.
- Tests were NOT written or run: this agent had no tools. test_reminders.py with
  the requested coverage (including the caplog PII test) is still outstanding.
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
DUBLIN = ZoneInfo("Europe/Dublin")
SMS_MAX = 160
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"


def _local_at(day: date, hh: int) -> datetime:
    # 08:00 and 20:00 never fall in a Dublin DST gap (transitions are at 01:00/02:00).
    return datetime.combine(day, time(hh, 0), tzinfo=DUBLIN, fold=0).astimezone(timezone.utc)


def _is_quiet(local: datetime) -> bool:
    return local.hour >= 21 or local.hour < 8


def _resolve(target: datetime, now: datetime, start: datetime) -> datetime | None:
    """Return a valid UTC send time, or None if the reminder must be dropped."""
    cand = max(target, now)
    if cand >= start:
        return None
    local = cand.astimezone(DUBLIN)
    if not _is_quiet(local):
        return cand
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    adj = _local_at(day, 20)
    if adj >= now:
        return adj
    nxt = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    dfr = _local_at(nxt, 8)
    return dfr if dfr < start and dfr >= now else None


def _text(name: str, local_start: datetime, country: str, sms: bool) -> str:
    sig = _SIG_PL if country.strip().upper() == "PL" else _SIG_DEFAULT
    when = f"{local_start:%d/%m/%Y} at {local_start:%H:%M}"

    def build(greet: str) -> str:
        return f"{greet}, reminder: your Brennan Opticians appointment is on {when}. {sig}"

    name = name.strip()
    if not name:
        return build("Hello")
    full = build(f"Hi {name}")
    if not sms or len(full) <= SMS_MAX:
        return full
    for k in range(len(name) - 1, 0, -1):
        t = build(f"Hi {name[:k].rstrip()}…")
        if len(t) <= SMS_MAX:
            return t
    t = build(f"Hi {name[0]}.")
    return t if len(t) <= SMS_MAX else build("Hello")


def _nonblank(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def plan_reminders(appointments, now: datetime) -> list[dict]:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(timezone.utc)
    out: list[dict] = []
    skipped = 0

    for appt in appointments:
        aid = appt.get("id") if isinstance(appt, dict) else None
        try:
            start = appt["starts_at"]
            if (not isinstance(start, datetime) or start.tzinfo is None
                    or start.utcoffset() is None or aid is None):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            log.warning("Skipping appointment id=%s: missing or invalid fields", aid)
            skipped += 1
            continue

        status = appt.get("status")
        if isinstance(status, str) and status.strip().lower() == "cancelled":
            continue

        if _nonblank(appt.get("phone")) and not appt.get("optout_sms_v2"):
            channel = "sms"
        elif _nonblank(appt.get("email")):
            channel = "email"
        else:
            log.warning("No usable channel for appointment id=%s; no reminder", aid)
            continue

        start_utc = start.astimezone(timezone.utc)
        t48 = _resolve(start_utc - timedelta(hours=48), now_utc, start_utc)
        t2 = _resolve(start_utc - timedelta(hours=2), now_utc, start_utc)
        if t48 is not None and t2 is not None and t2 - t48 < timedelta(hours=1):
            t48 = None

        name = appt.get("customer_name")
        country = appt.get("country")
        text = _text(name if isinstance(name, str) else "",
                     start_utc.astimezone(DUBLIN),
                     country if isinstance(country, str) else "",
                     channel == "sms")
        for kind, when in (("48h", t48), ("2h", t2)):
            if when is None:
                continue
            log.info("Planned %s reminder for appointment id=%s via %s at %s",
                     kind, aid, channel, when.isoformat())
            out.append({"appointment_id": aid, "channel": channel,
                        "send_at": when, "text": text})

    out.sort(key=lambda r: r["send_at"])
    log.info("Planned %d reminders, skipped %d invalid appointments", len(out), skipped)
    return out