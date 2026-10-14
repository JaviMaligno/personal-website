# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-tolwz35k/reminders.py =====
# NOTE: I had no tools in this session, so this code was NOT executed and the tests were NOT run.
# Deviation from the house rule: the per-reminder INFO line logs appointment id and channel only,
# not the contact, because R12 forbids logging email, phone or name. Resolve this with the client.

```python
"""Appointment reminder planning for Brennan Opticians (standard library only)."""
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
_REQUIRED = ("id", "customer_name", "email", "phone", "country", "status",
             "starts_at", "optout_sms_v2")
_KINDS = (("2h", timedelta(hours=2)), ("48h", timedelta(hours=48)))  # 2h first (R14)
_ORDER = {"48h": 0, "2h": 1}


def _local_quiet(local):
    return local.time() >= time(21, 0) or local.time() < time(8, 0)


def _is_quiet(dt):
    return _local_quiet(dt.astimezone(DUBLIN))


def _shift_back(dt):
    """Move a send time in quiet hours back to the 20:00 immediately before it."""
    local = dt.astimezone(DUBLIN)
    if not _local_quiet(local):
        return dt
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    return datetime(day.year, day.month, day.day, 20, 0, tzinfo=DUBLIN)


def _clean(a):
    """Validate an appointment; raise ValueError (message free of personal data)."""
    if not isinstance(a, dict):
        raise ValueError("appointment is not a dict")
    for k in _REQUIRED:
        if k not in a:
            raise ValueError("missing key " + k)
    s = a["starts_at"]
    if not isinstance(s, datetime) or s.tzinfo is None or s.utcoffset() is None:
        raise ValueError("starts_at is not a tz-aware datetime")
    for k in ("customer_name", "email", "phone", "country", "status"):
        if a[k] is not None and not isinstance(a[k], str):
            raise ValueError("bad type for " + k)
    return {
        "id": a["id"],
        "name": " ".join((a["customer_name"] or "").split()),
        "email": (a["email"] or "").strip(),
        "phone": (a["phone"] or "").strip(),
        "country": (a["country"] or "").strip().upper(),
        "status": (a["status"] or "").strip().lower(),
        "start": s,
        "optout": bool(a["optout_sms_v2"]),
    }


def _channel(phone, email, optout):
    if phone and not optout:
        return "sms"
    if email:
        return "email"
    return None


def _send_time(aid, start, kind, delta, now):
    """Return the final send_at for one reminder, or None if dropped."""
    send = start.astimezone(ZoneInfo("UTC")) - delta
    if kind == "48h" and send < now:
        send = now
    send = _shift_back(send)
    if send < now:
        if _is_quiet(now):
            log.info("appointment %s: %s reminder dropped (quiet hours, shifted time in past)",
                     aid, kind)
            return None
        send = now
    if send >= start:
        log.info("appointment %s: %s reminder dropped (not before start)", aid, kind)
        return None
    return send


def _text(name, start, kind, sig):
    local = start.astimezone(DUBLIN)
    greet = "Hi %s," % name if name else "Hi,"
    lead = ("your Brennan Opticians appointment is in 2 hours, on" if kind == "2h"
            else "your Brennan Opticians appointment is on")
    return "%s reminder: %s %s at %s. %s" % (
        greet, lead, local.strftime("%d/%m/%Y"), local.strftime("%H:%M"), sig)


def _sms_text(name, start, kind, sig):
    first = name.split()[0] if name else ""
    cands = [name, first]
    cands += [first[:n - 1] + "." for n in range(len(first) - 1, 1, -1)]
    if first:
        cands.append(first[0] + ".")
    cands.append("")
    text = ""
    for c in cands:
        text = _text(c, start, kind, sig)
        if len(text) <= SMS_LIMIT:
            break
    return text


def plan_reminders(appointments, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    out = []
    for a in appointments:
        aid = a.get("id") if isinstance(a, dict) else None
        try:
            c = _clean(a)
        except Exception as e:
            log.warning("skipping malformed appointment %s: %s", aid, e)
            continue
        aid = c["id"]
        if c["status"] == "cancelled":
            log.info("appointment %s: cancelled, no reminders", aid)
            continue
        channel = _channel(c["phone"], c["email"], c["optout"])
        if channel is None:
            log.warning("appointment %s: no usable contact, skipped", aid)
            continue
        sig = "Grzegorz Szczepański" if c["country"] == "PL" else "Siobhán Ní Dhuibhir"
        times = {}
        for kind, delta in _KINDS:  # 2h first
            try:
                t = _send_time(aid, c["start"], kind, delta, now)
            except Exception as e:
                log.error("appointment %s: %s reminder failed (%s)", aid, kind, type(e).__name__)
                continue
            if t is not None:
                times[kind] = t
        if "2h" in times and "48h" in times and times["2h"] == times["48h"]:
            log.info("appointment %s: 48h reminder dropped (same send time as 2h)", aid)
            del times["48h"]
        for kind, t in times.items():
            try:
                if channel == "sms":
                    text = _sms_text(c["name"], c["start"], kind, sig)
                else:
                    text = _text(c["name"], c["start"], kind, sig)
                rem = {"appointment_id": aid, "channel": channel,
                       "send_at": t.astimezone(DUBLIN), "text": text}
            except Exception as e:
                log.error("appointment %s: %s reminder failed (%s)", aid, kind, type(e).__name__)
                continue
            log.info("planned %s reminder for appointment %s via %s at %s",
                     kind, aid, channel, rem["send_at"].isoformat())
            out.append((t, str(aid), _ORDER[kind], rem))
    out.sort(key=lambda x: x[:3])
    return [x[3] for x in out]
```

# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-tolwz35k/test_reminders.py =====

```python
import copy
import inspect
import logging
from datetime import datetime, timedelta, timezone

import pytest

import reminders
from reminders import DUBLIN, plan_reminders

UTC = timezone.utc
EMAIL = "secret.person@example.com"
PHONE = "+353851234567"
NAME = "Jane Secretname"
NOW = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
START = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)  # 13:00 Dublin


def appt(**kw):
    d = {"id": "A1", "customer_name": NAME, "email": EMAIL, "phone": PHONE,
         "country": "IE", "status": "booked", "starts_at": START,
         "optout_sms_v2": False}
    d.update(kw)
    return d


def two(rs):
    return {("2h" if r["send_at"].astimezone(UTC) > rs[0]["send_at"].astimezone(UTC) else "48h"): r
            for r in rs} if len(rs) == 2 else None


def test_r1_keys_and_count():
    rs = plan_reminders([appt()], NOW)
    assert len(rs) == 2
    for r in rs:
        assert set(r) == {"appointment_id", "channel", "send_at", "text"}
        assert r["channel"] in ("sms", "email")
        assert r["send_at"].tzinfo is not None


def test_r5_times_and_dublin_tz():
    rs = plan_reminders([appt()], NOW)
    assert [r["send_at"] for r in rs] == [START - timedelta(hours=48), START - timedelta(hours=2)]
    assert all(r["send_at"].utcoffset() == timedelta(hours=1) for r in rs)
    assert str(rs[0]["send_at"].tzinfo) == "Europe/Dublin"


@pytest.mark.parametrize("start,date,hhmm", [
    (datetime(2026, 1, 15, 10, 0, tzinfo=UTC), "15/01/2026", "10:00"),
    (datetime(2026, 7, 15, 10, 0, tzinfo=UTC), "15/07/2026", "11:00"),
    (datetime(2026, 3, 30, 9, 0, tzinfo=UTC), "30/03/2026", "10:00"),
    (datetime(2026, 10, 26, 9, 0, tzinfo=UTC), "26/10/2026", "09:00"),
    (datetime(2026, 6, 10, 23, 30, tzinfo=UTC), "11/06/2026", "00:30"),
])
def test_r3_r15_date_time_local(start, date, hhmm):
    rs = plan_reminders([appt(starts_at=start)], start - timedelta(days=10))
    assert rs
    for r in rs:
        assert date in r["text"] and hhmm in r["text"]


def test_r15_48h_absolute_across_dst():
    start = datetime(2026, 3, 30, 9, 0, tzinfo=UTC)
    rs = plan_reminders([appt(starts_at=start)], start - timedelta(days=10))
    assert rs[0]["send_at"] == start - timedelta(hours=48)
    assert rs[0]["send_at"].astimezone(DUBLIN).strftime("%H:%M") == "09:00"


def test_r4_opt_out_never_read():
    class Guard(dict):
        def _chk(self, k):
            if k == "opt_out":
                raise AssertionError("opt_out accessed")

        def __getitem__(self, k):
            self._chk(k)
            return super().__getitem__(k)

        def __contains__(self, k):
            self._chk(k)
            return super().__contains__(k)

        def get(self, k, d=None):
            self._chk(k)
            return super().get(k, d)

    g = Guard(appt())
    g["opt_out"] = True
    rs = plan_reminders([g], NOW)
    assert {r["channel"] for r in rs} == {"sms"}
    assert "opt_out" not in inspect.getsource(reminders)


def test_r6_now_substitution():
    now = datetime(2026, 6, 9, 10, 0, tzinfo=UTC)
    rs = plan_reminders([appt()], now)
    assert rs[0]["send_at"] == now
    assert rs[1]["send_at"] == START - timedelta(hours=2)


def test_r7_never_in_past_property():
    starts = [START, datetime(2026, 6, 10, 21, 30, tzinfo=UTC), datetime(2026, 6, 10, 5, 0, tzinfo=UTC),
              datetime(2026, 3, 30, 9, 0, tzinfo=UTC)]
    for s in starts:
        a = appt(starts_at=s)
        now = s - timedelta(hours=60)
        while now < s + timedelta(hours=1):
            for r in plan_reminders([a], now):
                assert r["send_at"] >= now
                assert r["send_at"] < s
            now += timedelta(minutes=37)


def test_r8_channels():
    assert {r["channel"] for r in plan_reminders([appt()], NOW)} == {"sms"}
    assert {r["channel"] for r in plan_reminders([appt(optout_sms_v2=True)], NOW)} == {"email"}
    assert {r["channel"] for r in plan_reminders([appt(phone="")], NOW)} == {"email"}
    assert {r["channel"] for r in plan_reminders([appt(phone=None)], NOW)} == {"email"}


def test_r8_no_contact_skipped_and_logged(caplog):
    caplog.set_level(logging.DEBUG)
    assert plan_reminders([appt(optout_sms_v2=True, email="")], NOW) == []
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert PHONE not in caplog.text


@pytest.mark.parametrize("country,sig", [("IE", "Siobhán Ní Dhuibhir"), ("PL", "Grzegorz Szczepański")])
@pytest.mark.parametrize("phone", [PHONE, ""])
def test_r9_r13_limit_and_signature(country, sig, phone):
    long_name = "Bartholomew-Maximilian Featherstonehaugh " * 6
    rs = plan_reminders([appt(customer_name=long_name, country=country, phone=phone)], NOW)
    for r in rs:
        assert r["text"].endswith(sig)
        assert "10/06/2026" in r["text"] and "13:00" in r["text"]
        if phone:
            assert len(r["text"]) <= 160
        else:
            assert long_name.strip() in r["text"]


def test_r9_short_name_kept_and_first_name_fallback():
    rs = plan_reminders([appt(customer_name="Jo Bloggs")], NOW)
    assert "Hi Jo Bloggs," in rs[0]["text"]
    rs = plan_reminders([appt(customer_name="Jo " + "X" * 100, country="PL")], NOW)
    assert all(len(r["text"]) <= 160 and r["text"].startswith("Hi Jo,") for r in rs)


def _last_2h(local_send):
    start = local_send.astimezone(UTC) + timedelta(hours=2)
    return plan_reminders([appt(starts_at=start)], start - timedelta(days=10))[-1]["send_at"]


@pytest.mark.parametrize("h,m,day_off,exp_h", [
    (20, 59, 0, 20), (21, 0, 0, 20), (7, 59, -1, 20), (8, 0, 0, 8), (3, 0, -1, 20), (23, 59, 0, 20)])
def test_r10_quiet_boundaries(h, m, day_off, exp_h):
    local = datetime(2026, 6, 10, h, m, tzinfo=DUBLIN)
    got = _last_2h(local).astimezone(DUBLIN)
    if (h, m) == (20, 59) or (h, m) == (8, 0):
        assert got == local
    else:
        exp = datetime(2026, 6, 10 + day_off, exp_h, 0, tzinfo=DUBLIN)
        assert got == exp


def test_r7_r10_now_in_quiet_drops_first():
    now = datetime(2026, 6, 9, 21, 0, tzinfo=UTC)  # 22:00 Dublin
    rs = plan_reminders([appt()], now)
    assert len(rs) == 1
    assert rs[0]["send_at"] == START - timedelta(hours=2)


def test_r7_r10_both_dropped_when_quiet_and_near_start():
    now = datetime(2026, 6, 9, 22, 0, tzinfo=UTC)  # 23:00 Dublin
    start = datetime(2026, 6, 9, 23, 30, tzinfo=UTC)
    assert plan_reminders([appt(starts_at=start)], now) == []


def test_identical_send_at_keeps_only_2h(caplog):
    caplog.set_level(logging.INFO)
    now = datetime(2026, 6, 9, 14, 0, tzinfo=UTC)
    start = datetime(2026, 6, 9, 15, 0, tzinfo=UTC)
    rs = plan_reminders([appt(starts_at=start)], now)
    assert len(rs) == 1 and rs[0]["send_at"] == now
    assert "in 2 hours" in rs[0]["text"]


def test_past_appointment_yields_nothing():
    assert plan_reminders([appt()], START + timedelta(hours=1)) == []
    assert plan_reminders([appt()], START) == []


def test_r11_cancelled():
    assert plan_reminders([appt(status="Cancelled"), appt(id="B", status="CANCELLED")], NOW) == []


def test_r12_r2_no_pii_in_logs(caplog):
    caplog.set_level(logging.DEBUG)
    bad = [appt(id="N", starts_at=datetime(2026, 6, 10, 12, 0)),
           {k: v for k, v in appt(id="M").items() if k != "status"},
           appt(id="X", optout_sms_v2=True, phone="", email=""),
           appt(id="C", status="cancelled"),
           appt(id="E", phone="", optout_sms_v2=True), "garbage", appt(id="OK")]
    rs = plan_reminders(bad, NOW)
    assert {r["appointment_id"] for r in rs} == {"E", "OK"}
    assert caplog.records
    for r in caplog.records:
        m = r.getMessage()
        assert EMAIL not in m and PHONE not in m and "Secretname" not in m
    assert EMAIL not in caplog.text
    assert any("malformed" in r.getMessage() for r in caplog.records)


def test_info_line_per_reminder(caplog):
    caplog.set_level(logging.INFO)
    rs = plan_reminders([appt()], NOW)
    planned = [r for r in caplog.records if r.getMessage().startswith("planned")]
    assert len(planned) == len(rs) == 2
    assert all("A1" in r.getMessage() and "sms" in r.getMessage() for r in planned)


def test_r14_2h_first_and_error_isolated(monkeypatch):
    calls = []
    orig = reminders._send_time

    def fake(aid, start, kind, delta, now):
        calls.append(kind)
        if kind == "48h":
            raise RuntimeError("boom")
        return orig(aid, start, kind, delta, now)

    monkeypatch.setattr(reminders, "_send_time", fake)
    rs = plan_reminders([appt()], NOW)
    assert calls == ["2h", "48h"]
    assert len(rs) == 1 and rs[0]["send_at"] == START - timedelta(hours=2)


def test_r16_sorted():
    a = [appt(id="z", starts_at=START), appt(id="a", starts_at=START),
         appt(id="m", starts_at=START - timedelta(days=3))]
    rs = plan_reminders(a, NOW)
    keys = [(r["send_at"], str(r["appointment_id"])) for r in rs]
    assert keys == sorted(keys)
    assert [r["appointment_id"] for r in rs[-2:]] == ["a", "z"]


def test_inputs_not_mutated():
    a = [appt(), appt(id="B", optout_sms_v2=True)]
    before = copy.deepcopy(a)
    plan_reminders(a, NOW)
    assert a == before
```