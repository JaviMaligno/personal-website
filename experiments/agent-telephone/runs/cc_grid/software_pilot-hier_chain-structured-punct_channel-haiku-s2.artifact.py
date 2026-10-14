# brennan_reminders.py
#
# Status: NOT EXECUTED. No tools were available, so pytest was not run and no
# test files were written. Treat this module as unverified until tests run.
#
# Deviations from the brief:
# 1. Logging: the house rule asks for the contact in each INFO line, but R11
#    forbids logging email or phone. R11 is followed, so INFO lines carry the
#    appointment id and channel only.
# 2. The 160-character limit and name shortening apply to SMS only. Email text
#    has no length limit.
# 3. A non-string status is skipped with reason "invalid_status" (not in the brief).
# 4. KNOWN_STATUSES is a placeholder list (A-Q7).
# 5. T1 to T32 are not implemented as tests. T5 as written references the
#    field the brief forbids, so it must be rewritten before it can be used.
#
# Risks:
# - GSM-7 vs UCS-2: the Polish and Irish signatures contain characters outside
#   GSM-7 (a-acute, i-acute, n-acute, s-acute). Real SMS would be UCS-2 at 70
#   characters per segment, so a text within 160 code points may still go out
#   as several segments.
# - A-Q2: quiet-hours overflow drops reminders, which can leave a booking with
#   no reminder at all.
# - Shifting to 20:00 can place a send time days before the appointment for
#   bookings made shortly after a quiet window.

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders", "choose_channel"]

# ---- Configuration: every assumption lives here ----

LOGGER_NAME = "brennan_reminders"
log = logging.getLogger(LOGGER_NAME)

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_SHIFT_TO = time(20, 0)
SMS_MAX_CHARS = 160

# ASSUMPTION A-Q1 (pending client): "none" or "email". "email" is used only when
# no phone is present and an email address is present.
NO_PHONE_POLICY = "none"
# ASSUMPTION A-Q2 (pending client): only "drop" is implemented.
QUIET_OVERFLOW_POLICY = "drop"
# ASSUMPTION A-Q7 (pending client): placeholder list of recognised statuses.
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
KNOWN_STATUSES = frozenset({"booked", "confirmed", "scheduled", "pending"}) | CANCELLED_STATUSES

REQUIRED_KEYS = (
    "id", "customer_name", "email", "phone", "country",
    "status", "starts_at", "optout_sms_v2",
)
SIG_DEFAULT = unicodedata.normalize("NFC", "Siobh\u00e1n N\u00ed Dhuibhir")
SIG_PL = unicodedata.normalize("NFC", "Grzegorz Szczepa\u0144ski")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# ASSUMPTION A-Q5 (pending client): message wording.
TEMPLATE_WITH_NAME = (
    "Hi {name}, this is a reminder of your appointment at Brennan Opticians "
    "on {date} at {time}. {signature}"
)
TEMPLATE_NO_NAME = (
    "Hi, this is a reminder of your appointment at Brennan Opticians "
    "on {date} at {time}. {signature}"
)


@dataclass(frozen=True)
class Appointment:
    id: Any
    customer_name: str
    email: Optional[str]
    phone: Optional[str]
    country: Optional[str]
    status: str
    starts_at: datetime  # UTC-aware
    sms_opted_out: bool


# ---- Validation (R1, R2, R10, R11) ----

def _skip(ident: Any, reason: str) -> None:
    log.warning("skipped id=%s reason=%s", ident, reason)


def _clean(value: Any) -> Optional[str]:
    text = value.strip() if isinstance(value, str) else ""
    return text or None


def _parse(raw: Any) -> Optional[Appointment]:
    if not isinstance(raw, dict):
        _skip(None, "not_a_mapping")
        return None
    ident = raw.get("id")
    for key in REQUIRED_KEYS:
        if key not in raw:
            _skip(ident, "missing_key:" + key)
            return None
    if not isinstance(ident, (str, int)) or isinstance(ident, bool):
        _skip(None, "invalid_id")
        return None
    starts = raw["starts_at"]
    if not isinstance(starts, datetime):
        _skip(ident, "invalid_starts_at")
        return None
    if starts.utcoffset() is None:
        _skip(ident, "naive_starts_at")
        return None
    status = raw["status"]
    if not isinstance(status, str):
        _skip(ident, "invalid_status")
        return None
    flag = raw["optout_sms_v2"]
    if type(flag) is not bool:
        # Fail-safe: a non-bool flag means opted out.
        log.warning("invalid_optout_flag id=%s", ident)
        flag = True
    name = raw["customer_name"]
    return Appointment(
        id=ident,
        customer_name=name.strip() if isinstance(name, str) else "",
        email=_clean(raw["email"]),
        phone=_clean(raw["phone"]),
        country=_clean(raw["country"]),
        status=status.strip().lower(),
        starts_at=starts.astimezone(UTC),
        sms_opted_out=flag,
    )


# ---- Channel rule (R6); the only place it lives ----

def choose_channel(appointment: Appointment) -> Optional[str]:
    if appointment.sms_opted_out:
        # ASSUMPTION A-Q1 (pending client): opted out means no reminder at all.
        return None
    if appointment.phone:
        return "sms"
    if NO_PHONE_POLICY == "email" and appointment.email:
        return "email"
    return None


# ---- Schedule (R3, R4, A-Q4); all arithmetic in UTC ----

def candidate_times(starts_utc: datetime, now_utc: datetime) -> list[datetime]:
    if now_utc >= starts_utc:
        return []
    first = starts_utc - FIRST_OFFSET
    second = starts_utc - SECOND_OFFSET
    if now_utc >= second:
        return [now_utc]
    if now_utc >= first:
        return [now_utc, second]
    return [first, second]


# ---- Quiet hours (R9, R14) ----

def dublin_wall_to_utc(wall: datetime, fold: int = 0) -> datetime:
    """Convert a naive Dublin wall-clock time to a UTC-aware datetime."""
    return wall.replace(tzinfo=DUBLIN, fold=fold).astimezone(UTC)


def apply_quiet_hours(send_at: datetime, now_utc: datetime) -> Optional[datetime]:
    if QUIET_OVERFLOW_POLICY != "drop":
        raise NotImplementedError("only QUIET_OVERFLOW_POLICY 'drop' is implemented")
    local = send_at.astimezone(DUBLIN)
    t = local.time()
    if t >= QUIET_START or t < QUIET_END:
        day = local.date() if t >= QUIET_START else local.date() - timedelta(days=1)
        send_at = dublin_wall_to_utc(datetime.combine(day, QUIET_SHIFT_TO))
    if send_at < now_utc:
        # ASSUMPTION A-Q2 (pending client): a shifted or past time is dropped, not moved.
        return None
    return send_at


# ---- Message text (R7, R8, R12) ----

def signature_for(country: Optional[str]) -> str:
    code = country.strip().upper() if isinstance(country, str) else ""
    return SIG_PL if code == "PL" else SIG_DEFAULT


def _local_parts(starts_utc: datetime) -> tuple[str, str]:
    local = starts_utc.astimezone(DUBLIN)
    date_s = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    return date_s, time_s


def _name_options(name: str) -> list[str]:
    name = unicodedata.normalize("NFC", name)
    parts = name.split()
    options = [name]
    if len(parts) >= 2:
        options.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        options.append(parts[0])
    options.append("")
    return list(dict.fromkeys(options))


def _render(name: str, date_s: str, time_s: str, sig: str) -> str:
    if name:
        return TEMPLATE_WITH_NAME.format(name=name, date=date_s, time=time_s, signature=sig)
    return TEMPLATE_NO_NAME.format(date=date_s, time=time_s, signature=sig)


def build_text(appt: Appointment, channel: str) -> Optional[str]:
    sig = signature_for(appt.country)
    date_s, time_s = _local_parts(appt.starts_at)
    names = _name_options(appt.customer_name) if channel == "sms" else [appt.customer_name]
    for name in names:
        text = unicodedata.normalize("NFC", _render(name, date_s, time_s, sig))
        if channel != "sms" or len(text) <= SMS_MAX_CHARS:
            return text
    return None  # Only possible for SMS, when even the nameless text is too long.


# ---- Orchestration (R5, R13, R15, A-Q4, R11) ----

def plan_reminders(appointments, now: datetime) -> list[dict]:
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)

    rows = list(appointments)
    parsed = [a for a in (_parse(r) for r in rows) if a is not None]
    skipped = len(rows) - len(parsed)
    unknown = sum(1 for a in parsed if a.status not in KNOWN_STATUSES)

    out: list[dict] = []
    seen: set = set()
    for a in parsed:
        if a.status in CANCELLED_STATUSES:
            log.info("no reminders id=%s reason=cancelled", a.id)
            continue
        channel = choose_channel(a)
        if channel is None:
            log.info("no reminders id=%s reason=no_channel", a.id)
            continue
        for candidate in candidate_times(a.starts_at, now_utc):
            send_at = apply_quiet_hours(candidate, now_utc)
            if send_at is None:
                log.info("dropped id=%s reason=before_now", a.id)
                continue
            key = (a.id, channel, send_at)
            if key in seen:
                continue
            text = build_text(a, channel)
            if text is None:
                log.error("template_too_long id=%s", a.id)
                continue
            seen.add(key)
            out.append({
                "appointment_id": a.id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            log.info("planned reminder id=%s channel=%s", a.id, channel)

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    log.info("summary planned=%d skipped=%d unknown_status=%d", len(out), skipped, unknown)
    return out