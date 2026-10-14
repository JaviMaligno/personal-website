"""Brennan Opticians appointment reminders (Python 3.12, standard library only).

Module path: brennan_reminders.py. Pytest tests are included at the bottom of this
module (run with: pytest brennan_reminders.py).

Decisions
- send_at values are tz-aware UTC. Offsets (48h/2h) are absolute durations in UTC;
  quiet hours and text formatting use Europe/Dublin local time.
- Only optout_sms_v2 is read. It is true only for bool True or the strings
  "true"/"1" (case-insensitive, trimmed). A missing key means False.
- Date format in text is DD/MM/YYYY (client question Q5).
- Logging: one INFO line per planned reminder with appointment id, channel and a
  MASKED contact (e.g. "m***@example.com", "***67"). Full email, phone and name are
  never logged (R11 overrides logging the raw contact). Skips log the id and reason
  only. Exceptions log the id and exception type only.
- Quiet-hours moves follow D1/D2 (back to 20:00, else forward to 08:00, dropped if
  not before the start). D3/D4 collapse overdue or identical reminders to the 2h one.

OPEN QUESTIONS FOR CLIENT
Q1. Is the second reminder really 2 hours before? (assumption from garbled wording and the later mention of "the 2-hour reminder").
Q2. When an immediate send (48h already passed) falls in quiet hours, is moving forward to next 08:00 acceptable (instead of dropping), and should it be dropped if that is after the appointment starts?
Q3. For early appointments (e.g. 09:00), is a 2h reminder at 20:00 the previous evening (13 hours ahead) acceptable, given it is then not really a 2-hour reminder?
Q4. If a customer is opted out of SMS and has no email, should we skip silently (current) or alert staff?
Q5. Date format in the text (DD/MM/YYYY vs. e.g. "Mon 5 Nov") and wording/language for the Polish branch (should PL texts be in Polish?).
Q6. If both reminders are overdue, is a single reminder acceptable?
Q7. Is optout_sms_v2 meant to block only SMS (assumed) or also email?
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

FIRST_REMINDER_HOURS = 48
# UNCONFIRMED ASSUMPTION: the second reminder is 2 hours before (client question Q1).
SECOND_REMINDER_HOURS = 2
SMS_MAX_LEN = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
BUSINESS_TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIGNATURES = {"default": "Siobhán Ní Dhuibhir", "PL": "Grzegorz Szczepański"}
_LEADS = {"first": "Reminder", "second": "Final reminder"}


def _nfc(s) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip()


def _signature(country) -> str:
    return _nfc(SIGNATURES["PL"] if country == "PL" else SIGNATURES["default"])


def _is_quiet(local_dt: datetime) -> bool:
    t = local_dt.timetz().replace(tzinfo=None)
    return t >= QUIET_START or t < QUIET_END


def _adjust_quiet(dt: datetime, now: datetime, starts_at: datetime) -> datetime | None:
    """Return dt (UTC) if allowed; else previous 20:00 local; if that is before now,
    next 08:00 local, or None when that is not before starts_at."""
    local = dt.astimezone(BUSINESS_TZ)
    if not _is_quiet(local):
        return dt.astimezone(UTC)
    late = local.time() >= QUIET_START
    day = local.date()
    back_day = day if late else day - timedelta(days=1)
    back = datetime.combine(back_day, time(20, 0), BUSINESS_TZ).astimezone(UTC)
    if back >= now:
        return back
    fwd_day = day + timedelta(days=1) if late else day
    fwd = datetime.combine(fwd_day, QUIET_END, BUSINESS_TZ).astimezone(UTC)
    return fwd if fwd < starts_at else None


def _optout(appt: dict) -> bool:
    v = appt.get("optout_sms_v2")
    if v is True:
        return True
    return isinstance(v, str) and v.strip().lower() in ("true", "1")


def _choose_channel(appt: dict):
    """Return (channel, contact) or None."""
    phone = _nfc(appt.get("phone"))
    email = _nfc(appt.get("email"))
    if phone and not _optout(appt):
        return "sms", phone
    if email:
        return "email", email
    return None


def _mask(channel: str, contact: str) -> str:
    if channel == "email":
        local, _, domain = contact.partition("@")
        return f"{local[:1]}***@{domain}"
    return "***" + contact[-2:]


def _shorten_sms(name: str, lead: str, d: str, t: str, sig: str) -> str:
    first = name.split()[0] if name else ""
    greetings = [f"Hi {n}," for n in (name, first, first[:1] + "." if first else "") if n.strip(".")]
    greetings.append("Hi,")
    cands = [f"{g} {lead.lower() if False else lead}: your Brennan Opticians appointment is on {d} at {t}. {sig}"
             for g in greetings]
    cands += [f"{lead}: Brennan Opticians appointment on {d} at {t}. {sig}",
              f"{lead}: appointment on {d} at {t}. {sig}",
              f"Appointment {d} {t}. {sig}"]
    for c in cands:
        if len(c) <= SMS_MAX_LEN:
            return c
    return cands[-1]


def _build_text(appt: dict, when: datetime, channel: str, kind: str) -> str:
    """`when` is the appointment start. Date/time are rendered in Dublin local time."""
    local = when.astimezone(BUSINESS_TZ)
    d, t = local.strftime("%d/%m/%Y"), local.strftime("%H:%M")
    lead, sig, name = _LEADS[kind], _signature(appt.get("country")), _nfc(appt.get("customer_name"))
    if channel == "sms":
        return _shorten_sms(name, lead, d, t, sig)
    greet = f"Hi {name}," if name else "Hi,"
    return f"{greet} {lead}: your Brennan Opticians appointment is on {d} at {t}. {sig}"


def _plan_one(appt: dict, now: datetime) -> list[dict]:
    aid = appt.get("id")
    if str(appt.get("status") or "").strip().lower() == "cancelled":
        log.info("appointment %s cancelled: no reminders", aid)
        return []
    starts = appt.get("starts_at")
    if not isinstance(starts, datetime) or starts.tzinfo is None:
        log.info("appointment %s skipped: starts_at missing or naive", aid)
        return []
    if starts <= now:
        log.info("appointment %s skipped: already started", aid)
        return []
    chosen = _choose_channel(appt)
    if chosen is None:
        log.info("appointment %s skipped: no usable channel", aid)
        return []
    channel, contact = chosen
    adj = {}
    for kind, hours in (("first", FIRST_REMINDER_HOURS), ("second", SECOND_REMINDER_HOURS)):
        raw = max(starts - timedelta(hours=hours), now)
        res = _adjust_quiet(raw, now, starts)
        if res is None:
            log.info("appointment %s: %s reminder dropped (no valid time before start)", aid, kind)
        else:
            adj[kind] = res
    if "first" in adj and "second" in adj and adj["first"] >= adj["second"]:
        log.info("appointment %s: first reminder collapsed into second", aid)
        del adj["first"]
    out = []
    for kind, when in adj.items():
        out.append({"appointment_id": aid, "channel": channel, "send_at": when,
                    "text": _build_text(appt, starts, channel, kind), "_k": 0 if kind == "first" else 1})
        log.info("planned %s reminder for appointment %s via %s to %s at %s",
                 kind, aid, channel, _mask(channel, contact), when.isoformat())
    return out


def plan_reminders(appointments: list[dict], now: datetime) -> list[dict]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    res = []
    for appt in appointments:
        try:
            res.extend(_plan_one(appt, now))
        except Exception as exc:  # never log the message: it may contain PII
            log.warning("appointment %s failed: %s", appt.get("id") if isinstance(appt, dict) else None,
                        type(exc).__name__)
    res.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["_k"]))
    for r in res:
        del r["_k"]
    return res


# ----------------------------- tests (pytest) -----------------------------
NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
S = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def mk(**kw):
    a = {"id": "a1", "customer_name": "Mary Byrne", "email": "mary@example.com",
         "phone": "+353871234567", "country": "IE", "status": "booked",
         "starts_at": S, "optout_sms_v2": False}
    a.update(kw)
    return a


def U(*a):
    return datetime(*a, tzinfo=UTC)


def test_r1_shape():
    out = plan_reminders([mk()], NOW)
    assert len(out) == 2
    for r in out:
        assert set(r) == {"appointment_id", "channel", "send_at", "text"}
        assert r["channel"] in ("sms", "email") and r["send_at"].tzinfo is not None


def test_r3_only_v2_flag():
    assert plan_reminders([mk(opt_out=True)], NOW)[0]["channel"] == "sms"
    assert plan_reminders([mk(opt_out=False, optout_sms_v2=True)], NOW)[0]["channel"] == "email"
    assert plan_reminders([mk(optout_sms_v2="TRUE")], NOW)[0]["channel"] == "email"
    assert plan_reminders([mk(optout_sms_v2="no")], NOW)[0]["channel"] == "sms"


def test_r4_constants_and_timing():
    assert FIRST_REMINDER_HOURS == 48 and SECOND_REMINDER_HOURS == 2
    a, b = plan_reminders([mk()], NOW)
    assert a["send_at"] == S - timedelta(hours=48) and b["send_at"] == S - timedelta(hours=2)


def test_r5_never_in_past():
    for m in range(1, 3000, 37):
        starts = NOW + timedelta(minutes=m)
        for r in plan_reminders([mk(starts_at=starts)], NOW):
            assert NOW <= r["send_at"] < starts
    r = plan_reminders([mk(starts_at=NOW + timedelta(hours=10))], NOW)
    assert r[0]["send_at"] == NOW


def test_r6_matrix():
    for phone in ("+353871", "", None):
        for opt in (False, True, None):
            for email in ("a@b.ie", "", None):
                out = plan_reminders([mk(phone=phone, optout_sms_v2=opt, email=email)], NOW)
                if phone and not opt:
                    exp = "sms"
                elif email:
                    exp = "email"
                else:
                    exp = None
                assert {r["channel"] for r in out} == ({exp} if exp else set())


def test_r7_sms_length():
    base = len(_build_text(mk(customer_name="A"), S, "sms", "first"))
    k = 160 - base + 1
    t160 = _build_text(mk(customer_name="A" * k), S, "sms", "first")
    assert len(t160) == 160 and "A" * k in t160
    t161 = _build_text(mk(customer_name="A" * (k + 1)), S, "sms", "first")
    assert len(t161) <= 160 and "A" * (k + 1) not in t161
    t = _build_text(mk(customer_name="Bartholomew " * 30), S, "sms", "second")
    assert len(t) <= 160 and "15/07/2026" in t and "13:00" in t and t.endswith("Siobhán Ní Dhuibhir")
    assert len(_build_text(mk(customer_name="B" * 400), S, "email", "first")) > 160


def test_r8_local_time():
    assert "at 13:00" in plan_reminders([mk()], NOW)[0]["text"]  # IST
    w = mk(starts_at=U(2026, 1, 15, 13, 0))
    assert "at 13:00" in plan_reminders([w], U(2026, 1, 1))[0]["text"]  # GMT


def test_r9_boundaries():
    far = U(2027, 1, 1)
    f = lambda dt: _adjust_quiet(dt, NOW, far)
    assert f(U(2026, 7, 10, 19, 59)) == U(2026, 7, 10, 19, 59)
    assert f(U(2026, 7, 10, 20, 0)) == U(2026, 7, 10, 19, 0)
    assert f(U(2026, 7, 10, 6, 59)) == U(2026, 7, 9, 19, 0)
    assert f(U(2026, 7, 10, 7, 0)) == U(2026, 7, 10, 7, 0)


def test_r10_cancelled():
    for s in ("cancelled", "Cancelled", " CANCELLED "):
        assert plan_reminders([mk(status=s)], NOW) == []


def test_r11_no_pii_in_logs(caplog):
    caplog.set_level(logging.DEBUG)
    appts = [mk(), mk(id="a2", email="skip@example.org", phone=None, optout_sms_v2=True, status="Cancelled"),
             mk(id="a3", email="", phone="", customer_name="Secret Name"),
             mk(id="a4", email="bad@example.net", starts_at="not-a-date"),
             mk(id="a5", email="naive@example.com", starts_at=datetime(2026, 8, 1))]
    plan_reminders(appts, NOW)
    for s in ("mary@example.com", "skip@example.org", "bad@example.net", "naive@example.com",
              "+353871234567", "Secret Name"):
        assert s not in caplog.text
    assert "a3" in caplog.text


def test_r12_signature():
    assert plan_reminders([mk()], NOW)[0]["text"].endswith("Siobhán Ní Dhuibhir")
    assert plan_reminders([mk(country="PL")], NOW)[0]["text"].endswith("Grzegorz Szczepański")
    assert plan_reminders([mk(country="pl")], NOW)[0]["text"].endswith("Siobhán Ní Dhuibhir")


def test_r13_both_passed_only_second():
    now = U(2026, 7, 10, 10, 0)
    out = plan_reminders([mk(starts_at=U(2026, 7, 10, 11, 0))], now)
    assert len(out) == 1 and out[0]["send_at"] == now and "Final reminder" in out[0]["text"]


def test_r14_dst_days():
    for starts in (U(2026, 3, 31, 14, 0), U(2026, 10, 27, 10, 0), U(2026, 3, 29, 14, 0)):
        out = plan_reminders([mk(starts_at=starts)], starts - timedelta(days=10))
        assert out[0]["send_at"] == starts - timedelta(hours=48)
        assert out[1]["send_at"] == starts - timedelta(hours=2)
    out = plan_reminders([mk(starts_at=U(2026, 3, 31, 14, 0))], U(2026, 3, 1))
    assert "at 15:00" in out[0]["text"]


def test_r15_sorted():
    out = plan_reminders([mk(id="b", starts_at=S), mk(id="a", starts_at=S),
                          mk(id="c", starts_at=S - timedelta(days=1))], NOW)
    keys = [(r["send_at"], r["appointment_id"]) for r in out]
    assert keys == sorted(keys)
    assert [r["appointment_id"] for r in out[2:4]] == ["a", "b"]


def test_d1_quiet_now():
    now = U(2026, 1, 10, 22, 0)
    out = plan_reminders([mk(starts_at=U(2026, 1, 12, 10, 0))], now)
    assert out[0]["send_at"] == U(2026, 1, 11, 8, 0)
    assert plan_reminders([mk(starts_at=U(2026, 1, 11, 6, 0))], now) == []


def test_d2_early_appointment():
    out = plan_reminders([mk(starts_at=U(2026, 1, 20, 9, 0))], U(2026, 1, 1))
    assert out[1]["send_at"] == U(2026, 1, 19, 20, 0)
    now = U(2026, 1, 18, 21, 30)
    out = plan_reminders([mk(starts_at=U(2026, 1, 19, 8, 30))], now)
    assert [r["send_at"] for r in out] == [U(2026, 1, 19, 8, 0)]
    assert plan_reminders([mk(starts_at=U(2026, 1, 19, 7, 30))], now) == []


def test_d3_past_appointment():
    assert plan_reminders([mk(starts_at=NOW)], NOW) == []
    assert plan_reminders([mk(starts_at=NOW - timedelta(hours=1))], NOW) == []


def test_d4_duplicate_collapse():
    out = plan_reminders([mk(starts_at=NOW + timedelta(hours=1))], NOW)
    assert len(out) == 1 and out[0]["send_at"] == NOW


def test_d7_naive_now_and_inputs():
    import pytest
    with pytest.raises(ValueError):
        plan_reminders([mk()], datetime(2026, 7, 1, 12, 0))
    a = mk()
    snap = dict(a)
    plan_reminders([a], NOW)
    assert a == snap
    assert plan_reminders([mk(starts_at=datetime(2026, 8, 1))], NOW) == []