"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now).

Notes for the report (deviations and open risks):
- NOT RUN: this module was produced without tool access, so the pytest
  suite (tests/test_reminders.py) was neither written nor executed here.
- LOGGING / PII: the house rule asks for the contact in the per-reminder
  INFO line, but the brief forbids logging email addresses (DPC audit) and
  the design forbids phones and names. The INFO line therefore carries only
  the appointment id, kind and channel. The sending layer resolves the
  address from appointment_id.
- CONSENT DECISION: a missing or None optout_sms_v2 is treated as opted
  out (see SMS_OPTOUT_MISSING_MEANS_OPTED_OUT). This deliberately diverges
  from the literal brief. Only optout_sms_v2 is read, never opt_out.
- GSM-7 vs UCS-2: a, i, o, n with accents and the ellipsis force UCS-2,
  where one SMS segment is 70 characters. The 160 code point limit is
  applied as specified, so such messages may bill as several segments.
- DST: reminders use absolute durations, so local wall-clock time shifts
  by 1h across a DST change. This is accepted.
"""

from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SHIFT_BACK_TIME = time(20, 0)
DEFER_TIME = time(8, 0)

# Consent-safe default: a missing or None optout_sms_v2 means "opted out".
SMS_OPTOUT_MISSING_MEANS_OPTED_OUT = True

SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
EMAIL_EXTRA = "Reply to this message if you need to reschedule."

KIND_48H = 0
KIND_2H = 1
_KIND_NAMES = {KIND_48H: "48h", KIND_2H: "2h"}


def _is_opted_out(value) -> bool:
    if value is None:
        return SMS_OPTOUT_MISSING_MEANS_OPTED_OUT
    return value is not False


def _in_quiet(local: datetime) -> bool:
    return local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR


def _local_at(day, t: time) -> datetime:
    return datetime.combine(day, t, tzinfo=DUBLIN).astimezone(UTC)


def _adjust(point: datetime, now: datetime, start: datetime):
    """Return (send_time_utc, reason). send_time is None if dropped."""
    local = point.astimezone(DUBLIN)
    if not _in_quiet(local):
        return point, None
    if local.hour >= QUIET_START_HOUR:
        back_day = local.date()
        fwd_day = local.date() + timedelta(days=1)
    else:
        back_day = local.date() - timedelta(days=1)
        fwd_day = local.date()
    shifted = _local_at(back_day, SHIFT_BACK_TIME)
    if shifted >= now:
        return shifted, None
    deferred = _local_at(fwd_day, DEFER_TIME)
    if deferred < start:
        return deferred, None
    return None, "quiet hours and no valid send time before the appointment"


def _clean_name(name) -> str:
    if not isinstance(name, str):
        return ""
    return unicodedata.normalize("NFC", " ".join(name.split()))


def _compose(name: str, date_s: str, time_s: str, sig: str, extra: str) -> str:
    greet = f"Hi {name}," if name else "Hi,"
    body = f"{greet} your Brennan Opticians appointment is on {date_s} at {time_s}."
    if extra:
        body += " " + extra
    return unicodedata.normalize("NFC", f"{body} {sig}")


def _build_text(raw_name, local_start: datetime, sig: str, channel: str) -> str:
    date_s = f"{local_start:%d/%m/%Y}"
    time_s = f"{local_start:%H:%M}"
    name = _clean_name(raw_name)
    if channel == "email":
        return _compose(name, date_s, time_s, sig, EMAIL_EXTRA)

    def fits(n: str) -> str | None:
        t = _compose(n, date_s, time_s, sig, "")
        return t if len(t) <= SMS_LIMIT else None

    if not name:
        return _compose("", date_s, time_s, sig, "")
    first = name.split(" ")[0]
    text = fits(name) or fits(first)
    if text:
        return text
    # Remaining budget for the name characters in "Hi {name},".
    room = SMS_LIMIT - len(_compose("X", date_s, time_s, sig, "")) + 1
    if room - 1 >= 1:
        text = fits(first[: room - 1] + "…")
        if text:
            return text
    text = fits(first[0] + ".")
    if text:
        return text
    return _compose("", date_s, time_s, sig, "")


def _ident(appt, idx: int) -> str:
    if isinstance(appt, dict):
        i = appt.get("id")
        if isinstance(i, (str, int)) and not isinstance(i, bool) and str(i).strip():
            return str(i)
    return f"index {idx}"


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def plan_reminders(appointments, now) -> list[dict]:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not isinstance(appointments, (list, tuple)):
        raise TypeError("appointments must be a list or tuple")

    now_utc = now.astimezone(UTC)
    planned = []  # (send_at, str_id, kind, dict)

    for idx, appt in enumerate(appointments):
        label = _ident(appt, idx)
        if not isinstance(appt, dict):
            logger.warning("skipping malformed appointment (%s)", label)
            continue
        aid = appt.get("id")
        starts = appt.get("starts_at")
        status = appt.get("status")
        if (
            label == f"index {idx}"
            or not isinstance(starts, datetime)
            or not (status is None or isinstance(status, str))
        ):
            logger.warning("skipping malformed appointment (%s)", label)
            continue
        if starts.tzinfo is None or starts.utcoffset() is None:
            raise ValueError(f"starts_at must be timezone-aware (appointment {label})")

        if status and status.strip().lower() in ("cancelled", "canceled"):
            continue
        start_utc = starts.astimezone(UTC)
        if start_utc <= now_utc:
            continue

        optout_raw = appt.get("optout_sms_v2")
        if optout_raw is not None and not isinstance(optout_raw, bool):
            logger.warning("skipping malformed appointment (%s)", label)
            continue
        if _nonempty_str(appt.get("phone")) and not _is_opted_out(optout_raw):
            channel = "sms"
        elif _nonempty_str(appt.get("email")):
            channel = "email"
        else:
            logger.info("no usable contact channel for appointment %s", label)
            continue

        country = appt.get("country")
        pl = isinstance(country, str) and country.strip().upper() == "PL"
        sig = SIGNATURE_PL if pl else SIGNATURE_DEFAULT
        local_start = start_utc.astimezone(DUBLIN)
        text = _build_text(appt.get("customer_name"), local_start, sig, channel)

        # 2h first: it has priority.
        final2 = None
        t2 = start_utc - timedelta(hours=2)
        if t2 >= now_utc:
            final2, reason = _adjust(t2, now_utc, start_utc)
            if final2 is None:
                logger.info("dropping 2h reminder for %s: %s", label, reason)

        t48 = max(start_utc - timedelta(hours=48), now_utc)
        final48, reason = _adjust(t48, now_utc, start_utc)
        if final48 is None:
            logger.info("dropping 48h reminder for %s: %s", label, reason)
        elif final2 is not None and final48 >= final2:
            logger.info("dropping 48h reminder for %s: collides with 2h reminder", label)
            final48 = None

        for kind, final in ((KIND_48H, final48), (KIND_2H, final2)):
            if final is None:
                continue
            local = final.astimezone(DUBLIN)
            if final < now_utc or _in_quiet(local):
                logger.warning(
                    "dropping %s reminder for %s: final guard violated",
                    _KIND_NAMES[kind], label,
                )
                continue
            logger.info(
                "planned reminder appointment_id=%s kind=%s channel=%s",
                label, _KIND_NAMES[kind], channel,
            )
            planned.append((
                local, str(aid), kind,
                {"appointment_id": aid, "channel": channel, "send_at": local, "text": text},
            ))

    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    return [p[3] for p in planned]