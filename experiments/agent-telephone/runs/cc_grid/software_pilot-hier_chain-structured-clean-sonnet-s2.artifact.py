"""Brennan Opticians reminder planner (stdlib only, Python 3.9+).

Public entry point: plan_reminders(appointments, now).

Assumptions and flagged ambiguities (not resolved differently from the brief):
- The opt-out flag is optout_sms_v2 (R3). The legacy opt_out key is never read.
- House rule vs R11: the per-reminder INFO log names the appointment id, the
  channel and the contact kind ("phone" or "email"). The contact value is
  never logged, because R11 forbids logging email addresses and phones.
- The 160 limit is Python len(). Characters such as a-acute, n-acute, l-stroke
  and o-acute force UCS-2 SMS encoding (70 per segment), so the client should
  confirm the limit.
- Polish customers still get Europe/Dublin times (R15).
- Date format DD/MM/YYYY and the wording are assumed. One wording is used for
  both reminders, because a 48h reminder clamped to now would make "in 2
  hours" false.
- A 48h reminder sent late (inside the last 2h) is still sent.
- The 2h reminder is built and handled first. If its point is past, it is dropped.
- Tests (test_reminders.py) were not produced or run in this reply.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
_SIG_DEFAULT = "Siobh\u00e1n N\u00ed Dhuibhir"
_SIG_PL = "Grzegorz Szcza\u0144ski"
_SIG_PL = "Grzegorz Szczepa\u0144ski"
# (label, hours before, sort order). 2h is listed first so it is handled first.
_KINDS = (("2h", 2, 1), ("48h", 48, 0))


def _is_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _at(local_date, hour):
    return datetime(local_date.year, local_date.month, local_date.day, hour,
                    tzinfo=DUBLIN)


def _shift_for_quiet_hours(t, now, starts_at):
    """Return the adjusted send time, or None if the reminder must be dropped."""
    local = t.astimezone(DUBLIN)
    if not _is_quiet(local):
        return t
    day = local.date()
    if local.hour < 8:
        day = day - timedelta(days=1)
    back = _at(day, 20)
    if back >= now:
        return back
    fwd_day = local.date() + (timedelta(days=1) if local.hour >= 21 else timedelta(0))
    fwd = _at(fwd_day, 8)
    if fwd < starts_at:
        return fwd
    return None


def _choose_channel(phone, optout):
    return "sms" if (phone and str(phone).strip() and not optout) else "email"


def _signature(country):
    if str(country or "").strip().upper() == "PL":
        return _SIG_PL
    return _SIG_DEFAULT


def _name_candidates(name):
    name = " ".join(str(name or "").split())
    if not name:
        return [""]
    first = name.split(" ")[0]
    cands = [name, first]
    cands += [first[:n] + "." for n in range(len(first) - 1, 1, -1)]
    cands.append(first[0] + ".")
    cands.append("")
    return cands


def _build_text(name, starts_local, signature, channel):
    when = "on %s at %s" % (starts_local.strftime("%d/%m/%Y"),
                            starts_local.strftime("%H:%M"))
    text = ""
    for cand in _name_candidates(name):
        greeting = "Hi %s," % cand if cand else "Hi,"
        text = "%s reminder: your Brennan Opticians appointment is %s. %s" % (
            greeting, when, signature)
        if channel == "email" or len(text) <= SMS_LIMIT:
            return text
    return text


def _plan_one(appt, now):
    """Return list of (send_at, appointment_id, order, channel, text)."""
    aid = appt["id"]
    if aid is None:
        raise ValueError("missing id")
    starts_at = appt["starts_at"]
    if not isinstance(starts_at, datetime) or starts_at.utcoffset() is None:
        raise ValueError("bad starts_at")
    if str(appt.get("status") or "").strip().lower() == "cancelled":
        return []
    optout = appt.get("optout_sms_v2")
    if optout is None:
        logger.warning("optout_sms_v2 missing for appointment %s; treating as opted out", aid)
        optout = True
    if now >= starts_at:
        return []
    phone = appt.get("phone")
    channel = _choose_channel(phone, optout)
    if channel == "email" and not str(appt.get("email") or "").strip():
        logger.warning("no usable contact for appointment %s; skipping", aid)
        return []
    text = _build_text(appt.get("customer_name"), starts_at.astimezone(DUBLIN),
                       _signature(appt.get("country")), channel)
    contact_kind = "phone" if channel == "sms" else "email"
    out = []
    for label, hours, order in _KINDS:
        raw = starts_at.astimezone(ZoneInfo("UTC")) - timedelta(hours=hours)
        if label == "48h":
            raw = max(raw, now)
        elif raw < now:
            logger.info("2h reminder for appointment %s already past; dropped", aid)
            continue
        sent = _shift_for_quiet_hours(raw, now, starts_at)
        if sent is None or sent < now:
            logger.warning("dropping %s reminder for appointment %s (quiet hours)", label, aid)
            continue
        logger.info("planned %s reminder for appointment %s via %s (contact: %s)",
                    label, aid, channel, contact_kind)
        out.append((sent.astimezone(DUBLIN), aid, order, channel, text))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for appt in appointments:
        try:
            planned.extend(_plan_one(appt, now))
        except Exception:
            aid = appt.get("id") if isinstance(appt, dict) else None
            logger.warning("skipping malformed appointment %s", aid)
    planned.sort(key=lambda p: (p[0].astimezone(ZoneInfo("UTC")), str(p[1]), p[2]))
    return [{"appointment_id": aid, "channel": ch, "send_at": t, "text": txt}
            for t, aid, _o, ch, txt in planned]