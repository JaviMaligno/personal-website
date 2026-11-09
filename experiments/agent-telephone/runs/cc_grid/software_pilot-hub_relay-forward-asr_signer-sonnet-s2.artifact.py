"""Brennan Opticians appointment reminder planner.

Standard library only, plus the tzdata package where the OS has no tz database
(declare "tzdata" as a dependency). Tests are included below and run with pytest.

Decisions the client should confirm:
1. If moving a reminder back to 20:00 would put it before now, it moves forward
   to the next 08:00 if that is before the appointment starts, otherwise it is
   dropped (see _late_fallback, the only place this policy lives).
2. A missing or None optout_sms_v2 is treated as opted out (email, not SMS).
   Only an explicit False allows SMS. The legacy opt_out field is never read.
3. If the 2-hour point has already passed, that reminder is sent at now.
   If it then coincides with the 48-hour one, only the 2-hour one is kept.
4. Logging: the house rule asks for the contact in each INFO line, but the
   brief forbids logging email addresses (Data Protection Commission audit).
   The brief wins, so lines carry appointment_id and channel only, with no
   email, phone or name. Support can look the contact up by appointment id.
"""
import copy
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
log = logging.getLogger(__name__)
_DAY = timedelta(days=1)


def _aware(dt):
    if not isinstance(dt, datetime) or dt.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return dt


def _late_fallback(loc, starts):
    """Policy when the move back to 20:00 lands before now: next 08:00 if before start, else None."""
    day = loc.date() if loc.hour < 8 else loc.date() + _DAY
    fwd = datetime.combine(day, time(8), DUBLIN)
    return fwd if fwd < starts else None


def _quiet_hours(t, now, starts):
    loc = t.astimezone(DUBLIN)
    if 8 <= loc.hour < 21:
        return t
    day = loc.date() if loc.hour >= 21 else loc.date() - _DAY
    back = datetime.combine(day, time(20), DUBLIN)
    if back >= now:
        return back
    return _late_fallback(loc, starts)


def _signature(appt):
    country = str(appt.get("country") or "").strip().casefold()
    return "Grzegorz Szczepański" if country == "pl" else "Chevonne Nee Divver"


def _name_ladder(name):
    parts = name.split()
    if not parts:
        return [""]
    out = [name]
    if len(parts) > 1:
        out.append(f"{parts[0]} {parts[-1][0]}.")
    out += [parts[0], f"{parts[0][0]}."]
    out.append("")
    return out


def _text(appt, starts, channel):
    local = starts.astimezone(DUBLIN)
    when = f"{local:%d/%m/%Y} at {local:%H:%M}"
    sig = _signature(appt)
    name = str(appt.get("customer_name") or "").strip()
    candidates = [name] if channel == "email" else _name_ladder(name)
    text = ""
    for n in candidates:
        greet = f"Hi {n}," if n else "Hi,"
        text = f"{greet} reminder: your Brennan Opticians appointment is on {when}. {sig}"
        if channel == "email" or len(text) <= 160:
            break
    return text


def _channel(appt):
    phone = str(appt.get("phone") or "").strip()
    if phone and appt.get("optout_sms_v2") is False:
        return "sms"
    return "email" if str(appt.get("email") or "").strip() else None


def _plan_one(appt, now):
    if str(appt.get("status") or "").strip().casefold() == "cancelled":
        return []
    aid = appt["id"]
    starts = _aware(appt["starts_at"])
    if starts <= now:
        return []
    channel = _channel(appt)
    if channel is None:
        return []
    utc = starts.astimezone(timezone.utc)
    sends = []
    for kind, hours in ((0, 48), (1, 2)):
        t = max(utc - timedelta(hours=hours), now)
        sends.append((kind, _quiet_hours(t, now, starts)))
    sends = [(k, t) for k, t in sends if t is not None]
    if len(sends) == 2 and sends[0][1] == sends[1][1]:
        sends = sends[1:]
    text = _text(appt, starts, channel)
    return [(t.astimezone(timezone.utc), str(aid), k,
             {"appointment_id": aid, "channel": channel,
              "send_at": t.astimezone(DUBLIN), "text": text})
            for k, t in sends]


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    planned = []
    for appt in appointments:
        try:
            planned.extend(_plan_one(appt, now))
        except (KeyError, TypeError, ValueError, AttributeError):
            aid = appt.get("id") if isinstance(appt, dict) else None
            log.warning("skipping invalid appointment id=%s", aid)
    planned.sort(key=lambda p: p[:3])
    for _, _, kind, r in planned:
        log.info("reminder planned appointment_id=%s kind=%s channel=%s send_at=%s",
                 r["appointment_id"], "48h" if kind == 0 else "2h",
                 r["channel"], r["send_at"].isoformat())
    return [p[3] for p in planned]


# ----------------------------- tests (pytest) -----------------------------
UTC = timezone.utc
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def _appt(**kw):
    base = {"id": "a1", "customer_name": "Mary Murphy", "email": "mary@example.com",
            "phone": "+353851234567", "country": "IE", "status": "booked",
            "starts_at": datetime(2026, 11, 10, 14, 0, tzinfo=UTC),
            "optout_sms_v2": False}
    base.update(kw)
    return base


def _at(h, m=0, day=10):
    return datetime(2026, 11, day, h, m, tzinfo=UTC)


def test_basic_two_reminders_and_keys():
    r = plan_reminders([_appt()], NOW)
    assert [x["send_at"] for x in r] == [_at(14, day=8), _at(12)]
    assert all(set(x) == {"appointment_id", "channel", "send_at", "text"} for x in r)
    assert all(x["send_at"].tzinfo is DUBLIN for x in r)
    assert r[0]["text"] == ("Hi Mary Murphy, reminder: your Brennan Opticians appointment "
                            "is on 10/11/2026 at 14:00. Chevonne Nee Divver")


def test_dst_end_exact_hours():
    starts = datetime(2026, 10, 26, 10, 0, tzinfo=DUBLIN)
    r = plan_reminders([_appt(starts_at=starts)], datetime(2026, 10, 20, tzinfo=UTC))
    assert r[0]["send_at"] == datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
    assert r[0]["send_at"].hour == 11


def test_summer_display_time():
    starts = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    r = plan_reminders([_appt(starts_at=starts)], datetime(2026, 6, 1, tzinfo=UTC))
    assert "01/07/2026 at 13:00" in r[0]["text"]


def test_quiet_hours_boundaries():
    assert plan_reminders([_appt(starts_at=_at(23))], NOW)[-1]["send_at"] == _at(20)
    assert plan_reminders([_appt(starts_at=_at(22, 59))], NOW)[-1]["send_at"] == _at(20)
    assert plan_reminders([_appt(starts_at=_at(10))], NOW)[-1]["send_at"] == _at(8)
    assert plan_reminders([_appt(starts_at=_at(9, 59))], NOW)[-1]["send_at"] == _at(20, day=9)
    assert plan_reminders([_appt(starts_at=_at(22, 59))], NOW)[-1]["send_at"] == _at(20)
    assert plan_reminders([_appt(starts_at=_at(23))], NOW)[-1]["send_at"] == _at(20)
    assert plan_reminders([_appt(starts_at=_at(22, 59))], NOW)[-1]["send_at"] == _at(20)
    assert plan_reminders([_appt(starts_at=_at(21, 0))], NOW)[-1]["send_at"] == _at(19)


def test_quiet_forward_and_drop_and_coincide():
    now = _at(7)
    r = plan_reminders([_appt(starts_at=_at(9, 30))], now)
    assert [x["send_at"] for x in r] == [_at(8)]
    assert plan_reminders([_appt(starts_at=_at(7, 30))], now) == []


def test_past_and_cancelled():
    assert plan_reminders([_appt(starts_at=NOW)], NOW) == []
    assert plan_reminders([_appt(status=" CancelLed ")], NOW) == []
    r = plan_reminders([_appt(starts_at=_at(14, day=2))], NOW)
    assert r[0]["send_at"] == NOW and all(x["send_at"] >= NOW for x in r)


def test_channels():
    assert plan_reminders([_appt()], NOW)[0]["channel"] == "sms"
    assert plan_reminders([_appt(optout_sms_v2=True)], NOW)[0]["channel"] == "email"
    assert plan_reminders([_appt(optout_sms_v2=None)], NOW)[0]["channel"] == "email"
    no_flag = _appt()
    del no_flag["optout_sms_v2"]
    assert plan_reminders([no_flag], NOW)[0]["channel"] == "email"
    assert plan_reminders([_appt(phone="  ")], NOW)[0]["channel"] == "email"
    assert plan_reminders([_appt(optout_sms_v2=True, email=" ")], NOW) == []
    assert plan_reminders([_appt(opt_out=True)], NOW)[0]["channel"] == "sms"
    assert len({x["channel"] for x in plan_reminders([_appt(optout_sms_v2=True)], NOW)}) == 1


def test_length_ladder_and_email_unshortened():
    long1 = "A" * 30 + " " + "B" * 60
    t = plan_reminders([_appt(customer_name=long1)], NOW)[0]["text"]
    assert t.startswith("Hi " + "A" * 30 + " B., reminder") and len(t) <= 160
    long2 = "A" * 70 + " BBBBB"
    t = plan_reminders([_appt(customer_name=long2)], NOW)[0]["text"]
    assert t.startswith("Hi A., reminder") and "10/11/2026 at 14:00" in t and len(t) <= 160
    mid = "A" * 50 + " " + "B" * 20
    t = plan_reminders([_appt(customer_name=mid)], NOW)[0]["text"]
    assert t.startswith("Hi " + "A" * 50 + " B.,") and len(t) <= 160
    t = plan_reminders([_appt(customer_name=long1, optout_sms_v2=True)], NOW)[0]["text"]
    assert long1 in t and len(t) > 160


def test_signature():
    t = plan_reminders([_appt(country=" pl ")], NOW)[0]["text"]
    assert t.endswith("Grzegorz Szczepański")
    assert plan_reminders([_appt(country="IE")], NOW)[0]["text"].endswith("Chevonne Nee Divver")


def test_sorting_and_no_mutation():
    appts = [_appt(id="b", starts_at=_at(15)), _appt(id="a", starts_at=_at(15)),
             _appt(id="c", starts_at=_at(9, 59, day=20))]
    before = copy.deepcopy(appts)
    r = plan_reminders(appts, NOW)
    assert appts == before
    keys = [(x["send_at"].astimezone(UTC), x["appointment_id"]) for x in r]
    assert keys == sorted(keys)
    assert [x["appointment_id"] for x in r[:2]] == ["a", "b"]


def test_errors_and_bad_appointment(caplog):
    import pytest
    with pytest.raises(ValueError):
        plan_reminders([], datetime(2026, 11, 1))
    bad = _appt(id="bad", starts_at=datetime(2026, 11, 10, 14))
    with caplog.at_level(logging.INFO):
        r = plan_reminders([bad, _appt(id="ok")], NOW)
    assert {x["appointment_id"] for x in r} == {"ok"}
    assert "bad" in caplog.text


def test_logging_no_pii(caplog):
    with caplog.at_level(logging.INFO):
        r = plan_reminders([_appt(optout_sms_v2=True)], NOW)
    infos = [x for x in caplog.records if x.levelno == logging.INFO]
    assert len(infos) == len(r) == 2
    for needle in ("mary@example.com", "+353851234567", "Mary", "Murphy"):
        assert needle not in caplog.text
    assert "a1" in caplog.text and "email" in caplog.text