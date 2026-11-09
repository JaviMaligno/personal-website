# FILE: reminders.py
"""Reminder planner for appointments.

Files: reminders.py, tests/test_reminders.py

Assumptions:
 1. Appointment dicts use keys: id (or appointment_id), starts_at (tz-aware
    datetime), status, name, phone, email, optout_sms_v2, opt_out (ignored),
    country. Missing keys are treated as empty/false.
 2. optout_sms_v2 is evaluated by truthiness. Non-string phone/email values
    are treated as empty.
 3. A missing or empty id, a non-datetime starts_at, or a naive datetime
    (including `now`) raises ValueError. Messages never contain PII.
 4. Output appointment_id is the id value as given. Ties in sorting compare
    ids as strings.
 5. When both reminders would go out at the same instant, only the 2h one is
    kept (compared as UTC instants).
 6. Quiet hours: if t is quiet and the preceding 20:00 is >= now, use that
    20:00. Otherwise use the next 08:00 at or after t. The result is dropped
    if it is before now or after starts_at.
 7. Text wording is my own: "Reminder" for 48h, "Final reminder" for 2h.
    Dates are DD/MM/YYYY and times HH:MM in Europe/Dublin.
 8. SMS shortening order: full name, truncated name with "…", initials
    ("J.D."), then no name ("Hi,"). Length is len(str) <= 160.
 9. Conflict resolution on logging. The house rule asks for one INFO line per
    planned reminder naming channel and contact, while the task says never to
    log email, phone or name. I log appointment id, kind, channel, send_at and
    a MASKED contact (first char + "***" for email, "***" + last 2 digits for
    phone). Full contact details, names and message text are never logged. If
    support needs full contact details, that needs an explicit decision from
    the client.
10. Python 3.9+ compatible. zoneinfo needs system tz data (or the tzdata
    package on platforms without it).
11. Skipped appointments (cancelled, started, no channel) are not logged,
    except the no-channel case, which logs a WARNING with the id only.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"


def _s(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_quiet(local_dt: datetime) -> bool:
    return local_dt.hour >= 21 or local_dt.hour < 8


def _local(d: date, hour: int) -> datetime:
    # Wall-clock construction, normalised through UTC (handles gaps/folds).
    return datetime(d.year, d.month, d.day, hour, tzinfo=DUBLIN).astimezone(UTC).astimezone(DUBLIN)


def _prev_2000(dt: datetime) -> datetime:
    """Latest 20:00 Dublin local time at or before dt."""
    dt = dt.astimezone(DUBLIN)
    c = _local(dt.date(), 20)
    if c.astimezone(UTC) > dt.astimezone(UTC):
        c = _local(dt.date() - timedelta(days=1), 20)
    return c


def _next_0800(dt: datetime) -> datetime:
    """Earliest 08:00 Dublin local time at or after dt."""
    dt = dt.astimezone(DUBLIN)
    c = _local(dt.date(), 8)
    if c.astimezone(UTC) < dt.astimezone(UTC):
        c = _local(dt.date() + timedelta(days=1), 8)
    return c


def _channel(appt: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    phone = _s(appt.get("phone"))
    if phone and not appt.get("optout_sms_v2"):
        return "sms", phone
    if appt.get("optout_sms_v2") or not phone:
        email = _s(appt.get("email"))
        if email:
            return "email", email
    return None


def _mask(channel: str, contact: str) -> str:
    if channel == "email":
        return contact[:1] + "***"
    return "***" + contact[-2:]


def _signature(appt: Dict[str, Any]) -> str:
    return SIG_PL if _s(appt.get("country")).upper() == "PL" else SIG_DEFAULT


def _clean_name(appt: Dict[str, Any]) -> str:
    return " ".join(_s(appt.get("name")).split())


def _compose(name: str, appt_local: datetime, kind: str, sig: str) -> str:
    lead = "Final reminder" if kind == "2h" else "Reminder"
    greet = "Hi %s" % name if name else "Hi"
    return "%s, %s: your appointment is on %s at %s. %s" % (
        greet, lead, appt_local.strftime("%d/%m/%Y"), appt_local.strftime("%H:%M"), sig)


def _build_text(appt: Dict[str, Any], send_local_appt_dt: datetime, kind: str,
                name: Optional[str] = None) -> str:
    if name is None:
        name = _clean_name(appt)
    return _compose(name, send_local_appt_dt.astimezone(DUBLIN), kind, _signature(appt))


def _fit_sms(appt: Dict[str, Any], send_local_appt_dt: datetime, kind: str) -> str:
    name = _clean_name(appt)
    text = _build_text(appt, send_local_appt_dt, kind, name)
    if len(text) <= SMS_LIMIT:
        return text
    for n in range(len(name) - 1, 0, -1):
        part = name[:n].rstrip()
        if not part:
            continue
        text = _build_text(appt, send_local_appt_dt, kind, part + "…")
        if len(text) <= SMS_LIMIT:
            return text
    initials = "".join(w[0].upper() + "." for w in name.split())
    if initials:
        text = _build_text(appt, send_local_appt_dt, kind, initials)
        if len(text) <= SMS_LIMIT:
            return text
    return _build_text(appt, send_local_appt_dt, kind, "")


def _schedule(ideal: datetime, now: datetime, starts: datetime) -> Optional[datetime]:
    t = max(ideal, now)
    lt = t.astimezone(DUBLIN)
    if _is_quiet(lt):
        s = _prev_2000(lt)
        res = s if s.astimezone(UTC) >= now else _next_0800(lt)
    else:
        res = lt
    ru = res.astimezone(UTC)
    if ru > starts or ru < now:
        return None
    return res


def _plan_one(appt: Dict[str, Any], now: datetime) -> List[Tuple[datetime, str, int, Dict[str, Any]]]:
    aid = appt.get("id", appt.get("appointment_id"))
    if aid is None or aid == "":
        raise ValueError("appointment without id")
    starts = appt.get("starts_at")
    if not isinstance(starts, datetime) or starts.tzinfo is None or starts.utcoffset() is None:
        raise ValueError("appointment %s: starts_at must be a timezone-aware datetime" % aid)
    if _s(appt.get("status")).lower() == "cancelled":
        return []
    starts_u = starts.astimezone(UTC)
    if starts_u <= now:
        return []
    ch = _channel(appt)
    if ch is None:
        logger.warning("appointment %s skipped: no usable contact channel", aid)
        return []
    channel, contact = ch
    appt_local = starts_u.astimezone(DUBLIN)

    found: Dict[str, datetime] = {}
    for kind, hours in (("48h", 48), ("2h", 2)):
        res = _schedule(starts_u - timedelta(hours=hours), now, starts_u)
        if res is not None:
            found[kind] = res
    if len(found) == 2 and found["2h"].astimezone(UTC) == found["48h"].astimezone(UTC):
        del found["48h"]

    out = []
    for kind, send_at in found.items():
        text = (_fit_sms(appt, appt_local, kind) if channel == "sms"
                else _build_text(appt, appt_local, kind))
        logger.info("reminder planned: appointment=%s kind=%s channel=%s to=%s send_at=%s",
                    aid, kind, channel, _mask(channel, contact), send_at.isoformat())
        out.append((send_at, str(aid), 0 if kind == "2h" else 1,
                    {"appointment_id": aid, "channel": channel, "send_at": send_at, "text": text}))
    return out


def plan_reminders(appointments: Iterable[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_u = now.astimezone(UTC)
    items: List[Tuple[datetime, str, int, Dict[str, Any]]] = []
    count = 0
    for appt in appointments:
        count += 1
        items.extend(_plan_one(appt, now_u))
    items.sort(key=lambda x: (x[0].astimezone(UTC), x[1], x[2]))
    logger.info("planned %d reminders for %d appointments", len(items), count)
    return [x[3] for x in items]


# FILE: tests/test_reminders.py
import copy
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import reminders  # noqa: E402
from reminders import plan_reminders  # noqa: E402

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
EMAIL = "jane.secret@example.com"
PHONE = "0851234567"
EARLY = datetime(2026, 6, 1, tzinfo=UTC)


def dub(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUB)


def appt(**kw):
    base = {"id": "a1", "starts_at": dub(2026, 6, 10, 14), "name": "Jane Doe",
            "phone": PHONE, "email": EMAIL, "country": "IE"}
    base.update(kw)
    return base


def by_kind(res):
    return res


def test_march_dst():
    a = appt(starts_at=dub(2026, 3, 29, 12))
    res = plan_reminders([a], datetime(2026, 3, 20, tzinfo=UTC))
    assert [r["send_at"].astimezone(UTC) for r in res] == [
        datetime(2026, 3, 27, 11, tzinfo=UTC), datetime(2026, 3, 29, 9, tzinfo=UTC)]
    assert [r["send_at"].hour for r in res] == [11, 10]


def test_october_dst():
    a = appt(starts_at=dub(2026, 10, 25, 12))
    res = plan_reminders([a], datetime(2026, 10, 15, tzinfo=UTC))
    assert [r["send_at"].astimezone(UTC) for r in res] == [
        datetime(2026, 10, 23, 12, tzinfo=UTC), datetime(2026, 10, 25, 10, tzinfo=UTC)]
    assert [r["send_at"].hour for r in res] == [13, 10]


def test_utc_inputs_and_dublin_output():
    a = appt(starts_at=datetime(2026, 6, 10, 14, tzinfo=UTC))
    res = plan_reminders([a], EARLY)
    assert [r["send_at"].astimezone(UTC) for r in res] == [
        datetime(2026, 6, 8, 14, tzinfo=UTC), datetime(2026, 6, 10, 12, tzinfo=UTC)]
    for r in res:
        assert r["send_at"].tzinfo.key == "Europe/Dublin"
        assert r["send_at"].utcoffset() == timedelta(hours=1)


@pytest.mark.parametrize("n", [20, 60, 120, 500])
@pytest.mark.parametrize("country", ["IE", "PL"])
def test_sms_length(n, country):
    name = ("Żółć Wielkonazwiskowy " * 30)[:n] if n > 20 else "Zażółć Gęślą Jaźń"[:n]
    res = plan_reminders([appt(name=name, country=country)], EARLY)
    sig = "Grzegorz Szczepański" if country == "PL" else "Chevonne Nee Divver"
    for r in res:
        assert r["channel"] == "sms"
        assert len(r["text"]) <= 160
        assert "10/06/2026" in r["text"] or "08/06/2026" in r["text"]
        assert "14:00" in r["text"]
        assert r["text"].endswith(sig)


def test_very_long_name_is_truncated_with_ellipsis_or_fallback():
    res = plan_reminders([appt(name="A" * 500)], EARLY)
    assert all(len(r["text"]) <= 160 for r in res)
    assert all("…" in r["text"] for r in res)


def test_many_words_falls_back_without_name():
    name = " ".join(["B"] * 400)
    res = plan_reminders([appt(name=name)], EARLY)
    assert all(len(r["text"]) <= 160 and r["text"].endswith("Chevonne Nee Divver") for r in res)


def test_email_not_truncated():
    res = plan_reminders([appt(name="A" * 500, optout_sms_v2=True)], EARLY)
    assert all(r["channel"] == "email" and "A" * 500 in r["text"] for r in res)


def test_pl_signature_nonascii():
    res = plan_reminders([appt(country=" pl ")], EARLY)
    assert res and all(r["text"].endswith("Grzegorz Szczepański") for r in res)


def test_cancelled_skipped_and_other_status_processed():
    assert plan_reminders([appt(status=" CancelLed ")], EARLY) == []
    assert len(plan_reminders([appt(status="confirmed")], EARLY)) == 2
    assert len(plan_reminders([appt()], EARLY)) == 2
    assert len(plan_reminders([appt(status=None)], EARLY)) == 2


def test_optout_sms_v2_uses_email():
    res = plan_reminders([appt(optout_sms_v2=True)], EARLY)
    assert {r["channel"] for r in res} == {"email"}


def test_opt_out_ignored():
    res = plan_reminders([appt(opt_out=True, optout_sms_v2=False)], EARLY)
    assert {r["channel"] for r in res} == {"sms"}
    res = plan_reminders([appt(opt_out=True, optout_sms_v2=True)], EARLY)
    assert {r["channel"] for r in res} == {"email"}


def test_no_phone_uses_email():
    for p in ("  ", "", None):
        res = plan_reminders([appt(phone=p)], EARLY)
        assert {r["channel"] for r in res} == {"email"}


def test_no_contact_and_optout_without_email(caplog):
    caplog.set_level(logging.DEBUG)
    assert plan_reminders([appt(phone="", email=" ", id="x9")], EARLY) == []
    assert plan_reminders([appt(optout_sms_v2=True, email="", id="x8")], EARLY) == []
    assert "x9" in caplog.text and "x8" in caplog.text
    assert PHONE not in caplog.text


@pytest.mark.parametrize("h,mi,expected", [
    (22, 59, (2026, 6, 10, 20, 59)),   # ideal 20:59 not quiet
    (23, 0, (2026, 6, 10, 20, 0)),     # ideal 21:00 quiet -> prev 20:00
    (10, 0, (2026, 6, 10, 8, 0)),      # ideal 08:00 not quiet
    (9, 59, (2026, 6, 9, 20, 0)),      # ideal 07:59 quiet -> prev 20:00
    (9, 0, (2026, 6, 9, 20, 0)),       # 08:00-10:00 appt
])
def test_quiet_edges_via_plan(h, mi, expected):
    res = plan_reminders([appt(starts_at=dub(2026, 6, 10, h, mi))], EARLY)
    two_h = res[-1]
    assert two_h["send_at"].astimezone(UTC) == dub(*expected).astimezone(UTC)


def test_is_quiet_edges():
    assert not reminders._is_quiet(dub(2026, 6, 10, 20, 59))
    assert reminders._is_quiet(dub(2026, 6, 10, 21, 0))
    assert reminders._is_quiet(dub(2026, 6, 10, 7, 59))
    assert not reminders._is_quiet(dub(2026, 6, 10, 8, 0))


def test_now_in_quiet_hours_defers_to_0800():
    now = dub(2026, 6, 10, 22)
    res = plan_reminders([appt(starts_at=dub(2026, 6, 11, 12))], now)
    assert [r["send_at"].astimezone(UTC) for r in res] == [
        dub(2026, 6, 11, 8).astimezone(UTC), dub(2026, 6, 11, 10).astimezone(UTC)]


def test_past_48h_sends_at_now():
    now = dub(2026, 6, 10, 10)
    res = plan_reminders([appt(starts_at=dub(2026, 6, 11, 18))], now)
    assert res[0]["send_at"].astimezone(UTC) == now.astimezone(UTC)
    assert len(res) == 2


def test_past_start_dropped():
    now = dub(2026, 6, 10, 10)
    assert plan_reminders([appt(starts_at=dub(2026, 6, 10, 9))], now) == []
    assert plan_reminders([appt(starts_at=now)], now) == []


def test_collapse_duplicates_keeps_2h():
    now = dub(2026, 6, 10, 23)
    res = plan_reminders([appt(starts_at=dub(2026, 6, 11, 9))], now)
    assert len(res) == 1
    assert res[0]["send_at"].astimezone(UTC) == dub(2026, 6, 11, 8).astimezone(UTC)
    assert "Final reminder" in res[0]["text"]


def test_keep_48h_when_2h_unschedulable():
    now = dub(2026, 6, 10, 20, 30)
    res = plan_reminders([appt(starts_at=dub(2026, 6, 10, 23, 30))], now)
    assert len(res) == 1
    assert res[0]["send_at"].astimezone(UTC) == now.astimezone(UTC)
    assert "Final reminder" not in res[0]["text"]


def test_sort_order():
    apps = [appt(id="b", starts_at=dub(2026, 6, 12, 14)),
            appt(id="a", starts_at=dub(2026, 6, 12, 14)),
            appt(id="c", starts_at=dub(2026, 6, 11, 12))]
    res = plan_reminders(apps, EARLY)
    keys = [(r["send_at"].astimezone(UTC), r["appointment_id"]) for r in res]
    assert keys == sorted(keys)
    assert [r["appointment_id"] for r in res][:2] == ["a", "b"]


def test_exact_keys():
    for r in plan_reminders([appt()], EARLY):
        assert set(r) == {"appointment_id", "channel", "send_at", "text"}


def test_send_at_within_bounds():
    start = dub(2026, 6, 10, 9)
    for hrs in range(0, 120, 3):
        now = start - timedelta(hours=hrs, minutes=17)
        for r in plan_reminders([appt(starts_at=start)], now):
            assert now <= r["send_at"] <= start


def test_naive_raises_without_pii():
    with pytest.raises(ValueError) as e:
        plan_reminders([appt(starts_at=datetime(2026, 6, 10, 14))], EARLY)
    assert EMAIL not in str(e.value) and "Jane" not in str(e.value)
    with pytest.raises(ValueError):
        plan_reminders([appt()], datetime(2026, 6, 1))


def test_inputs_not_mutated():
    apps = [appt(), appt(id="a2", optout_sms_v2=True)]
    before = copy.deepcopy(apps)
    plan_reminders(apps, EARLY)
    assert apps == before


def test_no_pii_in_logs(caplog):
    caplog.set_level(logging.DEBUG)
    plan_reminders([appt(), appt(id="a2", optout_sms_v2=True), appt(id="a3", phone="", email="")], EARLY)
    assert EMAIL not in caplog.text
    assert PHONE not in caplog.text
    assert "Jane" not in caplog.text
    assert "a1" in caplog.text
    infos = [r for r in caplog.records if r.levelno == logging.INFO and "reminder planned" in r.getMessage()]
    assert len(infos) == 4