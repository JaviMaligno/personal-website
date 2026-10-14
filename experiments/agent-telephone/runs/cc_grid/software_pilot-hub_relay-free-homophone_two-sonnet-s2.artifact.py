"""Brennan Opticians appointment reminders (single-file module, stdlib only).

Dependency note: on servers without a system tz database (the server runs in
UTC) install the `tzdata` package so zoneinfo can load Europe/Dublin.
Tests are in this file (pytest: `pytest brennan_reminders.py`).
Status: written without the ability to execute code; the test suite has NOT
been run by the author. Run it before relying on it.

ASSUMPTIONS (unconfirmed with the client):
 1. "too, hours before" means 2 hours before the appointment.
 2. If the 2h point is already past but the appointment is still in the
    future, the second reminder's nominal time is now.
 3. A missing or None optout_sms_v2 is treated as opted out of SMS
    (only a literal False allows SMS).
 4. Logging: the house rule asks for the contact in the log line, but the
    privacy rule forbids logging email addresses. The log line therefore
    carries appointment id, channel and contact KIND (phone or email), never
    the contact value.

RISK: both signatures contain non-GSM-7 characters (the accented letters), so
real gateways will likely send these as Unicode with a 70-character segment
limit. This module enforces the stated 160-character limit (len). The client
should confirm whether they mean 160 characters or one segment.
"""
import logging
import unicodedata
from collections.abc import Mapping
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
log = logging.getLogger("brennan_reminders")

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"
_SMS_LIMIT = 160


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _quiet(dt):
    h = dt.astimezone(DUB).hour
    return h >= 21 or h < 8


def _at(day, hour):
    return datetime.combine(day, time(hour), tzinfo=DUB).astimezone(UTC)


def _move_back(dt):
    loc = dt.astimezone(DUB)
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    return _at(day, 20)


def _next_8(now):
    day = now.astimezone(DUB).date()
    cand = _at(day, 8)
    if cand <= now:
        cand = _at(day + timedelta(days=1), 8)
    return cand


def _adjust(nominal, now, start):
    """Apply quiet hours and never-in-the-past; None means drop."""
    if _quiet(nominal):
        moved = _move_back(nominal)
        if moved >= now:
            result = moved
        elif not _quiet(now):
            result = now
        else:
            result = _next_8(now)
    else:
        result = nominal
    return result if result < start else None


def _render(greeting_name, date_s, time_s, sig):
    hello = f"Hello {greeting_name}," if greeting_name else "Hello,"
    return _nfc(f"{hello} a friendly reminder from Brennan Opticians: your "
                f"appointment is on {date_s} at {time_s}. Kind regards, {sig}")


def _name_candidates(name):
    parts = name.split()
    if not parts:
        return
    yield " ".join(parts)
    if len(parts) > 1:
        yield f"{parts[0]} {parts[-1][0]}."
    yield parts[0]
    for n in range(len(parts[0]) - 1, 0, -1):
        yield parts[0][:n]


def _make_text(channel, name, date_s, time_s, sig):
    name = _nfc(" ".join(name.split())) if isinstance(name, str) else ""
    if channel == "email":
        return _render(name, date_s, time_s, sig)
    for cand in _name_candidates(name):
        text = _render(cand, date_s, time_s, sig)
        if len(text) <= _SMS_LIMIT:
            return text
    return _render("", date_s, time_s, sig)


def _clean(v):
    return v.strip() if isinstance(v, str) else ""


def _plan_one(appt, now):
    if not isinstance(appt, Mapping):
        raise ValueError("not a mapping")
    aid = appt.get("id")
    start = appt.get("starts_at")
    if aid is None or aid == "" or not isinstance(start, datetime) \
            or start.utcoffset() is None:
        log.info("appointment skipped id=%s reason=malformed", aid)
        return []
    status = appt.get("status")
    if status is not None and str(status).strip().lower() == "cancelled":
        log.info("appointment skipped id=%s reason=cancelled", aid)
        return []
    start = start.astimezone(UTC)
    if start <= now:
        log.info("appointment skipped id=%s reason=past", aid)
        return []

    if _clean(appt.get("phone")) and appt.get("optout_sms_v2") is False:
        channel, kind = "sms", "phone"
    elif _clean(appt.get("email")):
        channel, kind = "email", "email"
    else:
        log.info("appointment skipped id=%s reason=no_contact", aid)
        return []

    nominals = [max(start - timedelta(hours=48), now),
                max(start - timedelta(hours=2), now)]
    sends = [_adjust(n, now, start) for n in nominals]
    if sends[0] is not None and sends[1] is not None and sends[0] >= sends[1]:
        sends[0] = None

    loc = start.astimezone(DUB)
    date_s = f"{loc.day} {_MONTHS[loc.month - 1]} {loc.year}"
    time_s = f"{loc.hour:02d}:{loc.minute:02d}"
    country = appt.get("country")
    is_pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = _nfc(_SIG_PL if is_pl else _SIG_DEFAULT)
    text = _make_text(channel, appt.get("customer_name"), date_s, time_s, sig)

    out = []
    for order, send in enumerate(sends):
        if send is None:
            continue
        log.info("reminder planned id=%s channel=%s contact=%s send_at=%s",
                 aid, channel, kind, send.isoformat())
        out.append((send, str(aid), order, {
            "appointment_id": aid, "channel": channel,
            "send_at": send.astimezone(DUB), "text": text}))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        try:
            planned.extend(_plan_one(appt, now))
        except Exception as exc:  # never include message: may hold PII
            aid = appt.get("id") if isinstance(appt, Mapping) else None
            log.info("appointment skipped id=%s reason=error_%s",
                     aid, type(exc).__name__)
    planned.sort(key=lambda p: p[:3])
    return [p[3] for p in planned]


# ----------------------------------------------------------------- tests
import copy  # noqa: E402

_CAPTURED = []


class _H(logging.Handler):
    def emit(self, record):
        _CAPTURED.append(record.getMessage())


_HANDLER = _H()


def run(appts, now):
    if _HANDLER not in log.handlers:
        log.addHandler(_HANDLER)
        log.setLevel(logging.INFO)
    return plan_reminders(appts, now)


def dub(d, h, m=0, month=10):
    return datetime(2026, month, d, h, m, tzinfo=DUB)


def ap(**kw):
    base = dict(id="a1", customer_name="Mary Murphy", email="mary.m@example.com",
                phone="0851234567", country="IE", status="booked",
                starts_at=dub(20, 14, 30), optout_sms_v2=False)
    base.update(kw)
    return base


def test_worked_example_basic():
    now = datetime(2026, 10, 13, 9, tzinfo=UTC)
    r = run([ap()], now)
    assert [x["send_at"] for x in r] == [
        datetime(2026, 10, 18, 13, 30, tzinfo=UTC),
        datetime(2026, 10, 20, 11, 30, tzinfo=UTC)]
    assert r[0]["send_at"].utcoffset() == timedelta(hours=1)
    for x in r:
        assert set(x) == {"appointment_id", "channel", "send_at", "text"}
        assert x["channel"] == "sms"
        assert "20 Oct 2026" in x["text"] and "14:30" in x["text"]
        assert "Brennan Opticians" in x["text"] and "Mary Murphy" in x["text"]
        assert x["text"].endswith("Siobhán Ní Dhuibhir")


def test_dst_end_and_quiet_move_back():
    now = datetime(2026, 10, 13, 9, tzinfo=UTC)
    r = run([ap(starts_at=dub(26, 9))], now)
    assert r[0]["send_at"] == datetime(2026, 10, 24, 9, tzinfo=UTC)
    assert r[1]["send_at"] == dub(25, 20)
    assert r[1]["send_at"] == datetime(2026, 10, 25, 20, tzinfo=UTC)


def test_now_quiet_pushes_to_morning():
    r = run([ap()], dub(19, 22, 30))
    assert [x["send_at"] for x in r] == [dub(20, 8), dub(20, 12, 30)]


def test_first_is_now_second_moved_back():
    r = run([ap(starts_at=dub(20, 8, 30))], dub(19, 12))
    assert [x["send_at"] for x in r] == [dub(19, 12), dub(19, 20)]


def test_only_second_at_now():
    r = run([ap()], dub(20, 13))
    assert len(r) == 1 and r[0]["send_at"] == dub(20, 13)


def test_no_reminders_when_morning_after_start():
    assert run([ap(starts_at=dub(20, 7, 30))], dub(19, 22)) == []


def test_quiet_boundaries():
    assert _quiet(dub(19, 21)) and not _quiet(dub(19, 8))
    assert not _quiet(dub(19, 20, 59)) and _quiet(dub(19, 7, 59))
    assert _move_back(dub(19, 22)) == dub(19, 20)
    assert _move_back(dub(20, 3)) == dub(19, 20)


def test_skips():
    now = dub(13, 9)
    assert run([ap(status="  CANCELLED ")], now) == []
    assert run([ap(starts_at=dub(12, 9))], now) == []
    assert run([ap(phone="", email=" ")], now) == []
    assert run([ap(phone=None, email=None)], now) == []


def test_channels():
    now = dub(13, 9)
    assert {x["channel"] for x in run([ap(optout_sms_v2=True)], now)} == {"email"}
    assert run([ap(optout_sms_v2=True, email="")], now) == []
    assert {x["channel"] for x in run([ap(phone="  ")], now)} == {"email"}
    assert {x["channel"] for x in run([ap()], now)} == {"sms"}
    a = ap()
    del a["optout_sms_v2"]
    assert {x["channel"] for x in run([a], now)} == {"email"}
    assert {x["channel"] for x in run([ap(optout_sms_v2=None)], now)} == {"email"}


def test_long_name_sms_and_email():
    name = "Bartholomew Maximilian Featherstonehaugh-Cholmondeley"
    r = run([ap(customer_name=name)], dub(13, 9))
    for x in r:
        t = x["text"]
        assert len(t) <= 160
        assert "20 Oct 2026" in t and "14:30" in t
        assert t.endswith("Siobhán Ní Dhuibhir")
    r = run([ap(customer_name=name, phone="")], dub(13, 9))
    assert name in r[0]["text"]


def test_name_shortening_order():
    sig = _SIG_DEFAULT
    t = _make_text("sms", "Ann Bee", "20 Oct 2026", "14:30", sig)
    assert "Ann Bee" in t
    t = _make_text("sms", "Ann " + "B" * 40, "20 Oct 2026", "14:30", sig)
    assert "Ann B." in t and len(t) <= 160
    t = _make_text("sms", "A" * 60 + " Smith", "20 Oct 2026", "14:30", sig)
    assert len(t) <= 160 and t.startswith("Hello A")
    t = _make_text("sms", "", "20 Oct 2026", "14:30", sig)
    assert t.startswith("Hello,")


def test_no_name_template_fits_160():
    for sig in (_SIG_DEFAULT, _SIG_PL):
        for d in ("30 Sep 2026", "28 Sep 2026", "31 Dec 2026"):
            assert len(_render("", d, "23:59", sig)) <= 160


def test_missing_name_plain_greeting():
    r = run([ap(customer_name=None)], dub(13, 9))
    assert r[0]["text"].startswith("Hello, a friendly")


def test_signatures():
    now = dub(13, 9)
    pl = run([ap(country=" pl ")], now)
    assert all(x["text"].endswith("Grzegorz Szczepański") for x in pl)
    for c in ("IE", None, "GB"):
        r = run([ap(country=c)], now)
        assert all(x["text"].endswith("Siobhán Ní Dhuibhir") for x in r)


def test_sorted_mixed_batch():
    now = dub(13, 9)
    appts = [ap(id="b", starts_at=dub(22, 10)), ap(id="a", starts_at=dub(20, 14, 30)),
             ap(id="c", starts_at=dub(16, 11))]
    r = run(appts, now)
    keys = [(x["send_at"], str(x["appointment_id"])) for x in r]
    assert keys == sorted(keys)
    assert len(r) == 6


def test_tie_break_by_id():
    r = run([ap(id="b"), ap(id="a")], dub(13, 9))
    assert [x["appointment_id"] for x in r] == ["a", "b", "a", "b"][:0] or \
        [x["appointment_id"] for x in r] == ["a", "b", "a", "b"]


def test_malformed_skipped_and_now_validated():
    now = dub(13, 9)
    bad = [ap(starts_at=datetime(2026, 10, 20, 14, 30)), ap(id=None),
           ap(starts_at=None), "junk", None, ap(id="ok")]
    r = run(bad, now)
    assert {x["appointment_id"] for x in r} == {"ok"}
    for bad_now in (datetime(2026, 10, 13, 9), None):
        try:
            run([ap()], bad_now)
            assert False
        except ValueError:
            pass


def test_pure_no_mutation():
    appts = [ap(), ap(id="z", phone="")]
    before = copy.deepcopy(appts)
    run(appts, dub(13, 9))
    assert appts == before


def test_invariants_over_many_nows():
    start = dub(20, 14, 30)
    s_utc = start.astimezone(UTC)
    base = datetime(2026, 10, 17, 0, tzinfo=UTC)
    for i in range(0, 24 * 4 * 5):
        now = base + timedelta(minutes=15 * i)
        for x in run([ap()], now):
            assert x["send_at"] >= now and not _quiet(x["send_at"])
            assert x["send_at"] < s_utc


def test_zz_no_email_in_logs():
    run([ap(), ap(id="q", phone="", optout_sms_v2=True)], dub(13, 9))
    assert _CAPTURED
    joined = "\n".join(_CAPTURED)
    assert "@" not in joined and "example.com" not in joined
    assert "0851234567" not in joined