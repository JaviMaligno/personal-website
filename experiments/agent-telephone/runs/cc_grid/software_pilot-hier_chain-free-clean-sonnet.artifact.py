# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-wgfxn9nw/reminders.py =====
# NOTE: I had no execution tools, so the tests below have NOT been run.
"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now).

Rules and decisions implemented:
* Opt-out uses optout_sms_v2 only (missing/None means not opted out); the old
  opt_out field is ignored.
* Reminders at starts_at-48h and starts_at-2h (absolute elapsed time, computed
  in UTC so DST never skews them). Never earlier than now, never at/after start.
* Channel: SMS if phone is non-blank and not opted out, else email, else the
  appointment is skipped (logged by id only). Never both channels per reminder.
* SMS <= 160 characters (NFC-normalised): name is shortened (full, first name,
  first name + ellipsis, no name); date, time and signature always kept.
* Quiet hours 21:00-08:00 Europe/Dublin (21:00 inclusive, 08:00 allowed). A time
  inside moves back to the preceding 20:00 local (built as wall-clock time).
* 48h reminder: nominal = max(start-48h, now) (so "immediate" = now); moved
  back for quiet hours; if that is before now it is dropped (not deferred). This
  also covers an immediate first reminder that falls in quiet hours.
* 2h reminder: T = start-2h. If T >= now, use T moved back for quiet hours when
  that is >= now. Otherwise fall back: now if now is allowed, else the next 08:00
  local. Dropped if the result is not before start (logged by id).
* Dedupe: if both reminders are within 1 hour of each other (or equal), only the
  2h reminder is kept.
* Cancelled (case-insensitive, stripped), past appointments, and appointments
  with missing/naive starts_at yield nothing. Naive `now` raises ValueError.
* Privacy: email addresses are never logged. The per-reminder INFO line carries
  appointment id, channel and contact; for SMS the phone is masked to its last 4
  digits, and for email the contact is shown as "email on file".
* Input is never mutated. Output sorted by (send_at, appointment id, order).
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
_DEDUPE_WINDOW = timedelta(hours=1)


def _is_aware(value: Any) -> bool:
    """Return True if value is a timezone-aware datetime."""
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _to_local(dt: datetime) -> datetime:
    """Convert an aware datetime to Europe/Dublin."""
    return dt.astimezone(DUBLIN)


def _is_quiet(dt: datetime) -> bool:
    """True if dt falls in quiet hours (21:00-07:59 Dublin local)."""
    hour = _to_local(dt).hour
    return hour >= 21 or hour < 8


def _apply_quiet_hours(dt: datetime) -> datetime:
    """Return dt in Dublin time, moved back to the preceding 20:00 if in quiet hours."""
    local = _to_local(dt)
    if not (local.hour >= 21 or local.hour < 8):
        return local
    day: date = local.date()
    if local.hour < 8:
        day -= timedelta(days=1)
    return datetime.combine(day, time(20, 0), tzinfo=DUBLIN)


def _next_allowed(dt: datetime) -> datetime:
    """Return the next 08:00 Dublin local at or after a quiet-hours dt."""
    local = _to_local(dt)
    day: date = local.date()
    if local.hour >= 21:
        day += timedelta(days=1)
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN)


def _channel_for(appt: dict[str, Any]) -> tuple[str, str] | None:
    """Return (channel, contact) for the appointment, or None if unreachable."""
    phone = appt.get("phone")
    if isinstance(phone, str) and phone.strip() and not appt.get("optout_sms_v2"):
        return "sms", phone.strip()
    email = appt.get("email")
    if isinstance(email, str) and email.strip():
        return "email", email.strip()
    return None


def _signature_for(appt: dict[str, Any]) -> str:
    """Pick the signature from the country code."""
    country = appt.get("country")
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIGNATURE_PL
    return SIGNATURE


def _clean_name(name: Any) -> str:
    """Normalise a customer name (NFC, collapsed whitespace); '' if unusable."""
    if not isinstance(name, str):
        return ""
    return unicodedata.normalize("NFC", " ".join(name.split()))


def _render(name: str, when: datetime, signature: str, second: bool) -> str:
    """Render the message from the shared template."""
    lead = "final reminder" if second else "reminder"
    body = (
        f"your Brennan Opticians appointment is on "
        f"{when:%d/%m/%Y} at {when:%H:%M}."
    )
    greeting = f"Hi {name}, {lead}: " if name else f"{lead.capitalize()}: "
    return f"{greeting}{body} {signature}"


def _build_text(name: Any, start_local: datetime, signature: str,
                second: bool = False, max_len: int | None = None) -> str:
    """Build reminder text; if max_len is set, shorten the name to fit."""
    signature = unicodedata.normalize("NFC", signature)
    full = _clean_name(name)
    text = _render(full, start_local, signature, second)
    if max_len is None or len(text) <= max_len:
        return text
    first = full.split(" ")[0] if full else ""
    if first:
        text = _render(first, start_local, signature, second)
        if len(text) <= max_len:
            return text
        for k in range(len(first) - 1, 0, -1):
            text = _render(first[:k] + "…", start_local, signature, second)
            if len(text) <= max_len:
                return text
    return _render("", start_local, signature, second)


def _first_send(start: datetime, now: datetime) -> datetime | None:
    """Send time for the 48h reminder, or None if dropped."""
    nominal = max(start - timedelta(hours=48), now)
    send = _apply_quiet_hours(nominal)
    if send < now or send >= start:
        return None
    return send


def _second_send(start: datetime, now: datetime) -> datetime | None:
    """Send time for the 2h reminder, or None if dropped."""
    send: datetime | None = None
    nominal = start - timedelta(hours=2)
    if nominal >= now:
        cand = _apply_quiet_hours(nominal)
        if cand >= now:
            send = cand
    if send is None:
        send = _to_local(now) if not _is_quiet(now) else _next_allowed(now)
    return send if send < start else None


def _mask(channel: str, contact: str) -> str:
    """Loggable form of a contact (no email addresses)."""
    if channel == "sms":
        digits = "".join(c for c in contact if c.isdigit())
        return "***" + digits[-4:]
    return "email on file"


def _plan_one(appt: dict[str, Any], now: datetime) -> list[tuple[int, dict[str, Any]]]:
    """Plan reminders for one appointment as (order, reminder) pairs."""
    aid = appt.get("id")
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        logger.debug("no reminders for appointment %s: cancelled", aid)
        return []
    start = appt.get("starts_at")
    if not _is_aware(start):
        logger.warning("skipping appointment %s: missing or invalid starts_at", aid)
        return []
    start = start.astimezone(timezone.utc)
    if start <= now:
        logger.debug("no reminders for appointment %s: already started", aid)
        return []
    chan = _channel_for(appt)
    if chan is None:
        logger.info("no contact channel for appointment %s", aid)
        return []
    channel, contact = chan

    first = _first_send(start, now)
    second = _second_send(start, now)
    if first is None:
        logger.debug("48h reminder dropped for appointment %s: no allowed slot", aid)
    if second is None:
        logger.info("2h reminder dropped for appointment %s: no allowed slot before start", aid)
    if first is not None and second is not None and abs(second - first) <= _DEDUPE_WINDOW:
        logger.info("48h reminder dropped for appointment %s: too close to 2h reminder", aid)
        first = None

    start_local = _to_local(start)
    signature = _signature_for(appt)
    limit = SMS_LIMIT if channel == "sms" else None
    result: list[tuple[int, dict[str, Any]]] = []
    for order, send, is_second in ((0, first, False), (1, second, True)):
        if send is None:
            continue
        text = _build_text(appt.get("customer_name"), start_local, signature, is_second, limit)
        result.append((order, {
            "appointment_id": aid,
            "channel": channel,
            "send_at": _to_local(send),
            "text": text,
        }))
        logger.info("reminder planned: appointment=%s which=%s channel=%s contact=%s send_at=%s",
                    aid, "2h" if is_second else "48h", channel,
                    _mask(channel, contact), _to_local(send).isoformat())
    return result


def plan_reminders(appointments: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """Plan reminders for all appointments; see module docstring for the rules."""
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(timezone.utc)
    planned: list[tuple[int, dict[str, Any]]] = []
    for appt in appointments:
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda p: (p[1]["send_at"], str(p[1]["appointment_id"]), p[0]))
    return [r for _, r in planned]


# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-wgfxn9nw/test_reminders.py =====
import copy
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from reminders import _apply_quiet_hours, _build_text, _channel_for, plan_reminders

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIG = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
EMAIL = "secret.person@example.com"


def d(y, m, dd, h=0, mi=0, tz=DUB):
    return datetime(y, m, dd, h, mi, tzinfo=tz)


NOW = d(2026, 7, 1, 12)


def appt(**kw):
    base = dict(id="a1", customer_name="Mary Murphy", email=EMAIL, phone="+353871234567",
                country="IE", status="booked", starts_at=d(2026, 7, 15, 10),
                optout_sms_v2=False)
    base.update(kw)
    return base


def is_second(r):
    return "final reminder" in r["text"].lower()


def split(res):
    return [r for r in res if not is_second(r)], [r for r in res if is_second(r)]


def test_utc_input_gives_dublin_text():
    res = plan_reminders([appt(starts_at=d(2026, 7, 15, 12, tz=UTC))], NOW)
    assert len(res) == 2
    for r in res:
        assert "15/07/2026 at 13:00" in r["text"]
        assert "12:00" not in r["text"]
    assert res[0]["send_at"] == d(2026, 7, 13, 12, tz=UTC)
    assert res[1]["send_at"] == d(2026, 7, 15, 10, tz=UTC)


def test_dst_spring_48h_elapsed():
    now = d(2026, 3, 20, 12, tz=UTC)
    res = plan_reminders([appt(starts_at=d(2026, 3, 30, 10))], now)
    first, second = split(res)
    assert first[0]["send_at"] == d(2026, 3, 28, 9, tz=UTC)
    assert second[0]["send_at"] == d(2026, 3, 30, 8, tz=UTC)
    assert "30/03/2026 at 10:00" in first[0]["text"]


def test_dst_fall_48h_elapsed():
    now = d(2026, 10, 15, 12, tz=UTC)
    res = plan_reminders([appt(starts_at=d(2026, 10, 25, 12, tz=UTC))], now)
    first, _ = split(res)
    assert first[0]["send_at"] == d(2026, 10, 23, 12, tz=UTC)
    assert first[0]["send_at"].astimezone(DUB).hour == 13
    assert "at 12:00" in first[0]["text"]


def test_quiet_move_back_across_spring_transition():
    now = d(2026, 3, 20, 12, tz=UTC)
    res = plan_reminders([appt(starts_at=d(2026, 3, 29, 7, tz=UTC))], now)
    _, second = split(res)
    assert second[0]["send_at"] == d(2026, 3, 28, 20, tz=UTC)
    assert "at 08:00" in second[0]["text"]


def test_quiet_move_back_across_fall_transition():
    now = d(2026, 10, 15, 12, tz=UTC)
    res = plan_reminders([appt(starts_at=d(2026, 10, 25, 8, tz=UTC))], now)
    _, second = split(res)
    assert second[0]["send_at"] == d(2026, 10, 24, 19, tz=UTC)


@pytest.mark.parametrize("h,mi,expected", [
    (21, 0, d(2026, 7, 15, 20)),
    (23, 59, d(2026, 7, 15, 20)),
    (20, 59, d(2026, 7, 15, 20, 59)),
    (8, 0, d(2026, 7, 15, 8)),
    (7, 59, d(2026, 7, 14, 20)),
    (0, 0, d(2026, 7, 14, 20)),
])
def test_quiet_boundaries(h, mi, expected):
    assert _apply_quiet_hours(d(2026, 7, 15, h, mi)) == expected


def test_quiet_with_utc_input():
    assert _apply_quiet_hours(d(2026, 7, 15, 20, 30, tz=UTC)) == d(2026, 7, 15, 20)


def test_signatures():
    assert plan_reminders([appt()], NOW)[0]["text"].endswith(SIG)
    for c in ("PL", "pl", " Pl "):
        assert plan_reminders([appt(country=c)], NOW)[0]["text"].endswith(SIG_PL)


def test_sms_truncation_long_name():
    for name in ("Ż" * 300 + " Kowalski", "Bartłomiej " + "Z" * 200, "Ł ó " * 100):
        for country, sig in (("IE", SIG), ("PL", SIG_PL)):
            res = plan_reminders([appt(customer_name=name, country=country)], NOW)
            for r in res:
                assert r["channel"] == "sms"
                assert len(r["text"]) <= 160
                assert r["text"].endswith(sig)
                assert "15/07/2026 at 10:00" in r["text"]


def test_truncation_steps():
    start = d(2026, 7, 15, 10)
    t = _build_text("Bartłomiej " + "Z" * 200, start, SIG, max_len=160)
    assert "Bartłomiej" in t and "ZZZ" not in t
    t = _build_text("Ż" * 300, start, SIG, max_len=160)
    assert "…" in t and len(t) <= 160
    assert "Mary Murphy" in _build_text("Mary Murphy", start, SIG, max_len=160)


def test_email_keeps_full_name():
    name = "Ż" * 300 + " Kowalski"
    r = plan_reminders([appt(customer_name=name, phone=None)], NOW)[0]
    assert r["channel"] == "email" and name in r["text"] and r["text"].endswith(SIG)


def test_cancelled():
    assert plan_reminders([appt(status=" Cancelled ")], NOW) == []


def test_stale_opt_out_ignored():
    res = plan_reminders([appt(opt_out=True, optout_sms_v2=False)], NOW)
    assert {r["channel"] for r in res} == {"sms"}
    res = plan_reminders([appt(opt_out=False, optout_sms_v2=True)], NOW)
    assert res and {r["channel"] for r in res} == {"email"}


def test_sorting_and_tiebreak():
    a = [appt(id="b", starts_at=d(2026, 7, 20, 10)), appt(id="a", starts_at=d(2026, 7, 20, 10)),
         appt(id="c", starts_at=d(2026, 7, 10, 10))]
    res = plan_reminders(a, NOW)
    keys = [(r["send_at"], r["appointment_id"]) for r in res]
    assert keys == sorted(keys)
    same = [r["appointment_id"] for r in res if r["send_at"] == d(2026, 7, 18, 10)]
    assert same == ["a", "b"]


def test_past_appointments():
    assert plan_reminders([appt(starts_at=NOW), appt(starts_at=NOW - timedelta(days=1))], NOW) == []


def test_input_not_mutated():
    a = [appt(), appt(id="a2", phone=None)]
    snap = copy.deepcopy(a)
    plan_reminders(a, NOW)
    assert a == snap


def test_no_email_in_logs(caplog):
    caplog.set_level(logging.DEBUG)
    cases = [appt(), appt(id="a2", phone=None), appt(id="a3", optout_sms_v2=True, phone="  "),
             appt(id="a4", phone=None, email=" "), appt(id="a5", status="cancelled"),
             appt(id="a6", starts_at=datetime(2026, 7, 15, 10)),
             appt(id="a7", starts_at=d(2026, 7, 1, 12, 30)),
             appt(id="a8", starts_at=d(2026, 7, 2, 7, 30), phone=None)]
    plan_reminders(cases, d(2026, 7, 1, 23))
    plan_reminders(cases, NOW)
    assert caplog.records
    for rec in caplog.records:
        for s in (rec.getMessage(), str(rec.msg), str(rec.args)):
            assert EMAIL not in s and "secret.person" not in s
    assert "no contact channel for appointment a4" in caplog.text


def test_info_line_per_reminder(caplog):
    caplog.set_level(logging.INFO)
    res = plan_reminders([appt()], NOW)
    lines = [r.getMessage() for r in caplog.records if "planned" in r.getMessage()]
    assert len(lines) == len(res) == 2
    assert all("a1" in line and "sms" in line for line in lines)


def test_naive_now_rejected():
    with pytest.raises(ValueError) as e:
        plan_reminders([appt()], datetime(2026, 7, 1, 12))
    assert EMAIL not in str(e.value)


def test_contact_fallbacks():
    assert plan_reminders([appt(phone=None)], NOW)[0]["channel"] == "email"
    assert plan_reminders([appt(phone="   ")], NOW)[0]["channel"] == "email"
    assert plan_reminders([appt(phone=None, email="")], NOW) == []
    assert plan_reminders([appt(phone="1", optout_sms_v2=True, email=None)], NOW) == []
    a = appt()
    del a["optout_sms_v2"]
    assert plan_reminders([a], NOW)[0]["channel"] == "sms"
    assert _channel_for(appt(phone=None)) == ("email", EMAIL)


def test_bad_records_do_not_break_batch():
    bad = [{"id": "z"}, appt(id="n", starts_at=datetime(2026, 7, 15, 10)), appt(id="ok")]
    res = plan_reminders(bad, NOW)
    assert {r["appointment_id"] for r in res} == {"ok"}


def test_decision_a_less_than_two_hours_sends_now():
    now = d(2026, 7, 10, 12)
    res = plan_reminders([appt(starts_at=d(2026, 7, 10, 13))], now)
    assert len(res) == 1 and is_second(res[0]) and res[0]["send_at"] == now


def test_decision_a_moved_back_in_past_now_allowed():
    now = d(2026, 7, 11, 8, 10)
    res = plan_reminders([appt(starts_at=d(2026, 7, 11, 8, 30))], now)
    assert len(res) == 1 and is_second(res[0]) and res[0]["send_at"] == now


def test_decision_a_now_quiet_defers_to_morning():
    res = plan_reminders([appt(starts_at=d(2026, 7, 11, 9, 30))], d(2026, 7, 10, 23))
    assert len(res) == 1 and res[0]["send_at"] == d(2026, 7, 11, 8)
    res = plan_reminders([appt(starts_at=d(2026, 7, 11, 9))], d(2026, 7, 11, 2))
    assert len(res) == 1 and res[0]["send_at"] == d(2026, 7, 11, 8)


def test_decision_a_dropped_and_logged(caplog):
    caplog.set_level(logging.DEBUG)
    assert plan_reminders([appt(starts_at=d(2026, 7, 11, 7, 30))], d(2026, 7, 10, 23)) == []
    assert any("a1" in r.getMessage() and "dropped" in r.getMessage() for r in caplog.records)


def test_decision_a_normal_second():
    _, second = split(plan_reminders([appt()], NOW))
    assert second[0]["send_at"] == d(2026, 7, 15, 8)


def test_decision_c_immediate_first_in_quiet_hours_dropped():
    now = d(2026, 7, 14, 22)
    res = plan_reminders([appt(starts_at=d(2026, 7, 15, 10))], now)
    assert len(res) == 1 and is_second(res[0]) and res[0]["send_at"] == d(2026, 7, 15, 8)


def test_decision_e_dedupe():
    now = d(2026, 7, 10, 12)
    res = plan_reminders([appt(starts_at=d(2026, 7, 10, 15))], now)
    assert len(res) == 1 and is_second(res[0])
    res = plan_reminders([appt(starts_at=d(2026, 7, 10, 15, 30))], now)
    assert len(res) == 2 and res[0]["send_at"] == now


def test_invariants_never_past_never_both_channels():
    appts = [appt(id="x1", starts_at=d(2026, 3, 29, 7, tz=UTC)),
             appt(id="x2", phone=None, starts_at=d(2026, 3, 30, 9)),
             appt(id="x3", starts_at=d(2026, 10, 25, 12, tz=UTC), optout_sms_v2=True),
             appt(id="x4", starts_at=d(2026, 10, 26, 7, 30))]
    starts = {a["id"]: a["starts_at"] for a in appts}
    for base in (d(2026, 3, 26, tz=UTC), d(2026, 10, 22, tz=UTC)):
        for i in range(0, 6 * 24 * 60, 37):
            now = base + timedelta(minutes=i)
            seen = set()
            for r in plan_reminders(appts, now):
                assert r["send_at"] >= now
                assert r["send_at"] < starts[r["appointment_id"]]
                assert 8 <= r["send_at"].astimezone(DUB).hour < 21
                assert r["channel"] in {"sms", "email"}
                key = (r["appointment_id"], is_second(r))
                assert key not in seen
                seen.add(key)
                if r["channel"] == "sms":
                    assert len(r["text"]) <= 160