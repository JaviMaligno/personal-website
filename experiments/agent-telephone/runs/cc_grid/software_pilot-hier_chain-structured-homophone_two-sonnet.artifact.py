"""Brennan Opticians appointment reminders (stdlib only).

Tests are at the bottom of this file. Run them with: pytest reminders.py

NOTES (flagged decisions for the client)
- R3/R17(a): "2 hours before" is our interpretation of a garbled requirement.
  It is UNCONFIRMED by the client and must be confirmed. It is the module
  constant SECOND_REMINDER_HOURS = 2.
- R2: optout_sms_v2 missing or None is treated as opted out (privacy
  conservative). The legacy opt_out field is never read.
- R17(b): after the R4 and R9 adjustments, a send_at in the past is moved
  forward to now (if outside quiet hours) or to the next 08:00 Dublin time.
  This deliberately deviates from "move back" only when moving back would
  put send_at before now. Any reminder that would land at or after starts_at
  is dropped and logged at INFO. Appointments with starts_at <= now yield
  nothing. If both reminders end up with identical send_at and channel, both
  are kept (no dedupe).
- R17(c): no usable channel (no phone and no email, or opted out with no
  email) means the appointment is skipped with a WARNING carrying only the
  appointment id.
- R12: non-GSM characters (for example the accented letters in the
  signatures) make SMS providers segment and bill at 70 characters per
  segment. Only the 160-character limit from R7 is enforced.
- Logging: the house rule asks for the contact in each INFO line, but R11
  forbids logging email, phone or name. R11 was followed. Each line carries
  the appointment id, channel and send_at only, which still lets support
  trace deliveries via the appointment record.
- The tests have not been run. This environment had no execution tools, so
  please run pytest before relying on them.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("reminders")

TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
FIRST_REMINDER_HOURS = 48
SECOND_REMINDER_HOURS = 2
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"


def _shift(dt, hours):
    """Absolute-duration shift (not wall-clock), returned in Dublin time."""
    return (dt.astimezone(UTC) + timedelta(hours=hours)).astimezone(TZ)


def _quiet(dt):
    h = dt.astimezone(TZ).hour
    return h >= 21 or h < 8


def _at(dt, hour, day_offset=0):
    d = dt.astimezone(TZ).date() + timedelta(days=day_offset)
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=TZ)


def _move_back(dt):
    dt = dt.astimezone(TZ)
    if not _quiet(dt):
        return dt
    return _at(dt, 20, 0 if dt.hour >= 21 else -1)


def _next_8(dt):
    dt = dt.astimezone(TZ)
    return _at(dt, 8, 1 if dt.hour >= 21 else 0)


def _adjust(target, now, starts):
    t = _move_back(target)
    if t < now:
        t = now if not _quiet(now) else _next_8(now)
    return t if t < starts else None


def _sms_text(name, date, time, sig):
    first = name.split()[0] if name else ""
    variants = []
    for v in (name, first, first[:1] + "." if first else ""):
        if v and v not in variants:
            variants.append(v)
    variants.append("")
    text = ""
    for v in variants:
        text = _email_text(v, date, time, sig)
        if len(text) <= SMS_LIMIT:
            break
    return text


def _email_text(name, date, time, sig):
    lead = f"Hi {name}, reminder:" if name else "Reminder:"
    return f"{lead} your Brennan Opticians appointment is on {date} at {time}. {sig}"


def _plan_one(a, now):
    aid = a["id"]
    if str(a.get("status") or "").strip().lower() == "cancelled":
        logger.info("appointment %s cancelled, no reminders", aid)
        return []
    starts = a["starts_at"].astimezone(TZ)
    if starts <= now:
        logger.info("appointment %s skipped: already started", aid)
        return []
    phone = str(a.get("phone") or "").strip()
    email = str(a.get("email") or "").strip()
    opt = a.get("optout_sms_v2")
    opted_out = opt is None or bool(opt)
    if phone and not opted_out:
        channel = "sms"
    elif email:
        channel = "email"
    else:
        logger.warning("appointment %s skipped: no usable channel", aid)
        return []
    country = str(a.get("country") or "").strip().upper()
    sig = SIG_PL if country == "PL" else SIG_DEFAULT
    name = str(a.get("customer_name") or "").strip()
    date, time = f"{starts:%d/%m/%Y}", f"{starts:%H:%M}"
    build = _sms_text if channel == "sms" else _email_text
    text = build(name, date, time, sig)
    out = []
    # 2-hour reminder first: it has priority.
    targets = [
        ("second", _shift(starts, -SECOND_REMINDER_HOURS)),
        ("first", max(_shift(starts, -FIRST_REMINDER_HOURS), now)),
    ]
    for label, t in targets:
        adj = _adjust(t, now, starts)
        if adj is None:
            logger.info("appointment %s %s reminder dropped: would not precede start", aid, label)
            continue
        logger.info("reminder planned appointment=%s channel=%s send_at=%s",
                    aid, channel, adj.isoformat())
        out.append({"appointment_id": aid, "channel": channel,
                    "send_at": adj, "text": text})
    return out


def plan_reminders(appointments, now):
    now = now.astimezone(TZ)
    result = []
    for a in appointments:
        try:
            result.extend(_plan_one(a, now))
        except Exception as exc:  # isolate failures; log type only (no PII)
            aid = a.get("id") if isinstance(a, dict) else None
            logger.error("appointment %s failed: %s", aid, type(exc).__name__)
    result.sort(key=lambda r: r["send_at"])
    return result


# ----------------------------- tests (pytest) -----------------------------
def _ap(**kw):
    base = dict(id="a1", customer_name="Mary Murphy", email="secret@example.com",
                phone="0851234567", country="IE", status="booked",
                starts_at=datetime(2026, 6, 10, 14, 0, tzinfo=UTC),
                optout_sms_v2=False)
    base.update(kw)
    return base


NOW = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)


def _dub(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=TZ)


def test_r1_r3_r14_keys_offsets_no_mutation():
    import copy
    a = _ap()
    before = copy.deepcopy(a)
    res = plan_reminders([a], NOW)
    assert a == before
    assert len(res) == 2
    for r in res:
        assert set(r) == {"appointment_id", "channel", "send_at", "text"}
        assert r["send_at"].tzinfo is not None
    s = a["starts_at"]
    assert res[0]["send_at"] == s - timedelta(hours=48)
    assert res[1]["send_at"] == s - timedelta(hours=2)


def test_r3_r14_absolute_offsets_across_dst():
    s = datetime(2026, 3, 29, 12, 0, tzinfo=UTC)
    res = plan_reminders([_ap(starts_at=s)], datetime(2026, 3, 20, 9, 0, tzinfo=UTC))
    assert res[0]["send_at"].astimezone(UTC) == datetime(2026, 3, 27, 12, 0, tzinfo=UTC)


def test_r4_first_reminder_now():
    now = NOW
    res = plan_reminders([_ap(starts_at=now + timedelta(hours=24))], now)
    assert res[0]["send_at"] == now and len(res) == 2


def test_r2_optout_field():
    assert plan_reminders([_ap(opt_out=True, optout_sms_v2=False)], NOW)[0]["channel"] == "sms"
    assert plan_reminders([_ap(optout_sms_v2=True)], NOW)[0]["channel"] == "email"
    a = _ap()
    del a["optout_sms_v2"]
    assert plan_reminders([a], NOW)[0]["channel"] == "email"


def test_r6_channels():
    assert {r["channel"] for r in plan_reminders([_ap()], NOW)} == {"sms"}
    assert {r["channel"] for r in plan_reminders([_ap(phone="")], NOW)} == {"email"}
    assert plan_reminders([_ap(optout_sms_v2=True, email="")], NOW) == []


def test_r7_sms_shortening_steps():
    long_full = _ap(customer_name="A" + "b" * 150 + " Smith")
    t = plan_reminders([long_full], NOW)[0]["text"]
    assert len(t) <= 160 and t.startswith("Hi A.,") and "10/06/2026" in t and "15:00" in t
    t = plan_reminders([_ap(customer_name="N" * 40 + " " + "S" * 60)], NOW)[0]["text"]
    assert len(t) <= 160 and "N" * 40 in t and "S" * 60 not in t
    t = _sms_text("Anna Bee", "10/06/2026", "15:00", "S" * 85)
    assert t.startswith("Reminder:") and len(t) <= 160
    em = plan_reminders([_ap(optout_sms_v2=True, customer_name="X" * 300)], NOW)[0]["text"]
    assert "X" * 300 in em


def test_r8_r14_dublin_display():
    t = plan_reminders([_ap()], NOW)[0]["text"]
    assert "10/06/2026" in t and "15:00" in t
    w = plan_reminders([_ap(starts_at=datetime(2026, 1, 10, 14, 0, tzinfo=UTC))],
                       datetime(2026, 1, 1, 9, 0, tzinfo=UTC))[0]["text"]
    assert "14:00" in w


def test_r9_quiet_hours_and_dst():
    for h, mi in ((21, 0), (23, 59)):
        assert _move_back(_dub(2026, 6, 10, h, mi)) == _dub(2026, 6, 10, 20)
    for h, mi in ((0, 0), (7, 59)):
        assert _move_back(_dub(2026, 6, 10, h, mi)) == _dub(2026, 6, 9, 20)
    for h, mi in ((8, 0), (20, 59)):
        assert _move_back(_dub(2026, 6, 10, h, mi)) == _dub(2026, 6, 10, h, mi)
    # last Sunday of October (DST ends) and of March (DST starts)
    r = _move_back(_dub(2026, 10, 25, 0, 30))
    assert r.astimezone(UTC) == datetime(2026, 10, 24, 19, 0, tzinfo=UTC)
    r = _move_back(_dub(2026, 3, 29, 3, 0))
    assert r.astimezone(UTC) == datetime(2026, 3, 28, 20, 0, tzinfo=UTC)


def test_r5_sweep():
    s = datetime(2026, 6, 10, 14, 0, tzinfo=UTC)
    for i in range(150):
        now = datetime(2026, 6, 8, 0, 0, tzinfo=UTC) + timedelta(minutes=47 * i)
        for r in plan_reminders([_ap(starts_at=s)], now):
            assert r["send_at"] >= now and r["send_at"] < s
            assert not _quiet(r["send_at"])


def test_r10_cancelled():
    assert plan_reminders([_ap(status=" Cancelled ")], NOW) == []


def test_r11_no_pii_in_logs(caplog):
    caplog.set_level(logging.DEBUG, logger="reminders")
    apps = [_ap(), _ap(id="b", optout_sms_v2=True, phone=""),
            _ap(id="c", email="", phone="", ),
            _ap(id="d", starts_at="bad"),
            _ap(id="e", optout_sms_v2=True, email=""),
            _ap(id="f", status="cancelled")]
    plan_reminders(apps, NOW)
    assert caplog.records
    for rec in caplog.records:
        m = rec.getMessage()
        assert "secret@example.com" not in m and "0851234567" not in m
        assert "Mary" not in m
    assert "secret@example.com" not in caplog.text


def test_r12_signatures():
    t = plan_reminders([_ap()], NOW)[0]["text"]
    assert t.endswith("Siobhán Ní Dhuibhir")
    t = plan_reminders([_ap(country=" pl ", customer_name="Z" * 200)], NOW)[0]["text"]
    assert t.endswith("Grzegorz Szczepański") and len(t) <= 160


def test_r13_error_isolation():
    res = plan_reminders([_ap(id="x", starts_at="bad"), _ap(id="y"), {}], NOW)
    assert [r["appointment_id"] for r in res] == ["y", "y"]


def test_r15_sorted():
    res = plan_reminders([_ap(id="late", starts_at=datetime(2026, 6, 20, 14, tzinfo=UTC)),
                          _ap(id="early")], NOW)
    ts = [r["send_at"] for r in res]
    assert ts == sorted(ts) and len(res) == 4


def test_r17b_forward_and_drop():
    now = _dub(2026, 6, 9, 22)
    res = plan_reminders([_ap()], now)
    assert res[0]["send_at"] == _dub(2026, 6, 10, 8)
    now = _dub(2026, 6, 9, 12)
    res = plan_reminders([_ap(starts_at=now + timedelta(hours=1))], now)
    assert [r["send_at"] for r in res] == [now, now]
    now = _dub(2026, 6, 9, 22)
    assert plan_reminders([_ap(starts_at=_dub(2026, 6, 9, 23))], now) == []
    assert plan_reminders([_ap(starts_at=NOW)], NOW) == []


def test_r17c_no_channel_warns(caplog):
    caplog.set_level(logging.DEBUG, logger="reminders")
    assert plan_reminders([_ap(id="zz", phone=" ", email=None)], NOW) == []
    assert any(r.levelno == logging.WARNING and "zz" in r.getMessage()
               for r in caplog.records)