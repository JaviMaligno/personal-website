"""Brennan Opticians appointment reminder planner (stdlib only, Python 3.12).

Entry point: plan_reminders(appointments, now) -> list[dict] with keys
appointment_id, channel, send_at, text. Output is sorted by send_at (ties by
appointment_id, then reminder kind). send_at is tz-aware in Europe/Dublin.

Decisions and assumptions
1. ASSUMPTION: the second reminder is 2 hours before the appointment. The brief
   says "the second one too, hours before" with the number missing. Client to
   confirm. See REMINDER_OFFSETS.
2. Quiet window is 21:00-08:00 Europe/Dublin local time. A time in the window
   moves to the previous 20:00 local (built from wall-clock date plus 20:00, so
   DST is handled). 08:00 and 20:59 are allowed, 21:00 is not. Offsets are
   computed in absolute time, then converted to local time for the window check.
3. `now` must be timezone-aware, otherwise ValueError. Appointments with a
   missing, naive or invalid starts_at are skipped with a warning (id only).
4. Per reminder, target = starts_at - offset. For the 48h reminder, a target
   before `now` becomes `now`. The quiet window is then applied. If the result
   is before `now` the reminder is DROPPED (never sent in the quiet window,
   never in the past). It is also dropped if send_at >= starts_at. If the 48h
   send_at is not strictly before the 2h send_at, only the 2h reminder is kept
   (the 2h reminder has priority, and two reminders are never sent at the same
   instant).
5. Status "cancelled" (stripped, case-insensitive) is skipped. A missing status
   counts as active.
6. Signature is "Grzegorz Szczepański" if country is PL (stripped,
   case-insensitive), otherwise "Siobhán Ní Dhuibhir". Every text ends with it.
7. Text format: "Hi {name}, reminder: your Brennan Opticians appointment is on
   DD/MM/YYYY at HH:MM. {signature}" (Dublin local time). SMS is limited to 160
   characters (len() of the str). Only the name is shortened: full name, then
   first name, then truncated first name with ".", then an initial, then no
   name. Date and time are never altered. OPEN QUESTION: ń, á, ó etc. are
   non-GSM, so a real SMS would use UCS-2 with 70-character segments. Not
   handled here.
8. Channel is SMS if phone is non-blank and optout_sms_v2 is not True / "true".
   Otherwise email if an email is present. Never both. If there is no usable
   channel, no reminder is produced and a warning with the id is logged. The
   legacy `opt_out` field is never read.
9. Phone and email are never logged. The house rule asks for one INFO line per
   planned reminder saying who it goes to and how. That is satisfied with the
   appointment id and channel only, because the Data Protection Commission audit
   forbids logging email addresses, and the design note forbids phone numbers.
   Support can look up the contact from the appointment id.
10. Inputs are not mutated. A per-appointment error is logged with the id and
    exception type only, and does not stop the run.

Tests have not been run (no execution tools were available in this session).
"""

from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

# (kind, offset before start). The 2h offset is an ASSUMPTION, see docstring.
REMINDER_OFFSETS = (
    ("first", timedelta(hours=48)),
    ("second", timedelta(hours=2)),
)

SMS_MAX = 160
_KIND_ORDER = {k: i for i, (k, _) in enumerate(REMINDER_OFFSETS)}


def _signature(country) -> str:
    if isinstance(country, str) and country.strip().upper() == "PL":
        sig = "Grzegorz Szczepański"
    else:
        sig = "Siobhán Ní Dhuibhir"
    return unicodedata.normalize("NFC", sig)


def _aware(dt) -> bool:
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _compute_send_times(starts_at: datetime, now: datetime) -> dict:
    """Raw targets per kind, in absolute (UTC) time, with the 48h clamp to now."""
    out = {}
    start_utc = starts_at.astimezone(UTC)
    now_utc = now.astimezone(UTC)
    for kind, offset in REMINDER_OFFSETS:
        target = start_utc - offset
        if kind == "first" and target < now_utc:
            target = now_utc
        out[kind] = target
    return out


def _apply_quiet_window(t: datetime) -> datetime:
    """Return t in Dublin time, moved back to the previous 20:00 if in 21:00-08:00."""
    local = t.astimezone(DUBLIN)
    if local.hour >= 21:
        day = local.date()
    elif local.hour < 8:
        day = local.date() - timedelta(days=1)
    else:
        return local
    shifted = datetime.combine(day, time(20, 0), tzinfo=DUBLIN)
    return shifted.astimezone(DUBLIN)


def _opted_out(value) -> bool:
    if value is True:
        return True
    return isinstance(value, str) and value.strip().lower() == "true"


def _nonblank(value) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _choose_channel(appt: dict) -> str | None:
    if _nonblank(appt.get("phone")) and not _opted_out(appt.get("optout_sms_v2")):
        return "sms"
    if _nonblank(appt.get("email")):
        return "email"
    return None


def _shorten_name(name: str, room: int) -> str:
    """Return a version of name with len <= room, or "" if impossible."""
    if len(name) <= room:
        return name
    first = name.split()[0] if name.split() else ""
    if first and len(first) <= room:
        return first
    if first and room >= 2:
        return first[: room - 1] + "."
    if first and room >= 1:
        return first[0] if room == 1 else ""
    return ""


def _build_text(name: str | None, when: datetime, signature: str, channel: str) -> str:
    local = when.astimezone(DUBLIN)
    date_s = local.strftime("%d/%m/%Y")
    time_s = local.strftime("%H:%M")
    name = _nonblank(name) or "there"

    def render(n: str) -> str:
        greet = f"Hi {n}, reminder:" if n else "Reminder:"
        return (f"{greet} your Brennan Opticians appointment is on "
                f"{date_s} at {time_s}. {signature}")

    text = render(name)
    if channel != "sms" or len(text) <= SMS_MAX:
        return text
    room = SMS_MAX - len(render("x")) + 1
    short = _shorten_name(name, room)
    if not short and name:
        short = ""  # fall back to the no-name form
    return render(short)


def _plan_one(appt: dict, now: datetime) -> list:
    aid = appt.get("id")
    if aid is None or (isinstance(aid, str) and not aid.strip()):
        log.warning("Skipping appointment with missing id")
        return []
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        return []
    starts_at = appt.get("starts_at")
    if not _aware(starts_at):
        log.warning("Skipping appointment %s: invalid starts_at", aid)
        return []
    channel = _choose_channel(appt)
    if channel is None:
        log.warning("No usable channel for appointment %s", aid)
        return []

    now_utc = now.astimezone(UTC)
    kept = {}
    for kind, target in _compute_send_times(starts_at, now).items():
        send_at = _apply_quiet_window(target)
        if send_at.astimezone(UTC) < now_utc or send_at >= starts_at:
            continue
        kept[kind] = send_at
    if "first" in kept and "second" in kept and kept["first"] >= kept["second"]:
        del kept["first"]

    sig = _signature(appt.get("country"))
    result = []
    for kind, send_at in kept.items():
        result.append((send_at, str(aid), _KIND_ORDER[kind], {
            "appointment_id": aid,
            "channel": channel,
            "send_at": send_at,
            "text": _build_text(appt.get("customer_name"), starts_at, sig, channel),
        }))
        log.info("Planned %s reminder for appointment %s via %s at %s",
                 kind, aid, channel, send_at.isoformat())
    return result


def plan_reminders(appointments, now) -> list[dict]:
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for appt in appointments:
        try:
            planned.extend(_plan_one(appt, now))
        except Exception as exc:  # one bad appointment must not stop the run
            aid = appt.get("id") if isinstance(appt, dict) else None
            log.warning("Error planning appointment %s: %s", aid, type(exc).__name__)
    planned.sort(key=lambda p: (p[0].astimezone(UTC), p[1], p[2]))
    return [p[3] for p in planned]