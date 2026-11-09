"""Brennan Opticians appointment reminder planner.

Dependencies: standard library only, but zoneinfo needs the IANA database.
The server is UTC and may not ship it, so add `tzdata` to requirements
(pip install tzdata). Tests: pytest (`pytest this_file.py`).

Assumptions:
- The brief wins over the house logging rule. The house rule asks for the
  contact in the INFO line, but the brief forbids logging email addresses,
  so INFO lines carry appointment_id, channel and a contact kind
  ("phone on file" or "email on file"), never the address or number.
- Date and time in the text are the appointment's Dublin local date and time.
- A missing or empty name renders as "there".
- Quiet-hour forward move goes to the next 08:00 after the quiet-shifted raw time.
- A forward-moved reminder at or after starts_at is dropped. A back-shifted
  one is never after starts_at.
- A non-string or missing status, phone, email or country is treated as blank.
- Output ties are sorted by str(appointment_id).
- CONFIRM: the client should confirm that logging a contact kind instead of the
  actual contact is acceptable to support, and that "there" is wanted for
  blank names.
"""
import copy
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SMS_MAX = 160


def _s(v):
    return v.strip() if isinstance(v, str) else ""


def _aware(dt, label):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return dt.astimezone(UTC)


def _shift(t, now, starts):
    """Apply quiet hours to UTC instant t. Return UTC instant or None to drop."""
    local = t.astimezone(DUB)
    if 8 <= local.hour < 21:
        return t
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    back = datetime.combine(day, time(20), DUB).astimezone(UTC)
    if back >= now:
        return back
    day = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    fwd = datetime.combine(day, time(8), DUB).astimezone(UTC)
    return None if fwd >= starts else fwd


def _text(name, local_start, sig, is_sms):
    date = f"{local_start.day} {MONTHS[local_start.month - 1]} {local_start.year}"
    hhmm = f"{local_start.hour:02d}:{local_start.minute:02d}"

    def build(n):
        return (f"Hi {n or 'there'}, a reminder of your Brennan Opticians "
                f"appointment on {date} at {hhmm}. {sig}")

    name = " ".join(name.split())
    if not is_sms:
        return build(name)
    parts = name.split()
    cands = [name]
    if len(parts) > 1:
        cands.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        cands.append(parts[0])
    for c in cands:
        if len(build(c)) <= SMS_MAX:
            return build(c)
    avail = SMS_MAX - len(build("x")) + 1
    return build(parts[0][:max(avail, 0)] if parts else "")


def plan_reminders(appointments, now):
    now = _aware(now, "now")
    out = []
    for a in appointments:
        aid = a.get("id")
        if _s(a.get("status")).lower() in ("cancelled", "canceled"):
            log.debug("skip %s: cancelled", aid)
            continue
        starts = _aware(a.get("starts_at"), "starts_at")
        if starts <= now:
            log.debug("skip %s: already started", aid)
            continue
        phone, email = _s(a.get("phone")), _s(a.get("email"))
        if phone and a.get("optout_sms_v2") is False:
            channel, kind = "sms", "phone on file"
        elif email:
            channel, kind = "email", "email on file"
        else:
            log.debug("skip %s: no usable contact", aid)
            continue
        sig = ("Grzegorz Szczepański" if _s(a.get("country")).upper() == "PL"
               else "Chevonne Nee Divver")
        text = _text(_s(a.get("customer_name")), starts.astimezone(DUB),
                     sig, channel == "sms")
        raws = [max(starts - timedelta(hours=48), now), starts - timedelta(hours=2)]
        for i, raw in enumerate(raws):
            if i == 1 and raw < now:
                log.debug("skip %s: second reminder in the past", aid)
                continue
            t = _shift(raw, now, starts)
            if t is None:
                log.debug("skip %s: reminder %d has no valid send time", aid, i + 1)
                continue
            log.info("planned reminder %d for appointment %s via %s (%s)",
                     i + 1, aid, channel, kind)
            out.append(((t, str(aid), i), {
                "appointment_id": aid, "channel": channel,
                "send_at": t.astimezone(DUB), "text": text}))
    out.sort(key=lambda p: p[0])
    return [r for _, r in out]


# ---------------------------------------------------------------- tests
import pytest  # noqa: E402

EMAIL = "secret.person@example.com"


def _appt(**kw):
    d = {"id": "A1", "customer_name": "Mary O'Neill", "email": EMAIL,
         "phone": "+353851234567", "country": "IE", "status": "booked",
         "optout_sms_v2": False,
         "starts_at": datetime(2026, 10, 20, 12, 0, tzinfo=DUB)}
    d.update(kw)
    return d


NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def test_basic_two_reminders_and_keys():
    r = plan_reminders([_appt()], NOW)
    assert len(r) == 2
    assert set(r[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert r[0]["send_at"].astimezone(UTC) == datetime(2026, 10, 18, 11, 0, tzinfo=UTC)
    assert r[1]["send_at"].astimezone(UTC) == datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
    assert "20 Oct 2026 at 12:00" in r[0]["text"]
    assert r[0]["text"].endswith("Chevonne Nee Divver")
    assert EMAIL not in str(r)


def test_naive_raises():
    with pytest.raises(ValueError):
        plan_reminders([], datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 12))], NOW)


def test_no_mutation():
    a = [_appt()]
    b = copy.deepcopy(a)
    plan_reminders(a, NOW)
    assert a == b


@pytest.mark.parametrize("st", ["cancelled", " Canceled ", "CANCELLED"])
def test_cancelled(st):
    assert plan_reminders([_appt(status=st)], NOW) == []


def test_started_gets_nothing():
    assert plan_reminders([_appt()], datetime(2026, 10, 20, 11, 0, tzinfo=UTC)) == []


def test_clamp_first_to_now_and_drop_second():
    now = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)  # 09:00 Dublin, start 12:00
    r = plan_reminders([_appt()], now)
    assert r[0]["send_at"] == now and len(r) == 2
    now = datetime(2026, 10, 20, 10, 30, tzinfo=UTC)  # 11:30 Dublin, second passed
    r = plan_reminders([_appt()], now)
    assert len(r) == 1 and r[0]["send_at"] == now


def test_dst_march_elapsed_48h():
    s = datetime(2026, 3, 30, 12, 0, tzinfo=DUB)  # BST
    r = plan_reminders([_appt(starts_at=s)], datetime(2026, 3, 1, tzinfo=UTC))
    assert r[0]["send_at"].astimezone(UTC) == datetime(2026, 3, 28, 11, 0, tzinfo=UTC)
    assert r[0]["send_at"].hour == 11


def test_dst_october_elapsed_48h():
    s = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)  # GMT
    r = plan_reminders([_appt(starts_at=s)], NOW)
    assert r[0]["send_at"].astimezone(UTC) == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert r[0]["send_at"].hour == 13  # still BST on the 24th


def _second(h, m, day=14):
    s = datetime(2026, 10, day, h, m, tzinfo=DUB) + timedelta(hours=2)
    return plan_reminders([_appt(starts_at=s)], NOW)[-1]["send_at"]


@pytest.mark.parametrize("h,m,exp", [
    (20, 59, (14, 20, 59)), (21, 0, (14, 20, 0)), (23, 30, (14, 20, 0)),
    (3, 0, (13, 20, 0)), (7, 59, (13, 20, 0)), (8, 0, (14, 8, 0))])
def test_quiet_boundaries(h, m, exp):
    got = _second(h, m)
    assert (got.day, got.hour, got.minute) == exp


def test_shift_into_past_moves_forward():
    now = datetime(2026, 10, 14, 21, 30, tzinfo=UTC)  # 22:30 Dublin
    s = datetime(2026, 10, 15, 11, 0, tzinfo=DUB)
    r = plan_reminders([_appt(starts_at=s)], now)
    assert r[0]["send_at"] == datetime(2026, 10, 15, 8, 0, tzinfo=DUB)
    assert all(x["send_at"] >= now for x in r)


def test_shift_forward_beyond_start_drops():
    now = datetime(2026, 10, 14, 21, 0, tzinfo=UTC)  # 22:00 Dublin
    s = datetime(2026, 10, 15, 0, 0, tzinfo=DUB)
    assert plan_reminders([_appt(starts_at=s)], now) == []


@pytest.mark.parametrize("kw,exp", [
    ({}, "sms"),
    ({"optout_sms_v2": True}, "email"),
    ({"optout_sms_v2": None}, "email"),
    ({"optout_sms_v2": True, "email": " "}, None),
    ({"optout_sms_v2": None, "email": ""}, None),
    ({"phone": ""}, "email"),
    ({"phone": "  "}, "email"),
    ({"phone": None, "email": None}, None),
    ({"phone": "", "email": ""}, None),
])
def test_channel_matrix(kw, exp):
    r = plan_reminders([_appt(**kw)], NOW)
    assert {x["channel"] for x in r} == ({exp} if exp else set())


def test_missing_flag_is_opted_out():
    a = _appt()
    del a["optout_sms_v2"]
    assert plan_reminders([a], NOW)[0]["channel"] == "email"


def test_legacy_opt_out_ignored():
    assert plan_reminders([_appt(opt_out=True)], NOW)[0]["channel"] == "sms"
    assert plan_reminders([_appt(opt_out=False, optout_sms_v2=True)], NOW)[0]["channel"] == "email"


def test_pl_signature():
    for c in ("PL", " pl "):
        t = plan_reminders([_appt(country=c)], NOW)[0]["text"]
        assert t.endswith("Grzegorz Szczepański")


def test_sms_shortening_stages():
    long = "Bartholomew " + "Wolfeschlegelstein " * 3 + "Hauptmann"
    t = plan_reminders([_appt(customer_name=long, country="PL")], NOW)[0]["text"]
    assert len(t) <= 160 and "20 Oct 2026 at 12:00" in t
    assert t.endswith("Grzegorz Szczepański")
    t = plan_reminders([_appt(customer_name="Ann Marie Smith")], NOW)[0]["text"]
    assert t.startswith("Hi Ann Marie Smith,")
    t = plan_reminders([_appt(customer_name="A" * 300)], NOW)[0]["text"]
    assert len(t) == 160 and "20 Oct 2026 at 12:00" in t
    t = plan_reminders([_appt(customer_name="B" * 70 + " " + "C" * 70)], NOW)[0]["text"]
    assert len(t) <= 160 and ("B" * 70 + " C.") in t


def test_email_name_not_truncated():
    n = "Z" * 300
    t = plan_reminders([_appt(customer_name=n, optout_sms_v2=True)], NOW)[0]["text"]
    assert n in t and len(t) > 160


@pytest.mark.parametrize("n", ["", None, "   "])
def test_empty_name(n):
    t = plan_reminders([_appt(customer_name=n)], NOW)[0]["text"]
    assert t.startswith("Hi there,")


def test_sorting():
    a = _appt(id="B")
    b = _appt(id="A")
    r = plan_reminders([a, b], NOW)
    assert [x["appointment_id"] for x in r] == ["A", "B", "A", "B"]
    assert [x["send_at"] for x in r] == sorted(x["send_at"] for x in r)


def test_logging_no_email_and_traceable(caplog):
    caplog.set_level(logging.DEBUG)
    appts = [_appt(), _appt(id="C", status="cancelled"),
             _appt(id="N", phone="", email="", optout_sms_v2=True),
             _appt(id="E", optout_sms_v2=True)]
    plan_reminders(appts, NOW)
    plan_reminders([_appt(id="S")], datetime(2026, 12, 1, tzinfo=UTC))
    assert EMAIL not in caplog.text
    assert "+353851234567" not in caplog.text
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 4
    assert any("A1" in r.getMessage() and "sms" in r.getMessage() for r in infos)
    assert any("E" in r.getMessage() and "email" in r.getMessage() for r in infos)
    msgs = caplog.text
    assert "C: cancelled" in msgs and "N: no usable contact" in msgs
    assert "S: already started" in msgs