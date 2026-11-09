"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now).

Notes for the client (please confirm):
* OPT-OUT AMBIGUITY: the brief says "text them if optout_sms_v2 is true", but the
  field name means true = opted out. PM default applied: SMS only when the flag is
  explicitly False; missing or None means no SMS. Flip it in _sms_allowed().
  The legacy `opt_out` field is never read.
* LOGGING: house rule is one INFO line per planned reminder with channel and
  contact, so the SMS phone number is logged. PM requirement 11 says ids only, so
  please confirm that logging phone numbers is acceptable. Email is never logged.
* The tests below were written but NOT executed (no execution tool was available).
  Run: python3 -m pytest -q <path to this file>
"""
import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Dublin")
log = logging.getLogger("brennan.reminders")
SMS_LIMIT = 160


def _sms_allowed(optout_sms_v2):
    """True = opted out (field semantics). SMS only when explicitly False."""
    return optout_sms_v2 is False


def _safe_id(a):
    i = a.get("id") if isinstance(a, dict) else None
    return i if isinstance(i, (str, int)) else "<unknown>"


def _quiet_shift(t):
    t = t.astimezone(TZ)
    if t.hour >= 21:
        return datetime(t.year, t.month, t.day, 20, tzinfo=TZ)
    if t.hour < 8:
        p = t - timedelta(days=1)
        return datetime(p.year, p.month, p.day, 20, tzinfo=TZ)
    return t


def _next_8(now):
    n = now.astimezone(TZ)
    c = datetime(n.year, n.month, n.day, 8, tzinfo=TZ)
    if c <= n:
        d = n.date() + timedelta(days=1)
        c = datetime(d.year, d.month, d.day, 8, tzinfo=TZ)
    return c


def _adjust(t, now, starts):
    s = _quiet_shift(t)
    if s < now:
        s = _next_8(now)
    return s if s < starts else None


def _build_text(name, starts, country):
    sig = "Grzegorz Szczepański" if (
        isinstance(country, str) and country.strip().casefold() == "pl"
    ) else "Siobhán Ní Dhuibhir"
    local = starts.astimezone(TZ)
    when = f"{local:%Y-%m-%d} at {local:%H:%M}"
    parts = name.split() if isinstance(name, str) else []
    options = []
    if parts:
        options = [" ".join(parts), parts[0], parts[0][0] + "."]
    options.append("")
    text = ""
    for n in options:
        greet = f"Hi {n}," if n else "Hi,"
        text = unicodedata.normalize(
            "NFC", f"{greet} your Brennan Opticians appointment is on {when}. {sig}")
        if len(text) <= SMS_LIMIT:
            break
    return text


def _plan_one(a, now):
    if not isinstance(a, dict):
        raise ValueError("not a dict")
    aid = a["id"]
    starts = a["starts_at"]
    if not isinstance(aid, (str, int)):
        raise ValueError("bad id")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError("bad starts_at")
    status = a.get("status")
    if isinstance(status, str) and status.strip().lower() in ("cancelled", "canceled"):
        return []
    phone = a.get("phone")
    phone = phone.strip() if isinstance(phone, str) else ""
    if not phone or not _sms_allowed(a.get("optout_sms_v2")):
        return []
    if starts <= now:
        return []
    su = starts.astimezone(timezone.utc)
    raw1 = su - timedelta(hours=48)
    raw2 = su - timedelta(hours=2)
    r2 = None if raw2 < now else _adjust(raw2, now, starts)
    r1 = _adjust(max(raw1, now), now, starts)
    if r1 is not None and r2 is not None and r1 >= r2:
        r1 = None
    text = _build_text(a.get("customer_name"), starts, a.get("country"))
    out = []
    for order, t in ((1, r1), (2, r2)):
        if t is not None:
            out.append((order, {"appointment_id": aid, "channel": "sms",
                                "send_at": t.astimezone(TZ), "text": text,
                                "_phone": phone}))
    return out


def plan_reminders(appointments, now):
    """Return reminders (dicts: appointment_id, channel, send_at, text) sorted by send_at.

    Pure function: keeps no sent-state, so the CALLER MUST DEDUPLICATE across runs.
    Inputs are not mutated. Raises ValueError for a naive `now`. Malformed
    appointments are skipped and logged by id only.
    """
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for a in appointments:
        try:
            planned.extend((o, r) for o, r in _plan_one(a, now))
        except (KeyError, TypeError, ValueError, AttributeError):
            log.warning("Skipping malformed appointment %s", _safe_id(a))
    planned.sort(key=lambda p: (p[1]["send_at"], str(p[1]["appointment_id"]), p[0]))
    result = []
    for order, r in planned:
        phone = r.pop("_phone")
        log.info("Planned reminder %d for appointment %s via %s to %s at %s",
                 order, r["appointment_id"], r["channel"], phone,
                 r["send_at"].isoformat())
        result.append(r)
    return result


# ----------------------------- tests (pytest) -----------------------------

def D(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=TZ)


def mk(**kw):
    base = {"id": "A1", "customer_name": "Aoife Murphy", "email": "aoife@example.com",
            "phone": "+353871234567", "country": "IE", "status": "booked",
            "starts_at": D(2026, 6, 10, 10), "optout_sms_v2": False}
    base.update(kw)
    return base


EARLY = D(2026, 6, 1, 9)


def test_quiet_hour_boundaries():
    cases = [((22, 59), D(2026, 6, 10, 20, 59)),
             ((23, 0), D(2026, 6, 10, 20)),
             ((9, 59), D(2026, 6, 9, 20)),
             ((10, 0), D(2026, 6, 10, 8))]
    for (h, m), expected in cases:
        res = plan_reminders([mk(starts_at=D(2026, 6, 10, h, m))], EARLY)
        assert res[-1]["send_at"] == expected


def test_dst_spring_and_autumn():
    res = plan_reminders([mk(starts_at=D(2026, 3, 30, 10))], D(2026, 3, 1, 9))
    assert res[0]["send_at"] == D(2026, 3, 28, 9)
    assert res[0]["send_at"].utcoffset() == timedelta(0)
    res = plan_reminders([mk(starts_at=D(2026, 10, 26, 10))], D(2026, 10, 1, 9))
    assert res[0]["send_at"] == D(2026, 10, 24, 11)
    res = plan_reminders([mk(starts_at=D(2026, 3, 29, 3, 30))], D(2026, 3, 20, 9))
    assert res[-1]["send_at"] == D(2026, 3, 28, 20)


def test_text_in_dublin_time():
    s = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    t = plan_reminders([mk(starts_at=s)], D(2026, 6, 1, 9))[0]["text"]
    assert "2026-07-01 at 10:00" in t


def test_160_limit_staging():
    r = plan_reminders([mk(customer_name="Al " + "Z" * 200)], EARLY)
    assert "Hi Al," in r[0]["text"] and len(r[0]["text"]) <= 160
    r = plan_reminders([mk(customer_name="Q" * 200 + " Smith")], EARLY)
    assert "Hi Q.," in r[0]["text"] and len(r[0]["text"]) <= 160
    for x in r:
        assert "2026-06-10" in x["text"] and x["text"].endswith("Siobhán Ní Dhuibhir")


def test_signatures():
    r = plan_reminders([mk(country=" pl ")], EARLY)
    assert r[0]["text"].endswith("Grzegorz Szczepański")
    r = plan_reminders([mk()], EARLY)
    assert r[0]["text"].endswith("Siobhán Ní Dhuibhir")


def test_sorting_and_ties():
    a = [mk(id="B"), mk(id="A"), mk(id="C", starts_at=D(2026, 6, 9, 12))]
    r = plan_reminders(a, EARLY)
    keys = [(x["send_at"], x["appointment_id"]) for x in r]
    assert keys == sorted(keys)


def test_cancelled():
    for s in ("  Canceled ", "CANCELLED", "cancelled"):
        assert plan_reminders([mk(status=s)], EARLY) == []


def test_optout_and_phone():
    assert plan_reminders([mk(optout_sms_v2=True)], EARLY) == []
    assert plan_reminders([mk(optout_sms_v2=None)], EARLY) == []
    a = mk()
    del a["optout_sms_v2"]
    assert plan_reminders([a], EARLY) == []
    for p in (None, "", "   "):
        assert plan_reminders([mk(phone=p)], EARLY) == []
    assert plan_reminders([mk(opt_out=True)], EARLY)[0]["channel"] == "sms"


def test_acceptance_and_clamping():
    r = plan_reminders([mk()], D(2026, 6, 9, 23))
    assert len(r) == 1 and r[0]["send_at"] == D(2026, 6, 10, 8)
    now = D(2026, 6, 10, 14)
    r = plan_reminders([mk(starts_at=D(2026, 6, 10, 15))], now)
    assert len(r) == 1 and r[0]["send_at"] == now
    assert plan_reminders([mk(starts_at=D(2026, 6, 10, 23))], D(2026, 6, 10, 22)) == []
    now = D(2026, 6, 9, 12)
    r = plan_reminders([mk()], now)
    assert r[0]["send_at"] == now and len(r) == 2
    assert all(x["send_at"] >= now for x in r)


def test_naive_now_and_malformed_and_no_mutation():
    import copy
    try:
        plan_reminders([], datetime(2026, 6, 1))
        assert False
    except ValueError:
        pass
    good = mk()
    snap = copy.deepcopy(good)
    r = plan_reminders([{"id": "BAD", "starts_at": "x"}, "junk", good], EARLY)
    assert r and good == snap


def test_email_never_logged(caplog):
    caplog.set_level(logging.DEBUG)
    plan_reminders([mk(), mk(id="BAD", starts_at="x")], EARLY)
    assert "aoife@example.com" not in caplog.text
    assert "BAD" in caplog.text and "sms" in caplog.text