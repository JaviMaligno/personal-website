"""Brennan Opticians appointment reminders: plan_reminders(appointments, now).

Pure planning function (no I/O, no clock reads, no input mutation). The pytest
tests are at the bottom of this module (run: pytest <this file>).
NOTE: this module was written without an execution tool, so the tests have NOT
been run. Run them before relying on this file.

Logging (house rule vs R11): one INFO line per planned reminder with the
appointment_id, channel and send time. The contact itself (email address or
phone number) is deliberately NOT logged, because R11 forbids logging the
customer's email, phone and name. Support traces deliveries via appointment_id.
Skips and errors log only appointment_id and a reason code (never exception
messages).

[ASSUMPTION]s to confirm with the client:
 A1 Second reminder is 2 hours before the appointment (wording was garbled).
 A2 Missing/None optout_sms_v2 means opted out (email, never SMS).
 A3 Date is rendered as "15 Oct 2026" (English, all customers incl. PL).
 A4 Clamping to "now" applies only to the 48h reminder; a 2h reminder whose
    nominal time is already past is dropped.
 A5 Status "cancelled"/"canceled" is matched case-insensitively and trimmed;
    missing status means active.
 A6 Country "PL" is matched case-insensitively and trimmed.
 A7 Dublin time is used for all customers, including PL.
Open questions: confirm 2h; quiet-hours fallback (defer to next 08:00 when the
20:00 point has passed); 160 chars vs GSM-7/UCS-2 segmenting given diacritics
(Siobhan/Grzegorz signatures force UCS-2 -> 70 chars/segment); language and
date format for PL; Dublin vs Warsaw for PL; invocation frequency and
de-duplication (caller's responsibility); missing opt-out flag treatment.
"""
from __future__ import annotations

import logging
import unicodedata
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOG = logging.getLogger("brennan_opticians.reminders")
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX = 160
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = unicodedata.normalize("NFC", "Siobhán Ní Dhuibhir")
_SIG_PL = unicodedata.normalize("NFC", "Grzegorz Szczepański")
_CANCELLED = {"cancelled", "canceled"}


def _get(a, key):
    if isinstance(a, Mapping):
        return a.get(key)
    return getattr(a, key, None)


def _clean(v) -> str:
    return "" if v is None else str(v).strip()


def _safe_id(a) -> str:
    try:
        v = _get(a, "id")
        return "<missing>" if v is None else str(v)
    except Exception:
        return "<unknown>"


def _quiet(dt: datetime) -> bool:
    h = dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _back_to_20(t: datetime) -> datetime:
    local = t.astimezone(DUBLIN)
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    return datetime(day.year, day.month, day.day, 20, tzinfo=DUBLIN).astimezone(UTC)


def _next_8(t: datetime) -> datetime:
    local = t.astimezone(DUBLIN)
    day = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    return datetime(day.year, day.month, day.day, 8, tzinfo=DUBLIN).astimezone(UTC)


def _build_text(name: str, start_local: datetime, sig: str) -> str:
    date = f"{start_local.day} {_MONTHS[start_local.month - 1]} {start_local.year}"
    hhmm = f"{start_local.hour:02d}:{start_local.minute:02d}"
    greeting = f"Hi {name}," if name else "Hi,"
    text = (f"{greeting} reminder of your Brennan Opticians appointment "
            f"on {date} at {hhmm}. {sig}")
    return unicodedata.normalize("NFC", text).rstrip()


def _name_candidates(raw) -> list[str]:
    words = _clean(raw).split()
    if not words:
        return [""]
    cands = [" ".join(words)]
    if len(words) > 1:
        cands.append(f"{words[0]} {words[-1][0]}")
    cands += [words[0], words[0][0], ""]
    return list(dict.fromkeys(cands))


def _plan_one(a, n: datetime) -> list[tuple[datetime, dict]]:
    aid = _get(a, "id")
    if aid is None or not str(aid).strip():
        LOG.warning("appointment_id=<missing> skipped reason=missing_id")
        return []
    if _clean(_get(a, "status")).lower() in _CANCELLED:
        LOG.info("appointment_id=%s skipped reason=cancelled", aid)
        return []
    starts = _get(a, "starts_at")
    if (not isinstance(starts, datetime) or starts.tzinfo is None
            or starts.utcoffset() is None):
        LOG.warning("appointment_id=%s skipped reason=invalid_starts_at", aid)
        return []
    start = starts.astimezone(UTC)
    if start <= n:
        LOG.info("appointment_id=%s skipped reason=already_started", aid)
        return []

    phone = _clean(_get(a, "phone"))
    email = _clean(_get(a, "email"))
    optout = _get(a, "optout_sms_v2")
    opted_out = optout is None or bool(optout)
    channel = "sms" if phone and not opted_out else "email"
    if channel == "email" and not email:
        LOG.warning("appointment_id=%s skipped reason=no_destination", aid)
        return []

    sig = _SIG_PL if _clean(_get(a, "country")).upper() == "PL" else _SIG_DEFAULT
    start_local = start.astimezone(DUBLIN)
    cands = _name_candidates(_get(a, "customer_name"))
    if channel == "email":
        text = _build_text(cands[0], start_local, sig)
    else:
        text = ""
        for c in cands:
            text = _build_text(c, start_local, sig)
            if len(text) <= SMS_MAX:
                break

    def adjust(t: datetime):
        if _quiet(t):
            t = _back_to_20(t)
        if t < n:
            t = _next_8(n) if _quiet(n) else n
        return t if t < start else None

    # 2h path first (priority), no clamping.
    t2 = start - timedelta(hours=2)
    s2 = adjust(t2) if t2 >= n else None
    t48 = max(start - timedelta(hours=48), n)
    s48 = adjust(t48)
    if s2 is not None and s48 is not None and s2 == s48:
        s48 = None

    out = []
    for s in (s48, s2):
        if s is None:
            continue
        local = s.astimezone(DUBLIN)
        LOG.info("reminder planned appointment_id=%s channel=%s send_at=%s",
                 aid, channel, local.isoformat())
        out.append((s, {"appointment_id": aid, "channel": channel,
                        "send_at": local, "text": text}))
    return out


def plan_reminders(appointments, now):
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        raise ValueError("now must be a timezone-aware datetime")
    n = now.astimezone(UTC)
    rows = []
    for i, a in enumerate(appointments):
        try:
            items = _plan_one(a, n)
        except Exception as exc:
            LOG.warning("appointment_id=%s skipped reason=error:%s",
                        _safe_id(a), type(exc).__name__)
            items = []
        for utc, rem in items:
            rows.append((utc, str(rem["appointment_id"]), i, rem))
    rows.sort(key=lambda r: r[:3])
    return [r[3] for r in rows]


# ----------------------------------------------------------------- tests ---
import copy  # noqa: E402

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
START = datetime(2026, 10, 20, 14, 0, tzinfo=UTC)  # 15:00 IST
EMAIL = "secret.person@example.com"
PHONE = "0851234567"


def appt(**kw):
    d = {"id": "a1", "customer_name": "Mary Murphy", "email": EMAIL,
         "phone": PHONE, "country": "IE", "status": "booked",
         "starts_at": START, "optout_sms_v2": False}
    d.update(kw)
    return d


def test_two_hour_reminder_first():
    out = plan_reminders([appt()], NOW)
    last = out[-1]
    assert last["send_at"].astimezone(UTC) == START - timedelta(hours=2)
    assert last["send_at"].hour == 13  # 12:00 UTC in IST


def test_basic_shape_and_text():
    out = plan_reminders([appt()], NOW)
    assert len(out) == 2
    for r in out:
        assert set(r) == {"appointment_id", "channel", "send_at", "text"}
        assert r["send_at"].tzinfo is DUBLIN
        assert r["text"] == unicodedata.normalize(
            "NFC", "Hi Mary Murphy, reminder of your Brennan Opticians "
            "appointment on 20 Oct 2026 at 15:00. Siobhán Ní Dhuibhir")
        assert "hours" not in r["text"]
        assert EMAIL not in repr(r)
    assert out[0]["send_at"].astimezone(UTC) == START - timedelta(hours=48)
    assert plan_reminders([], NOW) == []


def test_naive_now_raises():
    try:
        plan_reminders([], datetime(2026, 10, 1, 12, 0))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_channel_table():
    cases = [
        ("0851", False, "e@x.ie", "sms"), ("0851", True, "e@x.ie", "email"),
        ("0851", None, "e@x.ie", "email"), (" ", False, "e@x.ie", "email"),
        (None, False, "e@x.ie", "email"), ("", True, "e@x.ie", "email"),
        ("0851", False, None, "sms"), ("0851", True, None, None),
        (None, False, " ", None),
    ]
    for phone, opt, email, exp in cases:
        out = plan_reminders(
            [appt(phone=phone, optout_sms_v2=opt, email=email)], NOW)
        if exp is None:
            assert out == [], (phone, opt, email)
        else:
            assert len(out) == 2 and {r["channel"] for r in out} == {exp}
    a = appt()
    del a["optout_sms_v2"]
    assert {r["channel"] for r in plan_reminders([a], NOW)} == {"email"}


def test_opt_out_legacy_field_never_read():
    class Guard(dict):
        def get(self, key, default=None):
            if key == "opt_out":
                raise AssertionError("opt_out read")
            return super().get(key, default)
    out = plan_reminders([Guard(appt(opt_out=True))], NOW)
    assert {r["channel"] for r in out} == {"sms"}


def test_same_instant_different_zones():
    tokyo = ZoneInfo("Asia/Tokyo")
    a = plan_reminders([appt(starts_at=START)], NOW)
    b = plan_reminders([appt(starts_at=START.astimezone(tokyo))],
                       NOW.astimezone(tokyo))
    assert a == b


def test_dst_elapsed_48h():
    start = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)  # 10:00 GMT
    out = plan_reminders([appt(starts_at=start)], NOW)
    assert out[0]["send_at"].astimezone(UTC) == datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
    assert out[0]["send_at"].hour == 11
    start = datetime(2027, 3, 29, 10, 0, tzinfo=UTC)  # 11:00 IST
    out = plan_reminders([appt(starts_at=start)],
                         datetime(2027, 3, 1, tzinfo=UTC))
    assert out[0]["send_at"].astimezone(UTC) == datetime(2027, 3, 27, 10, 0, tzinfo=UTC)
    assert out[0]["send_at"].hour == 10


def _two_hour_send(y, mo, d, h, mi):
    nominal = datetime(y, mo, d, h, mi, tzinfo=DUBLIN).astimezone(UTC)
    out = plan_reminders(
        [appt(starts_at=nominal + timedelta(hours=2))],
        nominal - timedelta(days=10))
    return out[-1]["send_at"]


def test_quiet_hour_boundaries_and_dst():
    cases = [
        ((2026, 11, 10, 22, 30), (2026, 11, 10, 20, 0)),
        ((2026, 11, 10, 6, 0), (2026, 11, 9, 20, 0)),
        ((2026, 11, 10, 8, 0), (2026, 11, 10, 8, 0)),
        ((2026, 11, 10, 20, 59), (2026, 11, 10, 20, 59)),
        ((2026, 11, 10, 21, 0), (2026, 11, 10, 20, 0)),
        ((2026, 11, 10, 7, 59), (2026, 11, 9, 20, 0)),
        ((2026, 11, 10, 0, 0), (2026, 11, 9, 20, 0)),
        ((2026, 10, 25, 6, 0), (2026, 10, 24, 20, 0)),
        ((2026, 10, 25, 22, 30), (2026, 10, 25, 20, 0)),
        ((2027, 3, 28, 6, 0), (2027, 3, 27, 20, 0)),
        ((2027, 3, 28, 22, 30), (2027, 3, 28, 20, 0)),
    ]
    for nominal, exp in cases:
        got = _two_hour_send(*nominal)
        want = datetime(*exp, tzinfo=DUBLIN)
        assert got.astimezone(UTC) == want.astimezone(UTC), (nominal, got)
        assert got.utcoffset() == want.utcoffset()


def test_long_name_sms_longest_signature():
    sig = unicodedata.normalize("NFC", "Grzegorz Szczepański")
    name = "Alexander " + "S" * 190
    assert len(name) == 200
    out = plan_reminders([appt(customer_name=name, country=" pl ")], NOW)
    for r in out:
        assert len(r["text"]) <= 160 and r["text"].endswith(sig)
        assert r["text"].startswith("Hi Alexander S, reminder")
        assert "20 Oct 2026 at 15:00" in r["text"]
    em = plan_reminders([appt(customer_name=name, country="PL",
                              optout_sms_v2=True)], NOW)
    assert name in em[0]["text"] and em[0]["channel"] == "email"
    t = plan_reminders([appt(customer_name="F" * 60 + " " + "S" * 100,
                             country="PL")], NOW)[0]["text"]
    assert t.startswith("Hi " + "F" * 60 + " S,") and len(t) <= 160
    t = plan_reminders([appt(customer_name="F" * 62 + " " + "S" * 100,
                             country="PL")], NOW)[0]["text"]
    assert t.startswith("Hi " + "F" * 62 + ",") and len(t) <= 160
    t = plan_reminders([appt(customer_name="F" * 100, country="PL")], NOW)[0]["text"]
    assert t.startswith("Hi F,") and len(t) <= 160


def test_blank_name_and_whitespace():
    for nm in (None, "", "   "):
        t = plan_reminders([appt(customer_name=nm)], NOW)[0]["text"]
        assert t.startswith("Hi, reminder of")
    t = plan_reminders([appt(customer_name="  Mary   Murphy ")], NOW)[0]["text"]
    assert t.startswith("Hi Mary Murphy,")


def test_signatures():
    for country, sig in (("PL", "Grzegorz Szczepański"), (" pl ", "Grzegorz Szczepański"),
                         ("IE", "Siobhán Ní Dhuibhir"), (None, "Siobhán Ní Dhuibhir")):
        want = unicodedata.normalize("NFC", sig)
        for r in plan_reminders([appt(country=country)], NOW):
            assert r["text"].endswith(want) and r["text"] == r["text"].rstrip()
            assert unicodedata.is_normalized("NFC", r["text"])


def test_cancelled():
    for st in ("cancelled", " Cancelled ", "CANCELED"):
        assert plan_reminders([appt(status=st)], NOW) == []
    assert len(plan_reminders([appt(status=None)], NOW)) == 2


def test_sorting():
    tokyo = ZoneInfo("Asia/Tokyo")
    early = START - timedelta(days=3)
    out = plan_reminders([
        appt(id="b"), appt(id="a"),
        appt(id="c", starts_at=early.astimezone(tokyo))], NOW)
    keys = [(r["send_at"].astimezone(UTC), r["appointment_id"]) for r in out]
    assert keys == sorted(keys)
    ids = [r["appointment_id"] for r in out if r["send_at"].astimezone(UTC) == START - timedelta(hours=48)]
    assert ids == ["a", "b"]
    dup = plan_reminders([appt(id="z", customer_name="First"),
                          appt(id="z", customer_name="Second")], NOW)
    assert dup[0]["text"].startswith("Hi First") and dup[1]["text"].startswith("Hi Second")


def test_late_first_reminder():
    start = NOW + timedelta(hours=10)
    out = plan_reminders([appt(starts_at=start)], NOW)
    assert [r["send_at"].astimezone(UTC) for r in out] == [
        NOW, datetime(2026, 10, 1, 19, 0, tzinfo=UTC)]


def test_r17_branches():
    # start <= now
    assert plan_reminders([appt(starts_at=NOW)], NOW) == []
    assert plan_reminders([appt(starts_at=NOW - timedelta(hours=1))], NOW) == []
    # 2h nominal past -> dropped; 48h clamped to now
    out = plan_reminders([appt(starts_at=NOW + timedelta(hours=1))], NOW)
    assert [r["send_at"].astimezone(UTC) for r in out] == [NOW]
    # now in quiet hours (23:00 IST): 48h deferred to next 08:00, 2h back to 20:00
    now = datetime(2026, 10, 1, 22, 0, tzinfo=UTC)
    out = plan_reminders([appt(starts_at=now + timedelta(hours=30))], now)
    assert [r["send_at"].astimezone(UTC) for r in out] == [
        datetime(2026, 10, 2, 7, 0, tzinfo=UTC), datetime(2026, 10, 2, 19, 0, tzinfo=UTC)]
    # now at 06:00 IST: deferred to 08:00 same day
    now = datetime(2026, 10, 1, 5, 0, tzinfo=UTC)
    out = plan_reminders([appt(starts_at=now + timedelta(hours=20))], now)
    assert out[0]["send_at"].astimezone(UTC) == datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
    assert len(out) == 2
    # deferred time >= start -> both dropped
    now = datetime(2026, 10, 1, 22, 0, tzinfo=UTC)
    assert plan_reminders([appt(starts_at=now + timedelta(hours=3))], now) == []
    # identical send_at -> only the 2h one
    start = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)
    out = plan_reminders([appt(starts_at=start)], now)
    assert [r["send_at"].astimezone(UTC) for r in out] == [
        datetime(2026, 10, 2, 7, 0, tzinfo=UTC)]
    # adjusted < now, now outside quiet -> send at now; duplicates collapse
    now = datetime(2026, 10, 1, 19, 30, tzinfo=UTC)  # 20:30 IST
    out = plan_reminders([appt(starts_at=datetime(2026, 10, 1, 23, 0, tzinfo=UTC))], now)
    assert [r["send_at"].astimezone(UTC) for r in out] == [now]


def test_output_invariants_grid():
    base = datetime(2026, 10, 23, 0, 0, tzinfo=UTC)
    for k in range(0, 5 * 24 * 60, 97):
        now = base + timedelta(minutes=k)
        for off in (1, 3, 10, 30, 50, 100):
            start = now + timedelta(hours=off, minutes=13)
            out = plan_reminders([appt(starts_at=start)], now)
            assert out
            seen = set()
            for r in out:
                s = r["send_at"]
                assert s.astimezone(UTC) >= now and s.astimezone(UTC) < start
                assert 8 <= s.hour < 21
                seen.add(s.astimezone(UTC))
            assert len(seen) == len(out)


def test_invalid_appointments_do_not_fail_batch(caplog):
    caplog.set_level(logging.DEBUG)
    bad = [appt(id=None), appt(id=""), appt(starts_at=None),
           appt(starts_at=datetime(2026, 10, 20, 14, 0)),
           appt(starts_at="2026-10-20"),
           appt(id="noaddr", optout_sms_v2=True, email=None),
           appt(id="nophone", phone=None, email="")]
    out = plan_reminders(bad + [appt(id="ok")], NOW)
    assert {r["appointment_id"] for r in out} == {"ok"}
    assert "noaddr" in caplog.text and "no_destination" in caplog.text


def test_inputs_not_mutated():
    items = [appt(id="b"), appt(id="a", customer_name=None)]
    before = copy.deepcopy(items)
    plan_reminders(items, NOW)
    assert items == before


def test_no_email_in_logs_or_output(caplog, capsys):
    caplog.set_level(logging.DEBUG)

    class Boom(dict):
        def get(self, key, default=None):
            if key == "country":
                raise RuntimeError(f"cannot read {EMAIL}")
            return super().get(key, default)

    items = [
        appt(id="sms"), appt(id="mail", optout_sms_v2=True),
        appt(id="canc", status="cancelled"),
        appt(id="past", starts_at=NOW - timedelta(days=1)),
        appt(id="naive", starts_at=datetime(2026, 10, 20, 14, 0)),
        appt(id="str", starts_at="tomorrow"), appt(id=None),
        appt(id="noaddr", optout_sms_v2=True, email=None),
        Boom(appt(id="boom")),
    ]
    out = plan_reminders(items, NOW)
    try:
        plan_reminders(items, datetime(2026, 10, 1))
    except ValueError as exc:
        assert EMAIL not in str(exc) and EMAIL not in repr(exc)
    captured = capsys.readouterr()
    assert {r["appointment_id"] for r in out} == {"sms", "mail"}
    for blob in (caplog.text, captured.out, captured.err, repr(out)):
        assert EMAIL not in blob
    for rec in caplog.records:
        assert EMAIL not in rec.getMessage() and EMAIL not in str(rec.args)
    assert PHONE not in caplog.text and "Mary" not in caplog.text
    assert "boom" in caplog.text
    assert sum(1 for r in caplog.records if r.getMessage().startswith("reminder planned")) == 4