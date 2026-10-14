import logging
import unicodedata
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
MAX_SMS = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SLOTS = ((0, timedelta(hours=48)), (1, timedelta(hours=2)))  # slot 0 = 48h, 1 = 2h


def _sms_opted_in(appt) -> bool:
    # ASSUMPTION: the client's literal wording is "send SMS when optout_sms_v2 is
    # true". The field name suggests the opposite (true = opted OUT), but we follow
    # the literal instruction; flip this single function if the client corrects it.
    # Only optout_sms_v2 is read; the legacy opt_out is never consulted.
    return appt.get("optout_sms_v2") is True


def _channel(appt):
    phone = appt.get("phone")
    if isinstance(phone, str) and phone.strip() and _sms_opted_in(appt):
        return "sms"
    # Email branch deliberately disabled: no fallback to email (R5). If the client
    # ever wants it, add the rule here and nowhere else.
    return None


def _check_aware(value, what):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")


def _validate(appt, idx):
    if not isinstance(appt, Mapping):
        raise ValueError(f"appointment #{idx}: not a mapping")
    for key in ("id", "starts_at"):
        if key not in appt:
            raise ValueError(f"appointment #{idx}: missing key '{key}'")
    _check_aware(appt["starts_at"], f"appointment #{idx}: starts_at")


def _quiet(local):
    return local.hour >= 21 or local.hour < 8


def _adjust_quiet(t, now):
    """t and now are UTC-aware. Returns the send instant after R8/R16."""
    local = t.astimezone(DUB)
    if not _quiet(local):
        return t
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    cand = datetime(day.year, day.month, day.day, 20, tzinfo=DUB).astimezone(UTC)
    if cand >= now:
        return cand
    nl = now.astimezone(DUB)
    if not _quiet(nl):
        return now
    d = nl.date() if nl.hour < 8 else nl.date() + timedelta(days=1)
    return datetime(d.year, d.month, d.day, 8, tzinfo=DUB).astimezone(UTC)


def _compose(name, when, sig):
    date = f"{when.day} {MONTHS[when.month - 1]} {when.year}"
    greet = f"Hi {name}, your" if name else "Your"
    return f"{greet} Brennan Opticians appointment is on {date} at {when:%H:%M}. {sig}".strip()


def _fit(name, when, sig):
    name = unicodedata.normalize("NFC", " ".join((name or "").split()))
    sig = unicodedata.normalize("NFC", sig)
    parts = name.split(" ") if name else []
    ladder = [name]
    if parts:
        first = parts[0]
        if len(parts) > 1:
            ladder.append(f"{first} {parts[-1][0]}.")
        ladder += [first, first[0], ""]
    for cand in ladder:
        text = unicodedata.normalize("NFC", _compose(cand, when, sig))
        if len(text) <= MAX_SMS:
            return text
    return unicodedata.normalize("NFC", _compose("", when, sig))


def plan_reminders(appointments, now):
    _check_aware(now, "now")
    now_u = now.astimezone(UTC)
    entries = []
    for idx, appt in enumerate(appointments):
        _validate(appt, idx)
        status = appt.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            continue
        starts = appt["starts_at"].astimezone(UTC)
        if starts <= now_u:
            continue
        channel = _channel(appt)
        if channel is None:
            continue
        country = appt.get("country")
        sig = SIG_PL if isinstance(country, str) and country.strip().upper() == "PL" else SIG_DEFAULT
        text = _fit(appt.get("customer_name"), starts.astimezone(DUB), sig)
        sends = {}
        for slot, delta in SLOTS:
            t = max(starts - delta, now_u)
            t = _adjust_quiet(t, now_u)
            if t < now_u or t >= starts:
                continue
            sends[slot] = t
        if 0 in sends and sends.get(1) == sends[0]:
            del sends[0]
        for slot, t in sends.items():
            entries.append((t, str(appt["id"]), slot, channel, appt, text))
    entries.sort(key=lambda e: e[:3])
    out = []
    for t, aid, _slot, channel, appt, text in entries:
        # Contact is the phone number for SMS; email addresses are never logged.
        contact = appt["phone"].strip() if channel == "sms" else "<withheld>"
        log.info("reminder planned: appointment=%s channel=%s contact=%s", aid, channel, contact)
        out.append({"appointment_id": appt["id"], "channel": channel,
                    "send_at": t.astimezone(DUB), "text": text})
    return out


# ---------------------------------------------------------------- tests (pytest)
SENTINEL = "sentinel.person@example.invalid"
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def _a(**kw):
    base = dict(id="A1", customer_name="Mary Murphy", email=SENTINEL, phone="+353851234567",
                country="IE", status="booked",
                starts_at=datetime(2026, 10, 20, 10, 0, tzinfo=DUB), optout_sms_v2=True)
    base.update(kw)
    return base


def _last(starts, now=NOW):
    return plan_reminders([_a(starts_at=starts)], now)[-1]["send_at"]


def test_basic_and_shape():
    r = plan_reminders([_a()], NOW)
    assert [set(x) for x in r] == [{"appointment_id", "channel", "send_at", "text"}] * 2
    assert r[0]["send_at"] == datetime(2026, 10, 18, 10, 0, tzinfo=DUB)
    assert r[1]["send_at"] == datetime(2026, 10, 20, 8, 0, tzinfo=DUB)
    assert r[0]["send_at"].tzinfo == DUB
    assert "20 Oct 2026 at 10:00" in r[0]["text"] and r[0]["text"].endswith(SIG_DEFAULT)


def test_quiet_boundaries():
    d = lambda h, m, s: datetime(2026, 10, 20, h, m, s, tzinfo=DUB) + timedelta(hours=2)
    assert _last(d(20, 59, 59)).strftime("%H:%M:%S") == "20:59:59"
    assert _last(d(21, 0, 0)) == datetime(2026, 10, 20, 20, 0, tzinfo=DUB)
    assert _last(d(7, 59, 59)) == datetime(2026, 10, 19, 20, 0, tzinfo=DUB)
    assert _last(d(8, 0, 0)) == datetime(2026, 10, 20, 8, 0, tzinfo=DUB)


def test_dst_transitions():
    s = datetime(2026, 3, 29, 9, 0, tzinfo=UTC)  # 10:00 IST after spring forward
    r = plan_reminders([_a(starts_at=s)], datetime(2026, 3, 1, tzinfo=UTC))
    assert r[0]["send_at"].astimezone(UTC) == s - timedelta(hours=48)
    assert r[0]["send_at"].strftime("%H:%M") == "09:00"
    assert r[1]["send_at"].strftime("%H:%M") == "08:00"
    s = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)  # 10:00 GMT after fall back
    r = plan_reminders([_a(starts_at=s)], datetime(2026, 10, 14, tzinfo=UTC))
    assert r[0]["send_at"].strftime("%H:%M") == "11:00"
    assert r[1]["send_at"].strftime("%H:%M") == "08:00"


def test_past_start_clamp_and_within_2h():
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    r = plan_reminders([_a()], now)
    assert r[0]["send_at"] == now and len(r) == 2
    assert plan_reminders([_a(starts_at=NOW)], NOW) == []
    s = datetime(2026, 10, 20, 11, 0, tzinfo=DUB)
    now = datetime(2026, 10, 20, 9, 30, tzinfo=DUB)
    r = plan_reminders([_a(starts_at=s)], now)
    assert len(r) == 1 and r[0]["send_at"] == now


def test_quiet_now_defers_or_drops():
    now = datetime(2026, 10, 20, 7, 0, tzinfo=DUB)
    r = plan_reminders([_a(starts_at=datetime(2026, 10, 20, 12, 0, tzinfo=DUB))], now)
    assert all(x["send_at"] >= datetime(2026, 10, 20, 8, 0, tzinfo=DUB) for x in r)
    r = plan_reminders([_a(starts_at=datetime(2026, 10, 20, 7, 30, tzinfo=DUB))], now)
    assert r == []


def test_channel_rules():
    assert plan_reminders([_a(status="CANCELLED")], NOW) == []
    assert plan_reminders([_a(optout_sms_v2=False, opt_out=False)], NOW) == []
    assert len(plan_reminders([_a(opt_out=True)], NOW)) == 2
    for p in ("", "  ", None):
        assert plan_reminders([_a(phone=p)], NOW) == []
    b = _a(); del b["optout_sms_v2"]
    assert plan_reminders([b], NOW) == []
    assert {x["channel"] for x in plan_reminders([_a()], NOW)} == {"sms"}


def test_pl_signature():
    r = plan_reminders([_a(country=" pl ")], NOW)
    assert all(x["text"].endswith(SIG_PL) for x in r)


def test_name_lengths():
    when = datetime(2026, 10, 20, 10, 0, tzinfo=DUB)
    k = MAX_SMS - len(_compose("A", when, SIG_DEFAULT)) + 1
    for n, full in ((k - 1, True), (k, True), (k + 1, False)):
        t = plan_reminders([_a(customer_name="A" * n)], NOW)[0]["text"]
        assert len(t) <= 160 and (("A" * n in t) == full)
        assert "20 Oct 2026" in t and "10:00" in t and t.endswith(SIG_DEFAULT)
    assert len(plan_reminders([_a(customer_name="A" * k)], NOW)[0]["text"]) == 160
    t = plan_reminders([_a(customer_name="Maria " + "B" * 140)], NOW)[0]["text"]
    assert "Hi Maria B." in t or "Hi Maria," in t


def test_sorting_and_dedupe():
    r = plan_reminders([_a(id="B"), _a(id="A")], NOW)
    assert [x["appointment_id"] for x in r] == ["A", "B", "A", "B"]
    now = datetime(2026, 10, 20, 8, 30, tzinfo=DUB)
    r = plan_reminders([_a(starts_at=datetime(2026, 10, 20, 9, 0, tzinfo=DUB))], now)
    assert len(r) == 1


def test_errors_and_no_email_leak(caplog):
    caplog.set_level(logging.INFO)
    for bad in (_a(starts_at=datetime(2026, 10, 20, 10, 0)), {"email": SENTINEL}, "x"):
        try:
            plan_reminders([bad], NOW)
            assert False
        except ValueError as e:
            assert SENTINEL not in str(e) and SENTINEL not in repr(e)
    try:
        plan_reminders([_a()], datetime(2026, 1, 1))
        assert False
    except ValueError:
        pass
    plan_reminders([_a()], NOW)
    assert caplog.records and SENTINEL not in caplog.text


def test_pure():
    a = _a(); snap = dict(a)
    plan_reminders([a], NOW)
    assert a == snap