# Brennan Opticians appointment reminders.
#
# Deviations from the brief (no tools were available, so none of this was run):
# - The tests are included at the bottom of this single module instead of a
#   separate test file. They have NOT been executed. To split them out, move
#   everything below the "tests" marker into test_reminders.py and import from
#   this module. Run with: pytest
# - The house rule asks for the contact in the INFO line, but the privacy
#   requirement forbids logging emails, phones and names. The privacy rule wins:
#   the INFO line carries only appointment id, reminder number, channel, send_at.

"""Reminder planning for Brennan Opticians.

plan_reminders(appointments, now) is pure. It holds no memory of what was sent,
so de-duplicating repeated runs (the immediate first reminder is re-issued on
every run while within 48h of the appointment) is the caller's job.
"""

import copy
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DEFAULT_TZ = "Europe/Dublin"
# Single config point for per-country timezones. Empty on purpose: everyone,
# including PL, uses Europe/Dublin as the client asked.
COUNTRY_TZ: dict[str, str] = {}

DEFAULT_SIGNATURE = "Chevonne Nee Divver"
COUNTRY_SIGNATURE = {"PL": "Grzegorz Szczepański"}
SMS_LIMIT = 160
# NOTE: accented characters such as "ń" can push real carriers into UCS-2
# encoding (70 chars per segment). We implement the stated 160 limit anyway.

_UTC = timezone.utc


def _tz_for(country) -> ZoneInfo:
    key = country.strip().upper() if isinstance(country, str) else ""
    return ZoneInfo(COUNTRY_TZ.get(key, DEFAULT_TZ))


def _u(dt: datetime) -> datetime:
    return dt.astimezone(_UTC)


def _quiet(dt: datetime) -> bool:
    return dt.hour >= 21 or dt.hour < 8


def _shift_quiet(dt: datetime) -> datetime:
    """dt must be in the local zone. Moves quiet-hour times back to 20:00."""
    if not _quiet(dt):
        return dt
    d = dt.date()
    if dt.hour < 8:
        d = d - timedelta(days=1)
    return datetime(d.year, d.month, d.day, 20, tzinfo=dt.tzinfo)


def _next_8(dt: datetime) -> datetime:
    d = dt.date()
    if dt.hour >= 8:
        d = d + timedelta(days=1)
    return datetime(d.year, d.month, d.day, 8, tzinfo=dt.tzinfo)


def _schedule(nominal_u, now_u, start_u, tz):
    shifted = _shift_quiet(nominal_u.astimezone(tz))
    if _u(shifted) < now_u:
        now_l = now_u.astimezone(tz)
        shifted = now_l if not _quiet(now_l) else _next_8(now_l)
    if _u(shifted) >= start_u:
        return None
    return shifted.astimezone(tz)


def _text(name: str, start_local: datetime, signature: str) -> str:
    greeting = f"Hi {name}," if name else "Hi,"
    date = f"{start_local.day:02d}/{start_local.month:02d}/{start_local.year:04d}"
    time = f"{start_local.hour:02d}:{start_local.minute:02d}"
    return (f"{greeting} this is a reminder of your appointment at "
            f"Brennan Opticians on {date} at {time}. {signature}")


def _sms_text(name: str, start_local: datetime, signature: str) -> str:
    parts = name.split()
    ladder = [" ".join(parts)]
    if len(parts) > 1:
        ladder.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        ladder.append(parts[0])
    ladder.append("")
    text = ""
    for n in ladder:
        text = _text(n, start_local, signature)
        if len(text) <= SMS_LIMIT:
            break
    return text


def _clean(v):
    return v.strip() if isinstance(v, str) and v.strip() else None


def _plan_one(a, idx, now_u, seen):
    if not isinstance(a, dict):
        logger.debug("skip index=%d reason=bad_record", idx)
        return []
    aid = a.get("id")
    if aid is None or aid == "":
        logger.debug("skip index=%d reason=missing_id", idx)
        return []
    if aid in seen:
        logger.debug("skip id=%s reason=duplicate_id", aid)
        return []
    seen.add(aid)
    status = a.get("status")
    if not isinstance(status, str):
        logger.debug("skip id=%s reason=bad_status", aid)
        return []
    starts = a.get("starts_at")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        logger.debug("skip id=%s reason=bad_starts_at", aid)
        return []
    if status.strip().lower() in ("cancelled", "canceled"):
        logger.debug("skip id=%s reason=cancelled", aid)
        return []
    start_u = _u(starts)
    if start_u <= now_u:
        logger.debug("skip id=%s reason=past", aid)
        return []

    phone = _clean(a.get("phone"))
    email = _clean(a.get("email"))
    # Only optout_sms_v2 is read; anything but a literal False is an opt-out.
    opted_out = a.get("optout_sms_v2") is not False
    if phone and not opted_out:
        channel = "sms"
    elif email:
        channel = "email"
    else:
        logger.debug("skip id=%s reason=no_contact", aid)
        return []

    tz = _tz_for(a.get("country"))
    country = a.get("country")
    sig = COUNTRY_SIGNATURE.get(
        country.strip().upper() if isinstance(country, str) else "",
        DEFAULT_SIGNATURE)
    raw_name = a.get("customer_name")
    name = " ".join(raw_name.split()) if isinstance(raw_name, str) else ""
    start_local = start_u.astimezone(tz)
    if channel == "sms":
        text = _sms_text(name, start_local, sig)
    else:
        text = _text(name, start_local, sig)

    nominals = (
        (1, max(start_u - timedelta(hours=48), now_u)),
        (2, start_u - timedelta(hours=2)),
    )
    out = []
    for n, nominal in nominals:
        if n == 2 and nominal < now_u:
            logger.debug("skip id=%s reason=reminder2_past", aid)
            continue
        send = _schedule(nominal, now_u, start_u, tz)
        if send is None:
            logger.debug("skip id=%s reason=reminder%d_not_before_start", aid, n)
            continue
        logger.info("reminder planned id=%s n=%d channel=%s send_at=%s",
                    aid, n, channel, send.isoformat())
        out.append({"appointment_id": aid, "channel": channel,
                    "send_at": send, "text": text})
    return out


def plan_reminders(appointments, now):
    """Plan reminders for a batch of appointments.

    Pure function: no input mutation, no clock access. It holds no memory of
    what was sent, so de-duplicating repeated runs (the immediate first
    reminder is re-issued each run) is the caller's job.
    Returns dicts with keys appointment_id, channel, send_at, text, sorted by
    send_at (stable on input order).
    """
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_u = _u(now)
    out, seen = [], set()
    for idx, a in enumerate(appointments or []):
        try:
            out.extend(_plan_one(a, idx, now_u, seen))
        except Exception:
            logger.debug("skip index=%d reason=error", idx)
    out.sort(key=lambda r: _u(r["send_at"]))
    return out


# ------------------------------ tests ------------------------------

DUB = ZoneInfo("Europe/Dublin")


def D(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUB)


def mk(**kw):
    base = {"id": "a1", "customer_name": "Mary", "email": "mary@example.com",
            "phone": "0851234567", "country": "IE", "status": "booked",
            "starts_at": D(2026, 10, 26, 10), "optout_sms_v2": False}
    base.update(kw)
    return base


NOW = D(2026, 10, 13, 9)


def test_cancelled_skipped():
    for s in ("cancelled", " Cancelled ", "CANCELED", "canceled"):
        assert plan_reminders([mk(status=s)], NOW) == []
    assert len(plan_reminders([mk(status="no-show")], NOW)) == 2


def test_naive_now_raises():
    try:
        plan_reminders([], datetime(2026, 10, 13))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_empty():
    assert plan_reminders([], NOW) == []


def test_output_shape_and_tz():
    r = plan_reminders([mk()], NOW)
    assert set(r[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert r[0]["send_at"].tzinfo.key == "Europe/Dublin"


def test_dst_end_example():
    r = plan_reminders([mk()], NOW)
    assert [x["send_at"] for x in r] == [D(2026, 10, 24, 11), D(2026, 10, 26, 8)]
    assert r[0]["text"] == ("Hi Mary, this is a reminder of your appointment at "
                            "Brennan Opticians on 26/10/2026 at 10:00. "
                            "Chevonne Nee Divver")


def test_spring_forward():
    # Mon 30 Mar 2026 10:00 IST; 48h elapsed back is 09:00 GMT on Sat 28 Mar.
    r = plan_reminders([mk(starts_at=D(2026, 3, 30, 10))], D(2026, 3, 20, 9))
    assert r[0]["send_at"] == D(2026, 3, 28, 9)
    assert (r[0]["send_at"].hour, r[0]["send_at"].utcoffset()) == (9, timedelta(0))


def test_timing_and_immediate():
    appt = mk(starts_at=D(2026, 10, 15, 14))
    r = plan_reminders([appt], D(2026, 10, 13, 10))
    assert [x["send_at"] for x in r] == [D(2026, 10, 13, 14), D(2026, 10, 15, 12)]
    now = D(2026, 10, 14, 10)
    r = plan_reminders([appt], now)
    assert [x["send_at"] for x in r] == [now, D(2026, 10, 15, 12)]


def test_under_two_hours_and_past():
    now = D(2026, 10, 14, 10)
    r = plan_reminders([mk(starts_at=D(2026, 10, 14, 11))], now)
    assert [x["send_at"] for x in r] == [now]
    assert plan_reminders([mk(starts_at=now)], now) == []
    assert plan_reminders([mk(starts_at=D(2026, 10, 14, 9))], now) == []


def test_quiet_boundaries():
    assert _shift_quiet(D(2026, 10, 20, 21, 0)) == D(2026, 10, 20, 20)
    assert _shift_quiet(D(2026, 10, 20, 20, 59)) == D(2026, 10, 20, 20, 59)
    assert _shift_quiet(D(2026, 10, 20, 0, 0)) == D(2026, 10, 19, 20)
    assert _shift_quiet(D(2026, 10, 20, 7, 59)) == D(2026, 10, 19, 20)
    assert _shift_quiet(D(2026, 10, 20, 8, 0)) == D(2026, 10, 20, 8)
    assert _shift_quiet(D(2026, 11, 1, 0, 0)) == D(2026, 10, 31, 20)


def _r2(start, now):
    r = plan_reminders([mk(starts_at=start)], now)
    return r[-1]["send_at"] if r else None


def test_worked_examples():
    start = D(2026, 10, 20, 9)
    assert _r2(start, D(2026, 10, 13, 9)) == D(2026, 10, 19, 20)
    assert _r2(start, D(2026, 10, 19, 20, 30)) == D(2026, 10, 19, 20, 30)
    assert _r2(start, D(2026, 10, 19, 22)) == D(2026, 10, 20, 8)
    assert plan_reminders([mk(starts_at=D(2026, 10, 20, 7, 30))],
                          D(2026, 10, 19, 22)) == []


def test_utc_equivalence():
    utc = timezone.utc
    a = plan_reminders([mk()], NOW)
    b = plan_reminders([mk(starts_at=D(2026, 10, 26, 10).astimezone(utc))],
                       NOW.astimezone(utc))
    assert a == b


def test_channels():
    def ch(**kw):
        r = plan_reminders([mk(**kw)], NOW)
        return {x["channel"] for x in r}
    assert ch() == {"sms"}
    assert ch(optout_sms_v2=True) == {"email"}
    for v in ("false", None):
        assert ch(optout_sms_v2=v) == {"email"}
    a = mk()
    del a["optout_sms_v2"]
    assert {x["channel"] for x in plan_reminders([a], NOW)} == {"email"}
    assert ch(phone=None) == {"email"}
    assert ch(phone="   ") == {"email"}
    assert ch(optout_sms_v2=True, email="  ") == set()
    assert ch(optout_sms_v2=True, email=None) == set()
    assert ch(phone=None, email=None) == set()
    assert ch(email=None) == {"sms"}


def test_old_optout_field_ignored():
    r = plan_reminders([mk(opt_out=True, optout_sms_v2=False)], NOW)
    assert {x["channel"] for x in r} == {"sms"}
    r = plan_reminders([mk(opt_out=False, optout_sms_v2=True)], NOW)
    assert {x["channel"] for x in r} == {"email"}


def test_signature_and_blank_name():
    for c in ("PL", " pl "):
        r = plan_reminders([mk(country=c)], NOW)
        assert all(x["text"].endswith(". Grzegorz Szczepański") for x in r)
    r = plan_reminders([mk(country=None, customer_name="  ")], NOW)
    assert r[0]["text"].startswith("Hi, this is a reminder")
    assert r[0]["text"].endswith("Chevonne Nee Divver")


def test_sms_ladder():
    start = D(2026, 10, 26, 10)
    base = _text("", start, DEFAULT_SIGNATURE)
    B = SMS_LIMIT - len(base) - 1

    def go(name, **kw):
        return plan_reminders([mk(customer_name=name, **kw)], NOW)[0]["text"]

    t = go("Mary " + "L" * B)
    assert t.startswith("Hi Mary L., this") and len(t) <= 160
    t = go("F" * (B - 2) + " Lx")
    assert t.startswith("Hi " + "F" * (B - 2) + ", this") and len(t) <= 160
    t = go("F" * (B + 1))
    assert t.startswith("Hi, this") and len(t) <= 160
    t = go("Mary Ann O'Brien")
    assert t.startswith("Hi Mary Ann O'Brien,")
    for name in ("Mary " + "L" * B, "F" * (B + 1)):
        for c in ("IE", "PL"):
            t = go(name, country=c)
            assert len(t) <= 160 and "26/10/2026 at 10:00" in t
            assert t.endswith(COUNTRY_SIGNATURE.get(c, DEFAULT_SIGNATURE))
    long_name = "Mary " + "L" * B
    e = go(long_name, optout_sms_v2=True)
    assert e.startswith("Hi " + long_name + ",") and len(e) > 160


def test_ordering_stable():
    a1, a2 = mk(id="a1"), mk(id="a2")
    r = plan_reminders([a1, a2], NOW)
    assert [x["appointment_id"] for x in r] == ["a1", "a2", "a1", "a2"]
    early = mk(id="b", starts_at=D(2026, 10, 16, 12))
    r = plan_reminders([a1, early], NOW)
    assert r[0]["appointment_id"] == "b"
    keys = [x["send_at"].astimezone(timezone.utc) for x in r]
    assert keys == sorted(keys)


def test_non_mutation():
    data = [mk(), mk(id="a2", status="cancelled")]
    before = copy.deepcopy(data)
    plan_reminders(data, NOW)
    assert data == before


def test_bad_records_and_duplicates():
    naive = mk(id="n", starts_at=datetime(2026, 10, 26, 10))
    no_id = mk()
    del no_id["id"]
    no_start = mk(id="s")
    del no_start["starts_at"]
    no_status = mk(id="t")
    del no_status["status"]
    dup = mk(starts_at=D(2026, 11, 30, 10))
    r = plan_reminders([naive, no_id, no_start, no_status, "junk", None,
                        mk(), dup], NOW)
    assert [x["appointment_id"] for x in r] == ["a1", "a1"]
    assert r[0]["send_at"] == D(2026, 10, 24, 11)


def test_no_pii_in_logs(caplog):
    emails = ["secret1@example.com", "secret2@example.com", "secret3@example.com"]
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=__name__)
    bad = [mk(id="n", email=emails[0], starts_at=datetime(2026, 10, 26, 10)),
           mk(id="w", email=emails[1], starts_at="tomorrow"),
           {"email": emails[2], "customer_name": "Zed Zebra"},
           mk(id="ok", customer_name="Visible Name", phone="0879999999")]
    r = plan_reminders(bad, NOW)
    assert len(r) == 2
    infos = [x for x in caplog.records if x.levelno == logging.INFO]
    assert len(infos) == 2
    for rec in caplog.records:
        blob = rec.getMessage() + (rec.exc_text or "")
        for e in emails + ["Zed", "Visible Name", "0879999999"]:
            assert e not in blob
    for e in emails:
        assert e not in caplog.text
    try:
        plan_reminders([mk(email=emails[0])], datetime(2026, 1, 1))
    except ValueError as exc:
        assert emails[0] not in str(exc)