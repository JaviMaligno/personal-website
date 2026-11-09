import logging
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = ZoneInfo("UTC")
SMS_MAX = 160
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SEND_HOUR = 20

# Only optout_sms_v2 is read; the legacy opt_out field is ignored (stale since
# the March CRM migration). OPEN QUESTION for client: the field is named
# "optout" yet the brief says SMS goes out "if optout_sms_v2 is true", so
# true is treated as consent (literal brief). Confirm polarity.
CONSENT_FIELD = "optout_sms_v2"

_KIND_ORDER = {"2h": 0, "48h": 1}


def _is_sms_consented(appt) -> bool:
    return appt.get(CONSENT_FIELD) is True


def _fail(appt_id, field):
    raise ValueError(f"appointment {appt_id!r}: missing or invalid field '{field}'")


def _validate(appt):
    """Return normalised (id, name, phone, country, starts_at_utc). Never echoes values."""
    appt_id = appt.get("id")
    if appt_id is None or appt_id == "":
        raise ValueError("appointment with missing field 'id'")
    name = appt.get("customer_name")
    if not isinstance(name, str):
        _fail(appt_id, "customer_name")
    phone = appt.get("phone")
    if phone is not None and not isinstance(phone, str):
        _fail(appt_id, "phone")
    country = appt.get("country")
    if country is not None and not isinstance(country, str):
        _fail(appt_id, "country")
    if CONSENT_FIELD not in appt:
        _fail(appt_id, CONSENT_FIELD)
    starts = appt.get("starts_at")
    if not isinstance(starts, datetime) or starts.tzinfo is None or starts.utcoffset() is None:
        _fail(appt_id, "starts_at")
    return appt_id, name, phone, country, starts.astimezone(UTC)


def _in_quiet(dt_utc) -> bool:
    h = dt_utc.astimezone(DUBLIN).hour
    return h >= QUIET_START_HOUR or h < QUIET_END_HOUR


def _local_to_utc(date, hour):
    # Wall time built with fold=0 (first occurrence if ambiguous); the
    # 20:00 and 08:00 targets are never in a DST gap or overlap in Dublin.
    return datetime(date.year, date.month, date.day, hour, tzinfo=DUBLIN).astimezone(UTC)


def _shift_quiet(dt_utc):
    """Move a time inside the quiet window back to the preceding 20:00 local."""
    local = dt_utc.astimezone(DUBLIN)
    d = local.date()
    if local.hour < QUIET_END_HOUR:
        d -= timedelta(days=1)
    return _local_to_utc(d, SEND_HOUR)


def _next_open(dt_utc):
    """Next 08:00 local after a time inside the quiet window."""
    local = dt_utc.astimezone(DUBLIN)
    d = local.date()
    if local.hour >= QUIET_START_HOUR:
        d += timedelta(days=1)
    return _local_to_utc(d, QUIET_END_HOUR)


def _signature(country) -> str:
    sig = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
    return unicodedata.normalize("NFC", sig)


def _shorten_name(name):
    """Yield name variants from longest to shortest, ending with no name."""
    name = unicodedata.normalize("NFC", name.strip())
    if name:
        yield name
        for n in range(len(name) - 1, 1, -1):
            yield name[:n].rstrip() + "…"
        first = name.split()[0]
        yield first
        yield first[0] + "."
    yield ""


def _build_text(appt_name, country, local_start) -> str:
    when = f"{local_start:%d/%m/%Y} at {local_start:%H:%M}"
    sig = _signature(country)
    text = ""
    for n in _shorten_name(appt_name):
        greet = f"Hi {n}, r" if n else "R"
        text = unicodedata.normalize(
            "NFC", f"{greet}eminder of your Brennan Opticians appointment on {when}. {sig}"
        )
        if len(text) <= SMS_MAX:
            return text
    return text


def _schedule(cand, now, start):
    if _in_quiet(cand):
        t = _shift_quiet(cand)
        if t < now:
            t = now if not _in_quiet(now) else _next_open(now)
    else:
        t = cand
    return t if t < start else None


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("'now' must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []

    for appt in appointments:
        appt_id = appt.get("id")
        status = appt.get("status")
        if isinstance(status, str) and status.strip().lower() == "cancelled":
            logger.info("appointment_id=%s skipped: cancelled", appt_id)
            continue
        appt_id, name, phone, country, start = _validate(appt)

        if not (phone and phone.strip()) or not _is_sms_consented(appt):
            logger.info("appointment_id=%s skipped: no phone or no SMS consent", appt_id)
            continue
        if start <= now_utc:
            logger.info("appointment_id=%s skipped: already started", appt_id)
            continue

        local_start = start.astimezone(DUBLIN)
        text = _build_text(name, country, local_start)
        times = {}
        for kind, delta in (("48h", timedelta(hours=48)), ("2h", timedelta(hours=2))):
            cand = max(start - delta, now_utc)
            t = _schedule(cand, now_utc, start)
            if t is None:
                logger.info("appointment_id=%s kind=%s dropped: not before start", appt_id, kind)
                continue
            times[kind] = t
        if "48h" in times and times.get("2h") == times["48h"]:
            del times["48h"]
            logger.info("appointment_id=%s kind=48h dropped: same time as 2h", appt_id)
        for kind, t in times.items():
            planned.append((t, str(appt_id), _KIND_ORDER[kind], appt_id, phone.strip(), text))

    planned.sort(key=lambda p: p[:3])
    out = []
    for t, _, _, appt_id, phone, text in planned:
        logger.info("reminder planned appointment_id=%s channel=sms contact=%s", appt_id, phone)
        out.append({
            "appointment_id": appt_id,
            "channel": "sms",
            "send_at": t.astimezone(DUBLIN),
            "text": text,
        })
    return out