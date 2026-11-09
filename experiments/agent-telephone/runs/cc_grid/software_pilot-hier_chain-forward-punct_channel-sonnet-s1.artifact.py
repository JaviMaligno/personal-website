import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
DUBLIN = ZoneInfo("Europe/Dublin")
MAX_SMS = 160


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _signature(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return "Grzegorz Szczepański"
    return "Siobhán Ní Dhuibhir"


def _channel(appt):
    """SMS only: phone present and optout_sms_v2 is exactly True. Legacy opt_out is ignored."""
    phone = appt.get("phone")
    if isinstance(phone, str) and phone.strip() and appt.get("optout_sms_v2") is True:
        return "sms"
    return None


def _apply_quiet_hours(dt_utc, now):
    """Move a time in 21:00-08:00 Dublin back to 20:00 before the window.
    Returns None if the result would be earlier than now (never send in the
    past or inside quiet hours; deferring later is not allowed, so it is dropped)."""
    local = dt_utc.astimezone(DUBLIN)
    if local.hour >= 21 or local.hour < 8:
        day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
        local = datetime(day.year, day.month, day.day, 20, 0, tzinfo=DUBLIN)
    result = local.astimezone(DUBLIN)
    return None if result < now else result


def _build_text(name, local_start, signature):
    when = f"{local_start:%d/%m/%Y} at {local_start:%H:%M}"
    name = (name or "").strip() if isinstance(name, str) else ""

    def fmt(n, brand=True):
        who = f" {n}," if n else ""
        shop = "your Brennan Opticians appointment" if brand else "your appointment"
        return f"Reminder:{who} {shop} is on {when}. {signature}"

    names = [name]
    names += [name[:k].rstrip() + "..." for k in range(len(name) - 1, 0, -1)]
    if name:
        names.append(name[0] + ".")
    names.append("")
    for n in names:
        text = fmt(n)
        if len(text) <= MAX_SMS:
            return text
    return fmt("", brand=False)


def plan_reminders(appointments, now):
    """Plan SMS reminders at 48h and 2h before each appointment (Europe/Dublin).

    Assumptions: a missed 2h point is not sent late; a 48h point already passed
    is moved to now; anything moved out of quiet hours that lands before now is
    dropped; reminders at/after the start are dropped; on collapse or overlap
    only the 2h reminder is kept. Inputs are never mutated.
    """
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    planned = []
    for idx, appt in enumerate(appointments):
        try:
            appt_id = appt.get("id")
        except Exception:
            log.warning("skipping malformed appointment at index %s", idx)
            continue
        try:
            status = appt.get("status")
            if isinstance(status, str) and status.strip().casefold() == "cancelled":
                log.info("appointment %s skipped: cancelled", appt_id)
                continue
            channel = _channel(appt)
            if channel is None:
                log.info("appointment %s skipped: no SMS consent or phone", appt_id)
                continue
            starts = appt["starts_at"]
            if not _aware(starts):
                raise ValueError("naive starts_at")
            if starts <= now:
                log.info("appointment %s skipped: already started", appt_id)
                continue
            t48 = max(starts - timedelta(hours=48), now)
            t2 = starts - timedelta(hours=2)
            s2 = _apply_quiet_hours(t2, now) if t2 >= now else None
            s48 = _apply_quiet_hours(t48, now)
            if s2 is not None and s2 >= starts:
                s2 = None
            if s48 is not None and s48 >= starts:
                s48 = None
            if s2 is not None and s48 is not None and s48 >= s2:
                s48 = None
            if s2 is None and t2 >= now:
                log.info("appointment %s: 2h reminder dropped", appt_id)
            if s48 is None:
                log.info("appointment %s: 48h reminder dropped", appt_id)
            text = _build_text(appt.get("customer_name"),
                               starts.astimezone(DUBLIN), _signature(appt.get("country")))
            phone = appt["phone"].strip()
            for kind, send_at in ((0, s48), (1, s2)):
                if send_at is None:
                    continue
                planned.append(((send_at, idx, kind), {
                    "appointment_id": appt_id,
                    "channel": channel,
                    "send_at": send_at,
                    "text": text,
                }))
                # Contact is the SMS phone number (never email or name), per support tracing rule.
                log.info("reminder planned: appointment=%s channel=%s contact=%s send_at=%s",
                         appt_id, channel, phone, send_at.isoformat())
        except Exception:
            log.warning("appointment %s skipped: malformed", appt_id)
    planned.sort(key=lambda p: p[0])
    return [r for _, r in planned]