"""Brennan Opticians appointment reminders (stdlib only, Python 3.12).

Public entry point: plan_reminders(appointments, now).

Tests (pytest) are included at the bottom of this module. Run with:
    pytest -q <path to this file>

Notes and assumptions:
- Required appointment fields: id and starts_at. Others degrade gracefully.
  An appointment missing a required field is skipped and logged by id only.
- The required "who and how" INFO log uses a masked contact: SMS shows the
  last 2 digits of the phone, email shows only "email on file". The email
  address is never logged (R10).
- optout_sms_v2 is honoured only when it is exactly True (strings such as
  "true" are not accepted); confirm the CRM sends real booleans.
- Naive starts_at raises ValueError even for cancelled appointments.
"""
import logging
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo

_log = logging.getLogger("brennan.reminders")
_DUBLIN = ZoneInfo("Europe/Dublin")
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SMS_LIMIT = 160
_SLOTS = ((timedelta(hours=48), 0), (timedelta(hours=2), 1))


def _sms_flag_allows(appt):
    # NOTE: the flag name "optout_sms_v2" reads like an opt-out, yet the
    # client's literal wording is "SMS if phone AND optout_sms_v2 is true".
    # Implemented exactly as stated; confirm with the client. To flip, change
    # this one helper to `return appt.get("optout_sms_v2") is not True`.
    return appt.get("optout_sms_v2") is True


def _clean(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _channel(appt):
    """Return (channel, masked_contact) or None. Never reads legacy opt_out."""
    phone = _clean(appt.get("phone"))
    if phone:
        if _sms_flag_allows(appt):
            return "sms", "phone ***" + phone[-2:]
        return None
    if _clean(appt.get("email")):
        return "email", "email on file"
    return None


def _signature(appt):
    country = appt.get("country")
    if isinstance(country, str) and country.strip().casefold() == "pl":
        return _SIG_PL
    return _SIG_DEFAULT


def _name_variants(name):
    name = " ".join(str(name or "").split())
    if not name:
        return [""]
    first = name.split()[0]
    out = []
    for v in (name, first, first[0].upper() + ".", ""):
        if v not in out:
            out.append(v)
    return out


def _render(name, start_local, sig):
    when = (f"{_DAYS[start_local.weekday()]} {start_local.day} "
            f"{_MONTHS[start_local.month - 1]} {start_local.year}")
    greeting = f"Hi {name}," if name else "Hi,"
    return (f"{greeting} your Brennan Opticians appointment is on {when} "
            f"at {start_local:%H:%M}. {sig}")


def _compose(appt_id, name, start_local, sig, channel):
    variants = _name_variants(name)
    if channel != "sms":
        return _render(variants[0], start_local, sig)
    for v in variants:
        text = _render(v, start_local, sig)
        if len(text) <= _SMS_LIMIT:
            return text
    raise ValueError(f"SMS text for appointment {appt_id} exceeds "
                     f"{_SMS_LIMIT} characters even without a name")


def _adjust(t, now, start):
    """Apply quiet hours (21:00 <= t < 08:00 blocked). None means drop."""
    loc = t.astimezone(_DUBLIN)
    if 8 <= loc.hour < 21:
        return loc
    day = loc.date()
    if loc.hour < 8:
        back_day, fwd_day = day - timedelta(days=1), day
    else:
        back_day, fwd_day = day, day + timedelta(days=1)
    back = datetime.combine(back_day, time(20, 0), _DUBLIN)
    if back >= now:
        return back
    fwd = datetime.combine(fwd_day, time(8, 0), _DUBLIN)
    return fwd if fwd < start else None


def plan_reminders(appointments, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    planned = []
    for appt in appointments:
        appt_id = appt.get("id")
        starts = appt.get("starts_at")
        if appt_id in (None, "") or not isinstance(starts, datetime):
            _log.warning("Skipping appointment %s: missing required fields",
                         appt_id)
            continue
        if starts.tzinfo is None or starts.utcoffset() is None:
            raise ValueError(f"starts_at must be timezone-aware "
                             f"(appointment {appt_id})")
        status = appt.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            continue
        if starts <= now:
            continue
        chan = _channel(appt)
        if chan is None:
            continue
        channel, contact = chan
        start_local = starts.astimezone(_DUBLIN)
        text = _compose(appt_id, appt.get("customer_name"), start_local,
                        _signature(appt), channel)
        start_utc = starts.astimezone(timezone.utc)
        for delta, slot in _SLOTS:
            t = (start_utc - delta).astimezone(_DUBLIN)
            if t < now:
                if slot == 0:
                    t = now.astimezone(_DUBLIN)
                else:
                    continue
            send_at = _adjust(t, now, starts)
            if send_at is None:
                continue
            planned.append((send_at, str(appt_id), slot, {
                "appointment_id": appt_id, "channel": channel,
                "send_at": send_at, "text": text}))
    planned.sort(key=lambda p: p[:3])
    result = [p[3] for p in planned]
    for r in result:
        _log.info("Reminder planned: appointment=%s channel=%s contact=%s "
                  "send_at=%s", r["appointment_id"], r["channel"],
                  _channel_contact(appointments, r), r["send_at"].isoformat())
    return result


def _channel_contact(appointments, reminder):
    for a in appointments:
        if a.get("id") == reminder["appointment_id"]:
            chan = _channel(a)
            if chan:
                return chan[1]
    return "unknown"


# ----------------------------- tests (pytest) -----------------------------
def _dub(*a):
    return datetime(*a, tzinfo=_DUBLIN)


def _appt(**kw):
    base = {"id": "A1", "customer_name": "Mary Murphy", "email": "secret@example.com",
            "phone": "+353851234567", "country": "IE", "status": "booked",
            "starts_at": _dub(2026, 10, 20, 14, 0), "optout_sms_v2": True}
    base.update(kw)
    return base


_NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def test_two_hour_reminder_and_text():
    out = plan_reminders([_appt()], _NOW)
    assert [o["send_at"] for o in out] == [_dub(2026, 10, 18, 14, 0),
                                           _dub(2026, 10, 20, 12, 0)]
    assert set(out[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert "Tue 20 Oct 2026 at 14:00" in out[1]["text"]
    assert out[1]["text"].endswith("Siobhán Ní Dhuibhir")


def test_optout_v2_only_contradictory_values():
    a = _appt(optout_sms_v2=False, opt_out=True)
    assert plan_reminders([a], _NOW) == []  # phone but flag false: nothing
    b = _appt(optout_sms_v2=True, opt_out=False)
    assert {o["channel"] for o in plan_reminders([b], _NOW)} == {"sms"}
    c = _appt(optout_sms_v2=True, opt_out=True)
    assert plan_reminders([c], _NOW)


def test_email_fallback_and_missing_contacts():
    out = plan_reminders([_appt(phone="")], _NOW)
    assert {o["channel"] for o in out} == {"email"}
    assert plan_reminders([_appt(phone=None, email="")], _NOW) == []
    assert plan_reminders([_appt(phone=None, email=None)], _NOW) == []


def test_cancelled_past_and_unknown_status():
    assert plan_reminders([_appt(status="cancelled")], _NOW) == []
    assert plan_reminders([_appt(starts_at=_dub(2026, 9, 1, 10))], _NOW) == []
    assert plan_reminders([_appt(status="weird")], _NOW)
    assert plan_reminders([], _NOW) == []


def test_naive_raises():
    import pytest
    with pytest.raises(ValueError):
        plan_reminders([], datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 14))], _NOW)


def test_missing_required_skipped():
    assert plan_reminders([{"phone": "1"}, _appt(starts_at=None)], _NOW) == []


def test_48h_passed_sent_now_and_2h_dropped():
    now = _dub(2026, 10, 19, 10, 0)
    out = plan_reminders([_appt()], now)
    assert out[0]["send_at"] == now and len(out) == 2
    now2 = _dub(2026, 10, 20, 13, 0)
    out2 = plan_reminders([_appt()], now2)
    assert [o["send_at"] for o in out2] == [now2]


def test_dst_spring_forward():
    a = _appt(starts_at=_dub(2026, 3, 29, 10, 0))
    out = plan_reminders([a], datetime(2026, 3, 1, tzinfo=timezone.utc))
    assert out[0]["send_at"].hour == 9  # 48h elapsed crosses the change
    assert out[0]["send_at"].utcoffset() == timedelta(0)
    assert out[1]["send_at"] == _dub(2026, 3, 29, 8, 0)


def test_dst_fall_back():
    a = _appt(starts_at=_dub(2026, 10, 25, 10, 0))
    out = plan_reminders([a], _NOW)
    assert out[0]["send_at"].hour == 11
    assert out[0]["send_at"].utcoffset() == timedelta(hours=1)
    assert out[1]["send_at"] == _dub(2026, 10, 25, 8, 0)


def test_quiet_hours_move_back_and_boundaries():
    a = _appt(starts_at=_dub(2026, 10, 20, 9, 0))  # 2h point = 07:00
    out = plan_reminders([a], _NOW)
    assert out[1]["send_at"] == _dub(2026, 10, 19, 20, 0)
    b = _appt(starts_at=_dub(2026, 10, 20, 10, 0))  # 2h point = 08:00 allowed
    assert plan_reminders([b], _NOW)[1]["send_at"] == _dub(2026, 10, 20, 8, 0)
    c = _appt(starts_at=_dub(2026, 10, 20, 23, 0))  # 2h point = 21:00 blocked
    assert plan_reminders([c], _NOW)[1]["send_at"] == _dub(2026, 10, 20, 20, 0)


def test_quiet_hours_defer_forward_or_drop():
    a = _appt(starts_at=_dub(2026, 10, 20, 9, 0))
    out = plan_reminders([a], _dub(2026, 10, 19, 20, 30))
    assert out[-1]["send_at"] == _dub(2026, 10, 20, 8, 0)
    b = _appt(starts_at=_dub(2026, 10, 20, 7, 50))
    assert plan_reminders([b], _dub(2026, 10, 19, 21, 30)) == []


def test_sms_length_shortening_and_pl_signature():
    long_name = "Bartholomew" * 20 + " Smith"
    out = plan_reminders([_appt(customer_name=long_name, country="pl")], _NOW)
    for o in out:
        assert len(o["text"]) <= 160
        assert o["text"].endswith("Grzegorz Szczepański")
        assert "20 Oct 2026" in o["text"] and "14:00" in o["text"]
    em = plan_reminders([_appt(customer_name=long_name, phone=None)], _NOW)
    assert long_name in em[0]["text"]


def test_sorting_ties_and_no_mutation():
    import copy
    appts = [_appt(id="B"), _appt(id="A")]
    snap = copy.deepcopy(appts)
    out = plan_reminders(appts, _NOW)
    assert appts == snap
    keys = [(o["send_at"], str(o["appointment_id"])) for o in out]
    assert keys == sorted(keys)


def test_email_never_logged(caplog):
    caplog.set_level(logging.DEBUG)
    plan_reminders([_appt(phone=None), _appt(id="X", starts_at=None),
                    _appt(id="Y")], _NOW)
    assert "secret@example.com" not in caplog.text
    assert "Reminder planned" in caplog.text