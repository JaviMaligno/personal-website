"""Appointment reminder planner (stdlib only).

Requirement IDs (R1..R18) are kept in comments.

Design decisions
D1. Per reminder: nominal time (start-48h / start-2h); reminder 1 uses `now`
    if nominal < now (R6); then the quiet window (21:00 inclusive to 08:00
    exclusive, Europe/Dublin) shifts the time back to 20:00 (R11). If that is
    < now (R7), defer FORWARD to 08:00 local, only if that is strictly before
    the start (and, for reminder 1, before reminder 2's send time); else drop.
    Reminder 2 is never dropped in favour of reminder 1 (R15).
D2. Reminder 1 at `now` inside the quiet window is deferred to 08:00 per D1.
D3. If reminder 1's send_at >= reminder 2's, reminder 1 is dropped (R15).
D4. Appointments with starts_at <= now get nothing. A reminder 2 whose time
    is already past (and is not in the quiet window) is omitted.
D5. Naive `now` raises ValueError. Bad appointments (naive/missing starts_at,
    missing id) are skipped with a warning (id only).
D6. SMS if phone is non-blank and not opted out, else email. No usable
    contact -> skip with warning. Opt-out truthy: True/"true"/"1"/"yes".
D7. Only cancelled/canceled is excluded.
D8. SMS shortening ladder: full name -> first name -> initial + "." -> no
    name, then shorter filler wording. Date, time and signature always kept.
D9. Inputs are never mutated.

Logging (R13 vs house rule): one INFO line is logged per planned reminder
with appointment id, channel, the contact field used ("phone" or "email") and
send time. Actual email addresses, phone numbers and names are never logged,
so support can trace deliveries by appointment id.

Time handling (R16): all arithmetic and comparisons are done in UTC (same-tzinfo
aware datetimes compare/add by wall clock, which is not DST safe); wall-clock
rules use ZoneInfo("Europe/Dublin"); results are returned in Europe/Dublin.
"""
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")  # R16
UTC = timezone.utc
SMS_LIMIT = 160  # R10
_TRUE = {"true", "1", "yes"}


def _local(dt):
    return dt.astimezone(DUBLIN)


def _at(day, hour):
    """Dublin wall-clock `hour`:00 on `day`, as UTC (20:00/08:00 are DST safe)."""
    return datetime.combine(day, time(hour), tzinfo=DUBLIN).astimezone(UTC)


def _quiet(dt):  # R11
    h = _local(dt).hour
    return h >= 21 or h < 8


def _shift_back(dt):  # R11
    loc = _local(dt)
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    return _at(day, 20)


def _defer(dt):  # D1
    loc = _local(dt)
    day = loc.date() if loc.hour < 8 else loc.date() + timedelta(days=1)
    return _at(day, 8)


def _truthy(v):  # R3, D6
    if v is True:
        return True
    return v is not None and str(v).strip().lower() in _TRUE


def _s(v):
    return v.strip() if isinstance(v, str) else ""


def _signature(appt):  # R14
    if _s(appt.get("country")).upper() == "PL":
        return "Grzegorz Szczepański"
    return "Chevonne Nee Divver"


def _text(n, name, date_s, time_s, sig, sms):  # R4, R10, D8
    def build(greet):
        if n == 1:
            return f"{greet} reminder: your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"
        return f"{greet} see you in 2 hours! Your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"

    parts = name.split()
    if not sms:
        return build(f"Hi {name}," if name else "Hi,")
    cands = []
    if name:
        cands.append(name)
        cands.append(parts[0])
        cands.append(parts[0][0] + ".")
    for c in cands:
        t = build(f"Hi {c},")
        if len(t) <= SMS_LIMIT:
            return t
    t = build("Hi,")
    if len(t) <= SMS_LIMIT:
        return t
    return f"Appt {date_s} {time_s}. {sig}"  # shorter filler, keeps date/time/sig


def _plan_one(appt, now):
    aid = appt.get("id")
    start = appt.get("starts_at")
    if aid is None or not isinstance(start, datetime) or start.tzinfo is None \
            or start.utcoffset() is None:
        logger.warning("skipping appointment %s: invalid id or starts_at", aid)
        return []
    status = _s(appt.get("status")).lower()
    if status in ("cancelled", "canceled"):  # R12
        logger.info("appointment %s skipped: cancelled", aid)
        return []
    start = start.astimezone(UTC)
    if start <= now:  # D4
        logger.info("appointment %s skipped: already started", aid)
        return []

    phone, email = _s(appt.get("phone")), _s(appt.get("email"))
    if phone and not _truthy(appt.get("optout_sms_v2")):  # R3, R8
        channel, field = "sms", "phone"
    elif email:
        channel, field = "email", "email"
    else:
        logger.warning("skipping appointment %s: no usable contact", aid)
        return []

    loc = _local(start)
    date_s, time_s = loc.strftime("%d/%m/%Y"), loc.strftime("%H:%M")
    sig = _signature(appt)
    name = _s(appt.get("customer_name"))

    # Reminder 2 (R15: priority)
    r2 = None
    nominal2 = start - timedelta(hours=2)
    if _quiet(nominal2):
        back = _shift_back(nominal2)
        if back >= now:
            r2 = back
        else:
            fwd = _defer(nominal2)
            if now <= fwd < start:
                r2 = fwd
    elif nominal2 >= now:
        r2 = nominal2

    # Reminder 1 (R5, R6)
    r1 = max(start - timedelta(hours=48), now)
    if _quiet(r1):
        back = _shift_back(r1)
        if back >= now:
            r1 = back
        else:
            fwd = _defer(r1)
            r1 = fwd if fwd >= now else None
    if r1 is not None:
        limit = r2 if r2 is not None else start
        if not (r1 < limit):  # D1, D3
            r1 = None

    out = []
    for n, when in ((1, r1), (2, r2)):
        if when is None or when < now:  # R7
            logger.info("appointment %s reminder %d dropped", aid, n)
            continue
        out.append((n, when))
    result = []
    for n, when in out:
        logger.info("reminder planned: appointment=%s reminder=%d channel=%s contact_field=%s send_at=%s",
                    aid, n, channel, field, when.isoformat())
        result.append((n, {
            "appointment_id": aid,
            "channel": channel,  # R9
            "send_at": _local(when),
            "text": _text(n, name, date_s, time_s, sig, channel == "sms"),
        }, when))
    return result


def plan_reminders(appointments, now):
    """R1: return planned reminders sorted by send_at (R17)."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    items = []
    for appt in appointments or []:
        if not isinstance(appt, dict):
            logger.warning("skipping non-dict appointment")
            continue
        items.extend(_plan_one(appt, now))
    items.sort(key=lambda x: (x[2], str(x[1]["appointment_id"]), x[0]))
    return [d for _, d, _ in items]


# ===================== test_reminders.py =====================
# (save the section below as test_reminders.py)
#
# import copy, logging
# from datetime import datetime, timedelta, timezone
# from zoneinfo import ZoneInfo
# import pytest
# from reminders import plan_reminders
#
# D = ZoneInfo("Europe/Dublin")
# NOW = datetime(2026, 6, 1, 12, 0, tzinfo=D)
# SIG = "Chevonne Nee Divver"
#
# def appt(**kw):
#     a = dict(id="A1", customer_name="Mary Murphy", email="mary@example.com",
#              phone="+353851234567", country="IE", status="confirmed",
#              starts_at=datetime(2026, 6, 10, 14, 0, tzinfo=D), optout_sms_v2=False)
#     a.update(kw)
#     return a
#
# def test_basic():
#     r = plan_reminders([appt()], NOW)
#     assert [x["send_at"] for x in r] == [datetime(2026, 6, 8, 14, tzinfo=D), datetime(2026, 6, 10, 12, tzinfo=D)]
#     for x in r:
#         assert x["channel"] == "sms" and "10/06/2026" in x["text"] and "14:00" in x["text"]
#         assert x["text"].endswith(SIG) and x["send_at"].tzinfo is not None
#
# def test_long_name():
#     r = plan_reminders([appt(customer_name="Maximilian " * 20)], NOW)
#     for x in r:
#         assert len(x["text"]) <= 160 and "14:00" in x["text"] and x["text"].endswith(SIG)
#
# def test_long_name_email_unlimited():
#     r = plan_reminders([appt(customer_name="X" * 200, phone="")], NOW)
#     assert r[0]["channel"] == "email" and "X" * 200 in r[0]["text"]
#
# def test_pl_signature():
#     r = plan_reminders([appt(country=" pl ")], NOW)
#     assert all(x["text"].endswith("Grzegorz Szczepański") for x in r)
#
# def test_dst_march():
#     s = datetime(2026, 3, 30, 10, 0, tzinfo=D)
#     r = plan_reminders([appt(starts_at=s)], datetime(2026, 3, 1, tzinfo=D))
#     assert r[0]["send_at"] == s - timedelta(hours=48)
#     assert r[0]["send_at"].astimezone(timezone.utc).hour == 9
#
# def test_dst_october():
#     s = datetime(2026, 10, 26, 10, 0, tzinfo=D)
#     r = plan_reminders([appt(starts_at=s)], datetime(2026, 10, 1, tzinfo=D))
#     assert r[0]["send_at"].astimezone(D).hour == 11
#     assert r[0]["send_at"].astimezone(timezone.utc) == datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
#
# def test_quiet_morning_goes_back():
#     r = plan_reminders([appt(starts_at=datetime(2026, 6, 10, 9, 0, tzinfo=D))], NOW)
#     assert r[1]["send_at"] == datetime(2026, 6, 9, 20, tzinfo=D)
#
# def test_quiet_21_inclusive():
#     r = plan_reminders([appt(starts_at=datetime(2026, 6, 10, 23, 0, tzinfo=D))], NOW)
#     assert r[0]["send_at"] == datetime(2026, 6, 8, 20, tzinfo=D)
#     assert r[1]["send_at"] == datetime(2026, 6, 10, 20, tzinfo=D)
#
# def test_past_48h_sent_now():
#     now = datetime(2026, 6, 9, 10, 0, tzinfo=D)
#     r = plan_reminders([appt()], now)
#     assert r[0]["send_at"] == now and r[1]["send_at"] == datetime(2026, 6, 10, 12, tzinfo=D)
#
# def test_now_in_quiet_deferred():
#     now = datetime(2026, 6, 9, 22, 0, tzinfo=D)
#     r = plan_reminders([appt()], now)
#     assert r[0]["send_at"] == datetime(2026, 6, 10, 8, tzinfo=D)
#     assert all(x["send_at"] >= now for x in r)
#
# def test_r1_dropped_when_not_before_r2():
#     now = datetime(2026, 6, 9, 22, 0, tzinfo=D)
#     r = plan_reminders([appt(starts_at=datetime(2026, 6, 10, 9, 30, tzinfo=D))], now)
#     assert len(r) == 1 and r[0]["send_at"] == datetime(2026, 6, 10, 8, tzinfo=D)
#
# def test_started_and_close():
#     assert plan_reminders([appt(starts_at=NOW - timedelta(hours=1))], NOW) == []
#     r = plan_reminders([appt(starts_at=NOW + timedelta(hours=1))], NOW)
#     assert len(r) == 1 and r[0]["send_at"] == NOW
#
# @pytest.mark.parametrize("st", ["cancelled", " CANCELED ", "Cancelled"])
# def test_cancelled(st):
#     assert plan_reminders([appt(status=st)], NOW) == []
#
# def test_other_status_reminded():
#     assert len(plan_reminders([appt(status=None)], NOW)) == 2
#
# @pytest.mark.parametrize("v", [True, "true", "1", "YES"])
# def test_optout_email(v):
#     assert {x["channel"] for x in plan_reminders([appt(optout_sms_v2=v)], NOW)} == {"email"}
#
# @pytest.mark.parametrize("p", [None, "", "   "])
# def test_no_phone_email(p):
#     assert {x["channel"] for x in plan_reminders([appt(phone=p)], NOW)} == {"email"}
#
# def test_no_contact_skipped():
#     assert plan_reminders([appt(phone=None, email="")], NOW) == []
#     assert plan_reminders([appt(optout_sms_v2=True, email=None)], NOW) == []
#
# def test_opt_out_ignored():
#     assert plan_reminders([appt(opt_out=True)], NOW)[0]["channel"] == "sms"
#     assert plan_reminders([appt(opt_out=False, optout_sms_v2=True)], NOW)[0]["channel"] == "email"
#
# def test_sorting():
#     a = appt(id="B", starts_at=datetime(2026, 6, 10, 14, tzinfo=D))
#     b = appt(id="A", starts_at=datetime(2026, 6, 10, 14, tzinfo=D))
#     c = appt(id="C", starts_at=datetime(2026, 6, 5, 14, tzinfo=D))
#     r = plan_reminders([a, b, c], NOW)
#     keys = [(x["send_at"].astimezone(timezone.utc), x["appointment_id"]) for x in r]
#     assert keys == sorted(keys)
#     assert [x["appointment_id"] for x in r[2:4]] == ["A", "B"]
#
# def test_naive_now_rejected():
#     with pytest.raises(ValueError):
#         plan_reminders([appt()], datetime(2026, 6, 1, 12))
#
# def test_bad_appointments_skipped():
#     bad = appt(id="N", starts_at=datetime(2026, 6, 10, 14))
#     r = plan_reminders([bad, appt(id=None), appt(id="OK")], NOW)
#     assert {x["appointment_id"] for x in r} == {"OK"}
#
# def test_no_mutation():
#     data = [appt()]
#     snap = copy.deepcopy(data)
#     plan_reminders(data, NOW)
#     assert data == snap
#
# def test_no_pii_in_logs(caplog):
#     with caplog.at_level(logging.DEBUG):
#         plan_reminders([appt(), appt(id="B", phone=None)], NOW)
#     assert caplog.records
#     assert "mary@example.com" not in caplog.text
#     assert "+353851234567" not in caplog.text
#     assert "Mary" not in caplog.text
#     assert "A1" in caplog.text