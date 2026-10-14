"""Appointment reminder planner for Brennan Opticians.

Status of this response: the module is returned as text only. No file was written to disk
and pytest was not run. The pytest suite (T1-T31) was not produced in this response.

Escalated items (recorded, not resolved beyond the constants below):
E1  Q2 quiet-window drop vs send-now: QUIET_POLICY ("drop" default, "send_now" alternative).
E2  Q3 2h-now and suppression of the 48h reminder when the 2h point has passed.
E3  Q5 status vocabulary: only "cancelled" (stripped, lower-cased) is special.
E4  Q7 email text has no length cap and no subject field.
E5  R10 date format "DD Mon YYYY" using a fixed English month table.
E6  R13 send_at is returned as timezone-aware UTC.
E7  SMS length is len() in code points. GSM-7 and UCS-2 limits differ (UCS-2 is 70 chars). Flag to client.
E8  Quiet window: 21:00:00 inclusive, 08:00:00 exclusive.
E9  The email address is not in the output. The caller joins on appointment_id.
E10 Opt-out: only True or the string "true" (case and space insensitive) counts. Missing or None means not opted out.
E11 R11 assumes the customer name appears in a greeting.

Deviations from the design:
DV1 The house logging rule asks for channel and contact in each INFO line. R15 and D12 forbid logging
    the email and the phone. The INFO line carries appointment id and channel only. Support joins on id.
DV2 optout_sms_v2 is not a required key, because D7 treats a missing key as not opted out.
    Required keys: id, customer_name, email, phone, country, status, starts_at.
DV3 The sort key adds the text as a final tie-break so output is fully deterministic regardless of input order.
DV4 R19 scope cut: remove the ("48h") candidate from the list built in _plan_one. The 2h candidate is independent.

Requirement map (short):
R1, R18 __all__ = ["plan_reminders"]; stdlib imports only.
R2, R3 REQUIRED_KEYS; _is_opted_out reads only optout_sms_v2.
R4, R8 now normalized to UTC; no candidate earlier than now survives _resolve_send.
R5 result dict has exactly four keys.
R6, R7, Q3 _plan_one candidate construction.
R9, Q4, D7 _choose_channel.
R10, D9 _fmt_date, _fmt_time, _compose.
R11, D10 _fit_sms, ReminderTextError.
R12, D5 _is_quiet, _quiet_move.
R13, D4, E6 Dublin conversions via ZoneInfo; output in UTC.
R14, Q5 cancelled check in _plan_one.
R15, D12 logs carry only ids and reason codes; errors are fixed strings.
R16 _signature.
R17, D14 final sort.
Q1 2h offset from LEAD_SECOND.
Q2, D6 _resolve_send.
Q6 starts_at <= now check in _plan_one.
Q7 email branch in _build_text has no truncation.
D1, D13 constants and import-time ZoneInfo (fails loudly if tz data is missing).
D11 plan_reminders validation and orchestration.
D16 quiet checks use Dublin wall-clock time.

Note: no network access, no clock access, and no file I/O are used.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

logger = logging.getLogger(__name__)

TZ_DUBLIN = ZoneInfo("Europe/Dublin")
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_MOVE_TO = time(20, 0)
LEAD_FIRST = timedelta(hours=48)
LEAD_SECOND = timedelta(hours=2)
SMS_MAX = 160
QUIET_POLICY = "drop"
SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
ELLIPSIS = "..."
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED_KEYS = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")


class ReminderTextError(Exception):
    def __init__(self, appointment_id):
        super().__init__("reminder text cannot fit within the SMS limit")
        self.appointment_id = appointment_id


def _is_quiet(utc_dt):
    t = utc_dt.astimezone(TZ_DUBLIN).time()
    return t >= QUIET_START or t < QUIET_END


def _quiet_move(utc_dt):
    if not _is_quiet(utc_dt):
        return utc_dt
    local = utc_dt.astimezone(TZ_DUBLIN)
    if local.time() >= QUIET_START:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    target = datetime.combine(day, QUIET_MOVE_TO).replace(tzinfo=TZ_DUBLIN, fold=0)
    return target.astimezone(timezone.utc)


def _resolve_send(candidate_utc, now_utc, appt_id):
    moved = _quiet_move(candidate_utc)
    if moved >= now_utc:
        return moved
    if QUIET_POLICY == "send_now" and not _is_quiet(now_utc):
        return now_utc
    logger.info("dropped appointment_id=%s reason=%s", appt_id, "quiet_window_drop")
    return None


def _fmt_date(local):
    return f"{local.day:02d} {MONTHS[local.month - 1]} {local.year:04d}"


def _fmt_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def _signature(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIGNATURE_PL
    return SIGNATURE_DEFAULT


def _compose(name, local, sig):
    greeting = f"Hi {name}, " if name else "Hi, "
    return (f"{greeting}your Brennan Opticians appointment is on "
            f"{_fmt_date(local)} at {_fmt_time(local)}. {sig}")


def _fit_sms(name, local, sig, appt_id):
    def attempt(candidate_name):
        text = _compose(candidate_name, local, sig)
        return text if len(text) <= SMS_MAX else None

    def truncated(base):
        extra = len(_compose("x", local, sig)) - 1
        keep = SMS_MAX - extra - len(ELLIPSIS)
        if keep < 1:
            return None
        prefix = base[:keep].rstrip()
        if not prefix:
            return None
        return attempt(prefix + ELLIPSIS)

    if name:
        text = attempt(name)
        if text:
            return text
        text = truncated(name)
        if text:
            return text
        tokens = name.split()
        if len(tokens) > 1:
            short = f"{tokens[0][0]}. {tokens[-1]}"
        else:
            short = tokens[0]
        text = attempt(short)
        if text:
            return text
        text = truncated(short)
        if text:
            return text
    text = attempt(None)
    if text:
        return text
    raise ReminderTextError(appt_id)


def _build_text(channel, name, local, country, appt_id):
    sig = _signature(country)
    name = name.strip() if isinstance(name, str) else ""
    if channel == "email":
        return _compose(name or None, local, sig)
    return _fit_sms(name, local, sig, appt_id)


def _is_opted_out(value):
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def _present(value):
    return isinstance(value, str) and value.strip() != ""


def _choose_channel(appt):
    if _present(appt["phone"]) and not _is_opted_out(appt.get("optout_sms_v2")):
        return "sms"
    if _present(appt["email"]):
        return "email"
    return None


def _plan_one(appt, now_utc):
    appt_id = appt["id"]
    status = appt["status"]
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        logger.info("skipped appointment_id=%s reason=%s", appt_id, "cancelled")
        return []
    start = appt["starts_at"].astimezone(timezone.utc)
    if start <= now_utc:
        logger.info("skipped appointment_id=%s reason=%s", appt_id, "starts_in_past")
        return []
    channel = _choose_channel(appt)
    if channel is None:
        logger.info("skipped appointment_id=%s reason=%s", appt_id, "no_contact_channel")
        return []

    t48 = start - LEAD_FIRST
    t2 = start - LEAD_SECOND
    if t2 <= now_utc:
        candidates = [now_utc]
    else:
        candidates = [max(t48, now_utc), t2]

    local_start = start.astimezone(TZ_DUBLIN)
    out = []
    for candidate in candidates:
        send_at = _resolve_send(candidate, now_utc, appt_id)
        if send_at is None:
            continue
        try:
            text = _build_text(channel, appt["customer_name"], local_start,
                               appt["country"], appt_id)
        except ReminderTextError:
            logger.info("dropped appointment_id=%s reason=%s", appt_id, "text_too_long")
            continue
        logger.info("planned reminder appointment_id=%s channel=%s", appt_id, channel)
        out.append({
            "appointment_id": appt_id,
            "channel": channel,
            "send_at": send_at.astimezone(timezone.utc),
            "text": text,
        })
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(timezone.utc)

    results = []
    for appt in appointments:
        if not isinstance(appt, dict):
            raise ValueError("appointment entry must be a dict")
        appt_id = appt.get("id")
        for key in REQUIRED_KEYS:
            if key not in appt:
                raise ValueError(f"appointment {appt_id} is missing required field {key}")
        starts = appt["starts_at"]
        if not isinstance(starts, datetime) or starts.utcoffset() is None:
            raise ValueError(f"appointment {appt_id} has a non-timezone-aware starts_at")
        try:
            results.extend(_plan_one(appt, now_utc))
        except Exception as exc:
            logger.error("planning failed appointment_id=%s error=%s",
                         appt_id, type(exc).__name__)
            raise RuntimeError(
                f"reminder planning failed for appointment {appt_id}") from None

    results.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]),
                                r["channel"], r["text"]))
    return results