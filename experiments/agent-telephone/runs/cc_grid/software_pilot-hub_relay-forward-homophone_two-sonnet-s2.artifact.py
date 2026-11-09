"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now).

Assumptions (to confirm with the client):
- The brief is garbled ("the second one too, hours before"); the second reminder is
  sent 2 hours before the appointment. 48h and 2h are elapsed time (UTC arithmetic),
  so they stay correct across DST changes.
- Quiet hours are 21:00-08:00 Europe/Dublin. A time inside the window moves back to
  the previous 20:00. If that is before `now`, it moves forward to the next 08:00 if
  that is still before starts_at, otherwise the reminder is dropped.
- Cancelled is matched case-insensitively. Appointments with starts_at <= now get
  nothing. A 2h point that has already passed is omitted; only the first reminder is
  sent immediately. Identical send_at values are both kept.
- SMS if a phone is present and optout_sms_v2 is not truthy (missing = not opted
  out), else email. The legacy opt_out field is ignored. If email is needed but
  missing, the reminder is skipped and only the appointment id is logged.
- Naive datetimes raise ValueError. Output send_at is tz-aware in Europe/Dublin.
- Logging: one INFO line per planned reminder. The brief forbids logging email
  addresses, so email reminders are logged as "email on file"; SMS logs the phone.
- SMS name shortening order: full name, first name + last initial, first name,
  truncated first name, name dropped. Date, HH:MM and signature are always kept.

Open questions for the client:
- Final template wording (one constant, TEMPLATE, below).
- Date format (currently DD/MM/YYYY).
- SMS limit: 160 counts characters, but names with non-GSM characters (Siobhan with
  fada, Szczepanski with n-acute) make a message UCS-2, where the real limit is 70
  per segment. Should we count that way?
- Krakow branch: times are shown in Dublin time even for PL customers. Should they
  be shown in Europe/Warsaw time?
"""
import copy
import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

log = logging.getLogger(__name__)
DUB = ZoneInfo("Europe/Dublin")
SMS_MAX = 160
TEMPLATE = ("Hi{name}, reminder: your appointment at Brennan Opticians "
            "is on {date} at {time}. {sig}")


def _check_aware(dt, what):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")


def _adjust(t, now, starts):
    """Apply quiet hours to t (aware). Returns aware Dublin datetime or None."""
    local = t.astimezone(DUB)
    if 8 <= local.hour < 21:
        return local
    day = local if local.hour >= 21 else local - timedelta(days=1)
    back = day.replace(hour=20, minute=0, second=0, microsecond=0)
    if back >= now:
        return back
    base = local if local.hour < 8 else local + timedelta(days=1)
    fwd = base.replace(hour=8, minute=0, second=0, microsecond=0)
    return fwd if fwd < starts else None


def _text(name, start_local, sig, limit=None):
    def build(n):
        return TEMPLATE.format(name=f" {n}" if n else "", date=start_local.strftime("%d/%m/%Y"),
                               time=start_local.strftime("%H:%M"), sig=sig)

    name = " ".join((name or "").split())
    if limit is None:
        return build(name)
    parts = name.split()
    cands = [name]
    if len(parts) > 1:
        cands.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        cands.append(parts[0])
    for c in cands:
        if len(build(c)) <= limit:
            return build(c)
    if parts:
        for n in range(len(parts[0]) - 1, 0, -1):
            if len(build(parts[0][:n])) <= limit:
                return build(parts[0][:n])
    return build("")


def plan_reminders(appointments, now):
    _check_aware(now, "now")
    out = []
    for a in appointments:
        starts = a["starts_at"]
        _check_aware(starts, "starts_at")
        if str(a.get("status") or "").strip().lower() == "cancelled" or starts <= now:
            continue
        aid = a["id"]
        phone = (a.get("phone") or "").strip()
        email = (a.get("email") or "").strip()
        if phone and not a.get("optout_sms_v2"):
            channel, contact = "sms", phone
        elif email:
            channel, contact = "email", "email on file"
        else:
            log.info("reminder skipped, no usable contact appointment_id=%s", aid)
            continue
        sig = ("Grzegorz Szczepański" if a.get("country") == "PL"
               else "Siobhán Ní Dhuibhir")
        text = _text(a.get("customer_name"), starts.astimezone(DUB), sig,
                     SMS_MAX if channel == "sms" else None)
        su = starts.astimezone(timezone.utc)
        nu = now.astimezone(timezone.utc)
        first = su - timedelta(hours=48)
        points = [(0, first if first >= nu else nu), (1, su - timedelta(hours=2))]
        for order, t in points:
            if order == 1 and t < nu:
                continue
            send = _adjust(t, now, starts)
            if send is None:
                continue
            out.append(((send, str(aid), order), {
                "appointment_id": aid, "channel": channel,
                "send_at": send, "text": text}))
            log.info("reminder planned appointment_id=%s channel=%s contact=%s send_at=%s",
                     aid, channel, contact, send.isoformat())
    out.sort(key=lambda p: p[0])
    return [r for _, r in out]


# ---------------------------------------------------------------- tests
NOW = datetime(2026, 6, 1, 10, 0, tzinfo=DUB)


def _a(**kw):
    d = {"id": "A1", "customer_name": "Aoife Murphy", "email": "aoife@example.com",
         "phone": "+353851234567", "country": "IE", "status": "booked",
         "starts_at": datetime(2026, 6, 10, 14, 0, tzinfo=DUB), "optout_sms_v2": False}
    d.update(kw)
    return d


def test_two_hour_reminder_and_48h():
    r = plan_reminders([_a()], NOW)
    assert [x["send_at"] for x in r] == [datetime(2026, 6, 8, 14, tzinfo=DUB),
                                         datetime(2026, 6, 10, 12, tzinfo=DUB)]
    assert set(r[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert "10/06/2026 at 14:00" in r[1]["text"]
    assert r[1]["text"].endswith("Siobhán Ní Dhuibhir")


def test_dst_march_elapsed():
    a = _a(starts_at=datetime(2026, 3, 30, 12, 0, tzinfo=DUB))
    r = plan_reminders([a], datetime(2026, 3, 1, 9, tzinfo=timezone.utc))
    assert r[0]["send_at"].hour == 11 and r[0]["send_at"].day == 28


def test_dst_october_elapsed():
    a = _a(starts_at=datetime(2026, 10, 26, 12, 0, tzinfo=DUB))
    r = plan_reminders([a], datetime(2026, 10, 1, 9, tzinfo=timezone.utc))
    assert r[0]["send_at"].hour == 13 and r[0]["send_at"].day == 24


def test_system_tz_utc(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    r = plan_reminders([_a()], NOW)
    assert r[1]["send_at"].utcoffset() == timedelta(hours=1)
    assert r[1]["send_at"].tzinfo == DUB


@pytest.mark.parametrize("start,expected", [
    ((10, 10, 0), (10, 8, 0)), ((10, 22, 59), (10, 20, 59)),
    ((10, 23, 0), (10, 20, 0)), ((10, 1, 30), (9, 20, 0)), ((10, 5, 0), (9, 20, 0))])
def test_quiet_hours(start, expected):
    d, h, m = start
    r = plan_reminders([_a(starts_at=datetime(2026, 6, d, h, m, tzinfo=DUB))], NOW)
    assert r[-1]["send_at"] == datetime(2026, 6, expected[0], expected[1], expected[2], tzinfo=DUB)


def test_moved_back_before_now_goes_forward_or_drops():
    now = datetime(2026, 6, 10, 21, 30, tzinfo=DUB)
    r = plan_reminders([_a(starts_at=datetime(2026, 6, 11, 12, tzinfo=DUB))], now)
    assert r[0]["send_at"] == datetime(2026, 6, 11, 8, tzinfo=DUB)
    assert all(x["send_at"] >= now for x in r)
    assert plan_reminders([_a(starts_at=datetime(2026, 6, 11, 7, tzinfo=DUB))], now) == []


def test_skips():
    assert plan_reminders([_a(status="Cancelled")], NOW) == []
    assert plan_reminders([_a(starts_at=NOW)], NOW) == []
    assert plan_reminders([_a(starts_at=NOW + timedelta(hours=1))], NOW) == []


def test_past_2h_omitted_but_immediate_first():
    now = datetime(2026, 6, 10, 13, tzinfo=DUB)
    r = plan_reminders([_a()], now)
    assert len(r) == 1 and r[0]["send_at"] == now


def test_channels():
    assert plan_reminders([_a()], NOW)[0]["channel"] == "sms"
    assert plan_reminders([_a(optout_sms_v2=True)], NOW)[0]["channel"] == "email"
    assert plan_reminders([_a(opt_out=True)], NOW)[0]["channel"] == "sms"
    assert plan_reminders([_a(phone=None)], NOW)[0]["channel"] == "email"
    assert plan_reminders([_a(phone="", email=None)], NOW) == []
    assert plan_reminders([_a(optout_sms_v2=True, email="")], NOW) == []


def test_sms_shortening_keeps_date_time_signature():
    a = _a(customer_name="Bartholomew " + "X" * 80 + " Featherstonehaugh", country="PL")
    t = plan_reminders([a], NOW)[0]["text"]
    assert len(t) <= 160 and "10/06/2026 at 14:00" in t and t.endswith("Grzegorz Szczepański")
    e = plan_reminders([dict(a, optout_sms_v2=True)], NOW)[0]["text"]
    assert "Featherstonehaugh" in e


def test_no_email_in_logs_and_one_line_each(caplog):
    caplog.set_level(logging.INFO)
    plan_reminders([_a(optout_sms_v2=True), _a(id="A2", email="", phone="")], NOW)
    assert "@" not in caplog.text and "example.com" not in caplog.text
    planned = [r for r in caplog.records if "planned" in r.getMessage()]
    assert len(planned) == 2 and "email" in planned[0].getMessage()


def test_input_unchanged_and_sorted():
    apps = [_a(id="B", starts_at=datetime(2026, 6, 12, 14, tzinfo=DUB)), _a(id="A")]
    before = copy.deepcopy(apps)
    r = plan_reminders(apps, NOW)
    assert apps == before
    keys = [(x["send_at"], str(x["appointment_id"])) for x in r]
    assert keys == sorted(keys)


def test_naive_raises():
    with pytest.raises(ValueError):
        plan_reminders([_a()], datetime(2026, 6, 1, 10))
    with pytest.raises(ValueError):
        plan_reminders([_a(starts_at=datetime(2026, 6, 10, 14))], NOW)