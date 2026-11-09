"""Brennan Opticians appointment reminders.

Public entry point: plan_reminders(appointments, now).

Run the tests (pytest is only needed for the tests; the module itself is stdlib only):
    python -m pytest reminders.py

Judgement calls for the client to confirm:
  * Rule 4(c) fallback: when the moved-back 20:00 time is already in the past,
    the reminder moves forward to the next 08:00 Dublin time after the quiet-hours
    time. The 2h reminder may therefore arrive up to a few hours before the
    appointment, and is dropped if 08:00 is not before the start.
  * All times, including for Polish (PL) customers, use Europe/Dublin. A PL
    customer's text shows Dublin local time, not Warsaw time.
  * "n with acute" (U+0144) in the PL signature, and fadas (a, e, i, o, u with
    acute) in Irish names, force SMS into UCS-2 (non-GSM) encoding. Carriers may
    then split messages at 70 characters per segment, so a 160 code point SMS
    can be billed or delivered as several parts.
  * House rule vs privacy: the per-reminder INFO line records appointment id,
    reminder kind, channel and the contact kind ("phone" or "email"), but never
    the phone number or email address, because the DPC audit forbids logging email.
  * Cancelled appointments are skipped before malformed-record checks, so a
    cancelled record with no starts_at is skipped silently.
  * Greeting, text template and separator (a single space before the signature)
    are my choice; the date is "15 Oct 2026" with an unpadded day.
"""
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_LENGTH = 160
SIGNATURE_DEFAULT = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepa\u0144ski"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _present(v):
    return v is not None and str(v).strip() != ""


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _at(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN)


def _adjust(t, first, now, start):
    """Apply rules 4(a)-(d) to one instant (all UTC). Return UTC instant or None."""
    if t < now:
        if not first:
            return None
        t = now
    local = t.astimezone(DUBLIN)
    if local.hour >= QUIET_START_HOUR or local.hour < QUIET_END_HOUR:
        if local.hour >= QUIET_START_HOUR:
            moved = _at(local.date(), 20)
            next_morning = _at(local.date() + timedelta(days=1), QUIET_END_HOUR)
        else:
            moved = _at(local.date() - timedelta(days=1), 20)
            next_morning = _at(local.date(), QUIET_END_HOUR)
        local = moved if moved.astimezone(UTC) >= now else next_morning
    final = local.astimezone(UTC)
    return None if final >= start else final


def _candidates(name):
    name = re.sub(r"\s+", " ", _nfc(str(name or ""))).strip()
    if not name:
        return [None]
    parts = name.split(" ")
    out = [name]
    if len(parts) > 1:
        out.append(f"{parts[0]} {parts[-1][0]}.")
    out += [parts[0], parts[0][0], None]
    return out


def _build_text(name, date_s, time_s, sig, sms):
    for cand in _candidates(name):
        greeting = f"Hi {cand}," if cand else "Hello,"
        text = _nfc(f"{greeting} your Brennan Opticians appointment is on "
                    f"{date_s} at {time_s}. {sig}")
        if not sms or len(text) <= SMS_MAX_LENGTH:
            return text
    return text  # neutral greeting always fits


def _plan_one(appt, now):
    status = str(appt.get("status") or "").strip().lower()
    if status in ("cancelled", "canceled"):
        return []
    appt_id = appt.get("id")
    starts_at = appt.get("starts_at")
    if appt_id is None or not _is_aware(starts_at):
        logger.warning("Skipping malformed appointment id=%s", appt_id)
        return []
    start = starts_at.astimezone(UTC)
    if start <= now:
        return []

    if _present(appt.get("phone")) and appt.get("optout_sms_v2") is False:
        channel, contact = "sms", "phone"
    elif _present(appt.get("email")):
        channel, contact = "email", "email"
    else:
        logger.warning("No usable contact channel for appointment id=%s", appt_id)
        return []

    local_start = start.astimezone(DUBLIN)
    date_s = f"{local_start.day} {MONTHS[local_start.month - 1]} {local_start.year}"
    time_s = f"{local_start.hour:02d}:{local_start.minute:02d}"
    sig = SIGNATURE_PL if str(appt.get("country") or "").strip().upper() == "PL" \
        else SIGNATURE_DEFAULT
    text = _build_text(appt.get("customer_name"), date_s, time_s, sig, channel == "sms")

    first = _adjust(start - timedelta(hours=48), True, now, start)
    second = _adjust(start - timedelta(hours=2), False, now, start)
    if first is not None and second is not None and first >= second:
        first = None
    out = []
    for kind, when in (("48h", first), ("2h", second)):
        if when is None:
            continue
        logger.info("Planned %s reminder for appointment id=%s via %s (%s on file)",
                    kind, appt_id, channel, contact)
        out.append({"appointment_id": appt_id, "channel": channel,
                    "send_at": when.astimezone(DUBLIN), "text": text})
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    result = []
    for appt in appointments:
        if not isinstance(appt, dict):
            logger.warning("Skipping malformed appointment id=%s", None)
            continue
        result.extend(_plan_one(appt, now_utc))
    result.sort(key=lambda r: r["send_at"])  # stable
    return result


# ----------------------------------------------------------------- tests ---
import copy  # noqa: E402
import logging as _logging  # noqa: E402

MARKER = "zz-marker-7431@pii.example"


def _d(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def _appt(**kw):
    base = dict(id="A1", customer_name="Mary O'Brien", email="m@example.com",
                phone="0851234567", country="IE", status="booked",
                starts_at=_d(2026, 11, 10, 14, 30), optout_sms_v2=False)
    base.update(kw)
    return base


def test_naive_now_raises():
    try:
        plan_reminders([], datetime(2026, 11, 1))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_normal_case_and_no_mutation():
    a = [_appt()]
    before = copy.deepcopy(a)
    r = plan_reminders(a, _d(2026, 11, 1, 12))
    assert [x["send_at"] for x in r] == [_d(2026, 11, 8, 14, 30), _d(2026, 11, 10, 12, 30)]
    assert all(x["send_at"].tzinfo == DUBLIN for x in r)
    assert "10 Nov 2026" in r[0]["text"] and "14:30" in r[0]["text"]
    assert r[0]["text"].endswith(SIGNATURE_DEFAULT)
    assert a == before


def test_quiet_hours_move_back():
    r = plan_reminders([_appt(starts_at=_d(2026, 11, 20, 9))], _d(2026, 11, 1))
    assert [x["send_at"] for x in r] == [_d(2026, 11, 18, 9), _d(2026, 11, 19, 20)]


def test_now_in_quiet_hours_forward_to_0800():
    now = _d(2026, 11, 9, 22)
    r = plan_reminders([_appt(starts_at=_d(2026, 11, 10, 9))], now)
    assert len(r) == 1 and r[0]["send_at"] == _d(2026, 11, 10, 8)
    assert plan_reminders([_appt(starts_at=_d(2026, 11, 10, 7, 30))], now) == []


def test_between_2h_point_and_start():
    now = _d(2026, 11, 10, 13)
    r = plan_reminders([_appt()], now)
    assert len(r) == 1 and r[0]["send_at"] == now


def test_dst_changeover():
    r = plan_reminders([_appt(starts_at=_d(2026, 10, 26, 10))], _d(2026, 10, 1))
    assert r[0]["send_at"] == _d(2026, 10, 24, 11)
    r = plan_reminders([_appt(starts_at=_d(2026, 10, 25, 3))], _d(2026, 10, 1))
    assert r[-1]["send_at"] == _d(2026, 10, 24, 20)
    assert r[-1]["send_at"].utcoffset() == timedelta(hours=1)


def test_channel_matrix():
    now = _d(2026, 11, 1)
    cases = [
        (dict(), "sms"),
        (dict(optout_sms_v2=True), "email"),
        (dict(optout_sms_v2=True, email=None), None),
        (dict(phone=None), "email"),
        (dict(phone="  "), "email"),
        (dict(phone=None, email=""), None),
        (dict(opt_out=True, optout_sms_v2=False), "sms"),
        (dict(opt_out=False, optout_sms_v2=True), "email"),
        (dict(optout_sms_v2=None), "email"),
    ]
    for kw, expected in cases:
        a = _appt(**kw)
        if kw.get("optout_sms_v2", 0) is None:
            a["optout_sms_v2"] = None
        r = plan_reminders([a], now)
        if expected is None:
            assert r == [], kw
        else:
            assert len(r) == 2 and {x["channel"] for x in r} == {expected}, kw
    a = _appt()
    del a["optout_sms_v2"]
    assert plan_reminders([a], now)[0]["channel"] == "email"


def test_cancelled_and_past():
    now = _d(2026, 11, 1)
    for s in (" Cancelled ", "CANCELED", "cancelled"):
        assert plan_reminders([_appt(status=s)], now) == []
    assert plan_reminders([_appt(starts_at=now)], now) == []
    assert plan_reminders([_appt(starts_at=_d(2026, 10, 1))], now) == []


def test_malformed_skipped_without_blocking(caplog):
    caplog.set_level(_logging.DEBUG)
    bad = [_appt(id="B1", starts_at=datetime(2026, 11, 10, 14, 30)),
           _appt(id="B2", starts_at=None), {"customer_name": "x"}]
    r = plan_reminders(bad + [_appt()], _d(2026, 11, 1))
    assert {x["appointment_id"] for x in r} == {"A1"}
    assert "B1" in caplog.text and "B2" in caplog.text


def test_long_names_sms_length():
    for name in ("Z" * 200, "Mary " + "O" * 195, ("Ab " * 70).strip(), ""):
        for country, sig in (("IE", SIGNATURE_DEFAULT), (" pl ", SIGNATURE_PL)):
            r = plan_reminders([_appt(customer_name=name, country=country)], _d(2026, 11, 1))
            for x in r:
                assert len(x["text"]) <= SMS_MAX_LENGTH
                assert "10 Nov 2026" in x["text"] and "14:30" in x["text"]
                assert x["text"].endswith(sig)
    r = plan_reminders([_appt(customer_name="Mary " + "O" * 195)], _d(2026, 11, 1))
    assert "Mary O." in r[0]["text"]
    r = plan_reminders([_appt(customer_name="Mary " + "O" * 195, phone=None)], _d(2026, 11, 1))
    assert "O" * 195 in r[0]["text"]  # email never shortened


def test_sort_order_and_ties():
    appts = [_appt(id="late", starts_at=_d(2026, 11, 20, 14, 30)),
             _appt(id="t1", starts_at=_d(2026, 11, 10, 14, 30)),
             _appt(id="t2", starts_at=_d(2026, 11, 10, 14, 30))]
    r = plan_reminders(appts, _d(2026, 11, 1))
    keys = [x["send_at"] for x in r]
    assert keys == sorted(keys)
    ids = [x["appointment_id"] for x in r]
    assert ids[:2] == ["t1", "t2"]
    assert ids.index("t1") < ids.index("t2")
    t1 = [x["send_at"] for x in r if x["appointment_id"] == "t1"]
    assert t1 == sorted(t1) and len(t1) == 2


def test_info_log_per_reminder(caplog):
    caplog.set_level(_logging.INFO)
    plan_reminders([_appt()], _d(2026, 11, 1))
    lines = [r for r in caplog.records if r.levelno == _logging.INFO]
    assert len(lines) == 2 and all("A1" in r.getMessage() and "sms" in r.getMessage()
                                   for r in lines)


def test_no_pii_in_logs_or_output(caplog, capsys):
    caplog.set_level(_logging.DEBUG)
    _logging.getLogger().setLevel(_logging.DEBUG)
    now = _d(2026, 11, 1)
    scenarios = [
        _appt(email=MARKER),
        _appt(id="E", email=MARKER, optout_sms_v2=True),
        _appt(id="N", email=MARKER, starts_at=datetime(2026, 11, 10, 14)),
        _appt(id="C", email=MARKER, status="cancelled"),
        _appt(id="X", email=MARKER, phone=None, starts_at=None),
        _appt(id="P", email=MARKER, starts_at=_d(2026, 10, 1)),
        _appt(id="Q", email=MARKER, phone=None, optout_sms_v2=True, customer_name="Q" * 200),
    ]
    plan_reminders(scenarios, now)
    try:
        plan_reminders(scenarios, datetime(2026, 11, 1))
    except ValueError as e:
        assert MARKER not in str(e) and MARKER not in repr(e)
    out = capsys.readouterr()
    assert MARKER not in out.out and MARKER not in out.err
    assert MARKER not in caplog.text
    for rec in caplog.records:
        assert MARKER not in rec.getMessage()
        assert MARKER not in str(rec.args) and MARKER not in repr(rec.args)
        assert MARKER not in str(rec.exc_text) and MARKER not in repr(rec.__dict__)