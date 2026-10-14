"""plan_reminders: plan SMS and email appointment reminders for Brennan Opticians.

Module path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-gv_tzkaz/plan_reminders.py

Status: written without the ability to execute code. The self-check has NOT been run.
Run it from outside the module directory with:
    python3 -I -c "import sys; sys.path.insert(0, '/private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-gv_tzkaz'); import plan_reminders; plan_reminders._self_check()"

Open items and conflicts for client or architect sign-off:
- R6 vs R9: when a shifted candidate lands before now and now is in quiet hours, the send moves to the first 08:00 Dublin after now (R25c). Implemented as stated.
- House logging rule asks for recipient contact in each INFO line. R12 and R34 forbid logging contact data, so R12 and R34 win. Logs carry appointment id and channel only.
- TWO_HOUR_OFFSET (2 hours) is unconfirmed with the client.
- The 160 limit is counted in Python characters. The signature contains a/o/n with acute accents, which are outside GSM-7, so SMS is UCS-2 at 70 characters per segment. Unresolved.
- "Preceding evening" for candidates at 21:00 to 23:59 is taken as 20:00 of the same calendar day (R25b).
- Statuses no_show and completed receive reminders under R22. Client to confirm.
- No email subject is produced because the return schema has no subject key. Client to confirm.
- PL customers get the English template with the PL signature. Client to confirm body language.
- Phone format (E.164) is not validated.
- Appointments with no phone and an email receive an email reminder under R21. Client to confirm.
- Template wording and the "Brennan Opticians" name are assumptions for sign-off.
- Name truncation tries k from len(name)-1 down to 1. If none fits, the nameless text is used. Client to confirm.
- Manual follow-up for oversized SMS is signalled only by a WARNING log line, because the return schema has no field for it.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
TWO_HOUR_OFFSET = timedelta(hours=2)
FORTY_EIGHT_HOUR_OFFSET = timedelta(hours=48)
SMS_MAX_CHARS = 160
ELLIPSIS = "..."
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
SEND_DAY_START = time(8, 0)
EVENING_SHIFT = time(20, 0)


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _clean(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _opted_out(value):
    if value is True:
        return True
    return isinstance(value, str) and value.strip().casefold() == "true"


def _is_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _dublin_at(day, t):
    return datetime.combine(day, t, tzinfo=DUBLIN).astimezone(UTC)


def _quiet_shift(candidate):
    local = candidate.astimezone(DUBLIN)
    if not _is_quiet(local):
        return candidate
    if local.hour >= 21:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    return _dublin_at(day, EVENING_SHIFT)


def _next_window_start(now):
    local = now.astimezone(DUBLIN)
    if local.hour < 8:
        day = local.date()
    else:
        day = local.date() + timedelta(days=1)
    return _dublin_at(day, SEND_DAY_START)


def _schedule(nominal, now):
    candidate = nominal if nominal >= now else now
    shifted = _quiet_shift(candidate)
    if shifted < now:
        if _is_quiet(now.astimezone(DUBLIN)):
            shifted = _next_window_start(now)
        else:
            shifted = now
    return shifted


def _message(name, starts_local, signature):
    date_s = f"{starts_local.day:02d}/{starts_local.month:02d}/{starts_local.year:04d}"
    time_s = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    tail = f"your Brennan Opticians appointment is on {date_s} at {time_s}. {signature}"
    if name:
        return f"Hello {name}, reminder: {tail}"
    return f"Hello, reminder: {tail}"


def _sms_text(name, starts_local, signature):
    full = _message(name, starts_local, signature)
    if len(full) <= SMS_MAX_CHARS:
        return full
    for k in range(len(name) - 1, 0, -1):
        candidate = _message(name[:k] + ELLIPSIS, starts_local, signature)
        if len(candidate) <= SMS_MAX_CHARS:
            return candidate
    bare = _message("", starts_local, signature)
    return bare if len(bare) <= SMS_MAX_CHARS else None


def _plan_one(appt, now):
    aid = appt.get("id")
    starts = appt.get("starts_at")
    if not _is_aware(starts):
        raise ValueError(f"appointment {aid}: starts_at must be an aware datetime")
    starts_utc = starts.astimezone(UTC)

    status = appt.get("status")
    if isinstance(status, str) and status.strip().casefold() == "cancelled":
        logger.info("appointment %s: no reminders (cancelled)", aid)
        return []
    if starts_utc <= now:
        logger.info("appointment %s: no reminders (past_start)", aid)
        return []

    phone = _clean(appt.get("phone"))
    email = _clean(appt.get("email"))
    opted_out = _opted_out(appt.get("optout_sms_v2"))
    if opted_out and phone is None:
        channel = None
    elif phone is not None and not opted_out:
        channel = "sms"
    elif email is not None:
        channel = "email"
    else:
        channel = None
    if channel is None:
        logger.info("appointment %s: no reminders (no_channel)", aid)
        return []

    raw_name = appt.get("customer_name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    country = appt.get("country")
    signature = SIGNATURE_PL if isinstance(country, str) and country.strip() == "PL" else SIGNATURE
    starts_local = starts_utc.astimezone(DUBLIN)

    if channel == "sms":
        text = _sms_text(name, starts_local, signature)
        if text is None:
            logger.warning("appointment %s: sms_too_long, manual follow-up required", aid)
            return []
    else:
        text = _message(name, starts_local, signature)

    plans = {}
    for label, nominal in (
        ("48h", starts_utc - FORTY_EIGHT_HOUR_OFFSET),
        ("2h", starts_utc - TWO_HOUR_OFFSET),
    ):
        send = _schedule(nominal, now)
        if send >= starts_utc:
            logger.info("appointment %s: %s reminder dropped (at_or_after_start)", aid, label)
            continue
        plans[label] = send

    if "48h" in plans and "2h" in plans and plans["48h"] >= plans["2h"]:
        logger.info("appointment %s: duplicate_48h_suppressed", aid)
        del plans["48h"]

    results = []
    for label in ("48h", "2h"):
        if label not in plans:
            continue
        logger.info("appointment %s: planned %s reminder via %s", aid, label, channel)
        results.append({
            "appointment_id": aid,
            "channel": channel,
            "send_at": plans[label].astimezone(UTC),
            "text": text,
        })
    return results


def plan_reminders(appointments, now):
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list")
    if not _is_aware(now):
        raise ValueError("now must be an aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        if not isinstance(appt, dict):
            raise ValueError("each appointment must be a dict")
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


def _self_check():
    def appt(**overrides):
        base = {
            "id": "A1",
            "customer_name": "Anna Murphy",
            "email": "anna@example.com",
            "phone": "+353861234567",
            "country": "IE",
            "status": "booked",
            "starts_at": datetime(2026, 10, 20, 14, 0, tzinfo=UTC),
            "optout_sms_v2": None,
        }
        base.update(overrides)
        return base

    def sends(rows):
        return [r["send_at"] for r in rows]

    now = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)

    rows = plan_reminders([appt()], now)
    assert sends(rows) == [datetime(2026, 10, 18, 14, 0, tzinfo=UTC),
                           datetime(2026, 10, 20, 12, 0, tzinfo=UTC)]
    assert all(r["channel"] == "sms" for r in rows)
    assert "on 20/10/2026 at 15:00." in rows[0]["text"]

    rows = plan_reminders([appt()], datetime(2026, 10, 19, 10, 0, tzinfo=UTC))
    assert sends(rows) == [datetime(2026, 10, 19, 10, 0, tzinfo=UTC),
                           datetime(2026, 10, 20, 12, 0, tzinfo=UTC)]

    rows = plan_reminders([appt()], datetime(2026, 10, 20, 13, 0, tzinfo=UTC))
    assert sends(rows) == [datetime(2026, 10, 20, 13, 0, tzinfo=UTC)]

    rows = plan_reminders([appt(starts_at=datetime(2026, 10, 20, 8, 0, tzinfo=UTC))], now)
    assert sends(rows) == [datetime(2026, 10, 18, 8, 0, tzinfo=UTC),
                           datetime(2026, 10, 19, 19, 0, tzinfo=UTC)]
    assert "at 09:00." in rows[1]["text"]

    rows = plan_reminders([appt(starts_at=datetime(2026, 10, 14, 9, 0, tzinfo=UTC))],
                          datetime(2026, 10, 13, 21, 0, tzinfo=UTC))
    assert sends(rows) == [datetime(2026, 10, 14, 7, 0, tzinfo=UTC)]

    assert plan_reminders([appt(status=" Cancelled ")], now) == []

    rows = plan_reminders([appt(optout_sms_v2=" TRUE ")], now)
    assert len(rows) == 2 and all(r["channel"] == "email" for r in rows)
    assert plan_reminders([appt(optout_sms_v2=True, email=None)], now) == []

    rows = plan_reminders([appt(country="PL")], now)
    assert all(r["text"].endswith("Grzegorz Szczepański") for r in rows)

    rows = plan_reminders([appt(customer_name="A" * 200)], now)
    assert rows and all(r["channel"] == "sms" for r in rows)
    assert all(len(r["text"]) <= SMS_MAX_CHARS for r in rows)
    assert all(r["text"].endswith(SIGNATURE) and "..." in r["text"] for r in rows)
    assert all("20/10/2026 at 15:00" in r["text"] for r in rows)

    summer = plan_reminders(
        [appt(starts_at=datetime(2026, 7, 1, 11, 0, tzinfo=UTC))],
        datetime(2026, 6, 1, 0, 0, tzinfo=UTC))
    assert datetime(2026, 7, 1, 9, 0, tzinfo=UTC) in sends(summer)
    assert "on 01/07/2026 at 12:00." in summer[0]["text"]

    winter = plan_reminders(
        [appt(starts_at=datetime(2026, 12, 1, 12, 0, tzinfo=UTC))],
        datetime(2026, 11, 1, 0, 0, tzinfo=UTC))
    assert datetime(2026, 12, 1, 10, 0, tzinfo=UTC) in sends(winter)
    assert "on 01/12/2026 at 12:00." in winter[0]["text"]

    print("self-check ok")


if __name__ == "__main__":
    _self_check()