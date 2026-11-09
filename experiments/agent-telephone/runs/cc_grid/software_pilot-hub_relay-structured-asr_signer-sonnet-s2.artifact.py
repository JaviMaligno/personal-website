"""Brennan Opticians appointment reminder planner (stdlib only, pure and stateless).

Contents: the module first, pytest tests at the bottom (run: pytest <this file>).
I could not execute the tests in this environment, so they are unrun.

Defaults applied:
- R3: optout_sms_v2 missing or None counts as opted out.
- R7: dates look like "15 Oct 2026" with a hard-coded month table; times are 24h HH:MM Dublin.
- R9: status is matched case-insensitively and trimmed; "canceled" is also accepted.
- R13/R26: send_at is returned in Europe/Dublin; COUNTRY_ZONES maps countries to zones
  (empty, so Dublin for everyone including PL). Changing it is a one-line edit.
- R16: required fields are id, status and an aware starts_at; anything else missing is tolerated.
- R22: every status other than cancelled is active.
- R23: no de-duplication across runs (the caller's job); output has exactly 4 keys.
- R24: English text only; only the signature varies by country.
- R25: the 160 limit is len() code points (SMS_MAX_LEN).
- Logging: the house rule asks for the contact in the INFO line, but R10 forbids logging
  email/phone. R10 wins: the line carries appointment id, kind and channel only.
- Name shortening: "first name plus last initial" is rendered as "Pádraig D.".
"""
import logging
from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

UTC = timezone.utc
DEFAULT_ZONE = "Europe/Dublin"
COUNTRY_ZONES: dict[str, str] = {}  # e.g. {"GB": "Europe/London"}; empty -> Dublin for all
SMS_MAX_LEN = 160
FIRST_LEAD = timedelta(hours=48)
SECOND_LEAD = timedelta(hours=2)
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SEND_BEFORE_QUIET_HOUR = 20
DEFAULT_SIGNATURE = "Chevonne Nee Divver"
PL_SIGNATURE = "Grzegorz Szczepański"
GENERIC_GREETING = "there"
CANCELLED = {"cancelled", "canceled"}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class _Malformed(Exception):
    pass


def _norm(v):
    return v.strip().upper() if isinstance(v, str) else ""


def _zone_for(country) -> ZoneInfo:
    return ZoneInfo(COUNTRY_ZONES.get(_norm(country), DEFAULT_ZONE))


def _signature(country) -> str:
    return PL_SIGNATURE if _norm(country) == "PL" else DEFAULT_SIGNATURE


def _quiet(t: datetime, tz) -> bool:
    h = t.astimezone(tz).hour
    return h >= QUIET_START_HOUR or h < QUIET_END_HOUR


def _move_back(t: datetime, tz) -> datetime:
    local = t.astimezone(tz)
    d = local.date()
    if local.hour < QUIET_END_HOUR:
        d -= timedelta(days=1)
    return datetime.combine(d, time(SEND_BEFORE_QUIET_HOUR), tzinfo=tz).astimezone(UTC)


def _next_open(now: datetime, tz) -> datetime:
    local = now.astimezone(tz)
    d = local.date()
    if local.hour >= QUIET_START_HOUR:
        d += timedelta(days=1)
    return datetime.combine(d, time(QUIET_END_HOUR), tzinfo=tz).astimezone(UTC)


def _resolve(nominal, now, starts, tz):
    """All datetimes are UTC. Returns the send instant (UTC) or None to drop."""
    t = max(nominal, now)
    if not _quiet(t, tz):
        return t
    back = _move_back(t, tz)
    if back >= now:
        return back
    if not _quiet(now, tz):
        return now
    d = _next_open(now, tz)
    return d if d < starts else None


def _name_candidates(name):
    if not isinstance(name, str) or not name.split():
        return []
    parts = name.split()
    out = [" ".join(parts)]
    if len(parts) > 1:
        out.append(f"{parts[0]} {parts[-1][0]}.")
    out.append(parts[0])
    return out


def _build_text(name, starts, tz, sig, limit):
    local = starts.astimezone(tz)
    when = f"{local.day} {MONTHS[local.month - 1]} {local.year} at {local:%H:%M}"

    def make(n):
        return f"Hi {n}, reminder: your Brennan Opticians appointment is on {when}. {sig}"

    cands = _name_candidates(name)
    if limit is None:
        return make(cands[0] if cands else GENERIC_GREETING)
    for c in cands:
        if len(make(c)) <= limit:
            return make(c)
    return make(GENERIC_GREETING)


def _has(v):
    return isinstance(v, str) and bool(v.strip())


def _plan_one(appt, now):
    if not isinstance(appt, Mapping):
        raise _Malformed("not a mapping")
    aid = appt.get("id")
    if aid is None:
        raise _Malformed("missing id")
    starts = appt.get("starts_at")
    if "status" not in appt or appt["status"] is None:
        raise _Malformed("missing status")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise _Malformed("missing or naive starts_at")
    if str(appt["status"]).strip().lower() in CANCELLED:
        log.debug("appointment %s cancelled, no reminders", aid)
        return []
    opt = appt.get("optout_sms_v2")
    opted_out = opt is None or bool(opt)
    if _has(appt.get("phone")) and not opted_out:
        channel = "sms"
    elif _has(appt.get("email")):
        channel = "email"
    else:
        log.info("appointment %s: no usable channel, no reminder", aid)
        return []
    starts_u = starts.astimezone(UTC)
    now_u = now.astimezone(UTC)
    if starts_u <= now_u:
        return []
    tz = _zone_for(appt.get("country"))
    text = _build_text(appt.get("customer_name"), starts_u, tz,
                       _signature(appt.get("country")),
                       SMS_MAX_LEN if channel == "sms" else None)
    second = _resolve(starts_u - SECOND_LEAD, now_u, starts_u, tz)
    first = None
    if starts_u - now_u >= SECOND_LEAD:
        first = _resolve(starts_u - FIRST_LEAD, now_u, starts_u, tz)
        if first is not None and second is not None and first >= second:
            first = None
    out = []
    for order, when in ((0, first), (1, second)):
        if when is not None:
            out.append((when, str(aid), order, {
                "appointment_id": aid, "channel": channel,
                "send_at": when.astimezone(tz), "text": text}))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    rows = []
    for appt in appointments:
        aid = appt.get("id") if isinstance(appt, Mapping) else None
        try:
            rows.extend(_plan_one(appt, now))
        except _Malformed as e:
            log.warning("skipping malformed appointment id=%s: %s",
                        aid if aid is not None else "unavailable", e)
        except Exception as e:  # never include message text (may carry PII)
            log.error("failed planning appointment id=%s: %s",
                      aid if aid is not None else "unavailable", type(e).__name__)
    rows.sort(key=lambda r: r[:3])
    for when, _, order, rem in rows:
        # R10 overrides the house rule: no contact details, only id and channel.
        log.info("planned reminder appointment_id=%s kind=%s channel=%s send_at=%s",
                 rem["appointment_id"], "second" if order else "first",
                 rem["channel"], when.isoformat())
    return [r[3] for r in rows]


# ----------------------------- tests -----------------------------
import copy  # noqa: E402

DUB = ZoneInfo(DEFAULT_ZONE)
EMAIL = "pat.secret@example.com"


def _appt(**kw):
    a = {"id": "A1", "customer_name": "Pádraig", "email": EMAIL, "phone": "+353851234567",
         "country": "IE", "status": "booked", "optout_sms_v2": False,
         "starts_at": datetime(2026, 10, 15, 9, 30, tzinfo=DUB)}
    a.update(kw)
    return a


NOW = datetime(2026, 10, 1, 12, 0, tzinfo=DUB)


def test_basic_and_example_text():
    r = plan_reminders([_appt()], NOW)
    assert [set(x) for x in r] == [{"appointment_id", "channel", "send_at", "text"}] * 2
    assert r[0]["send_at"] < r[1]["send_at"]
    assert r[1]["text"] == ("Hi Pádraig, reminder: your Brennan Opticians appointment is on "
                            "15 Oct 2026 at 09:30. Chevonne Nee Divver")
    assert r[0]["channel"] == "sms"


def test_quiet_boundaries():
    d = lambda h, m, day=10: datetime(2026, 6, day, h, m, tzinfo=DUB).astimezone(UTC)
    far = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2027, 1, 1, tzinfo=UTC)
    cases = [(d(20, 59), d(20, 59)), (d(21, 0), d(20, 0)), (d(0, 0), d(20, 0, 9)),
             (d(7, 59), d(20, 0, 9)), (d(8, 0), d(8, 0))]
    for nominal, expected in cases:
        assert _resolve(nominal, far, end, DUB) == expected


def test_dst_elapsed_time():
    s = datetime(2026, 10, 26, 10, 0, tzinfo=DUB)
    r = plan_reminders([_appt(starts_at=s)], datetime(2026, 10, 1, 12, tzinfo=DUB))
    assert r[0]["send_at"] == datetime(2026, 10, 24, 10, tzinfo=UTC)
    assert r[0]["send_at"].hour == 11
    s = datetime(2026, 3, 29, 10, 0, tzinfo=DUB)
    r = plan_reminders([_appt(starts_at=s)], datetime(2026, 3, 1, 12, tzinfo=DUB))
    assert r[0]["send_at"] == datetime(2026, 3, 27, 9, tzinfo=UTC)
    assert r[0]["send_at"].hour == 9


def test_now_in_quiet_hours_defers():
    now = datetime(2026, 10, 1, 23, 0, tzinfo=DUB)
    r = plan_reminders([_appt(starts_at=now + timedelta(hours=40))], now)
    assert r[0]["send_at"] == datetime(2026, 10, 2, 8, 0, tzinfo=DUB)
    now = datetime(2026, 10, 15, 3, 0, tzinfo=DUB)
    r = plan_reminders([_appt(starts_at=datetime(2026, 10, 15, 10, tzinfo=DUB))], now)
    assert len(r) == 1 and r[0]["send_at"] == datetime(2026, 10, 15, 8, tzinfo=DUB)


def test_boundaries():
    now = datetime(2026, 10, 1, 12, 0, tzinfo=DUB)
    r = plan_reminders([_appt(starts_at=now + timedelta(hours=48))], now)
    assert len(r) == 2 and r[0]["send_at"] == now
    r = plan_reminders([_appt(starts_at=now + timedelta(hours=2))], now)
    assert len(r) == 1 and r[0]["send_at"] == now
    r = plan_reminders([_appt(starts_at=now + timedelta(hours=2, minutes=-1))], now)
    assert len(r) == 1 and r[0]["send_at"] == now
    assert plan_reminders([_appt(starts_at=now)], now) == []
    assert plan_reminders([_appt(starts_at=now - timedelta(hours=1))], now) == []


def test_channels_and_optout():
    assert plan_reminders([_appt(optout_sms_v2=True)], NOW)[0]["channel"] == "email"
    assert plan_reminders([_appt(optout_sms_v2=None)], NOW)[0]["channel"] == "email"
    assert plan_reminders([_appt(optout_sms_v2=True, email=" ")], NOW) == []
    assert plan_reminders([_appt(phone="  ", email="")], NOW) == []
    a = _appt(opt_out=True)
    assert plan_reminders([a], NOW)[0]["channel"] == "sms"
    del a["optout_sms_v2"]
    assert plan_reminders([a], NOW)[0]["channel"] == "email"
    assert plan_reminders([_appt(phone="", optout_sms_v2=False)], NOW)[0]["channel"] == "email"


def test_cancelled():
    for s in ("cancelled", " CANCELED ", "Cancelled"):
        assert plan_reminders([_appt(status=s)], NOW) == []
    assert plan_reminders([_appt(status="pending")], NOW) != []


def test_sms_shortening_and_signature():
    t = plan_reminders([_appt(customer_name="F" * 40 + " M " + "L" * 60)], NOW)[0]["text"]
    assert len(t) <= SMS_MAX_LEN and "F" * 40 + " L." in t and t.endswith(DEFAULT_SIGNATURE)
    t = plan_reminders([_appt(customer_name="F" * 100 + " " + "L" * 10, country=" pl ")],
                       NOW)[0]["text"]
    assert t.startswith("Hi there,") and t.endswith(PL_SIGNATURE)
    assert "15 Oct 2026 at 09:30" in t
    t = plan_reminders([_appt(customer_name=None, country=None)], NOW)[0]["text"]
    assert t.startswith("Hi there,") and t.endswith(DEFAULT_SIGNATURE)
    long_name = "F" * 100 + " " + "L" * 10
    t = plan_reminders([_appt(customer_name=long_name, optout_sms_v2=True)], NOW)[0]["text"]
    assert long_name in t and len(t) > SMS_MAX_LEN


def test_display_in_dublin_whatever_zone():
    s = datetime(2026, 7, 15, 8, 30, tzinfo=UTC)
    assert "15 Jul 2026 at 09:30" in plan_reminders([_appt(starts_at=s)], NOW)[0]["text"]


def test_sorting_and_purity():
    appts = [_appt(id="B"), _appt(id="A")]
    snap = copy.deepcopy(appts)
    r = plan_reminders(appts, NOW)
    assert appts == snap
    keys = [(x["send_at"], str(x["appointment_id"])) for x in r]
    assert keys == sorted(keys)
    assert [x["appointment_id"] for x in r] == ["A", "B", "A", "B"]


def test_errors_and_logs(caplog):
    caplog.set_level(logging.DEBUG)
    try:
        plan_reminders([], datetime(2026, 1, 1))
        assert False
    except ValueError as e:
        assert EMAIL not in str(e)
    bad = [_appt(id="X", starts_at=datetime(2026, 10, 20, 9)),
           {"email": EMAIL}, _appt(id="N", phone="", email="", optout_sms_v2=True),
           _appt(id="C", status="cancelled"), _appt(id="OK")]
    r = plan_reminders(bad, NOW)
    assert {x["appointment_id"] for x in r} == {"OK"}
    assert EMAIL not in caplog.text and "Pádraig" not in caplog.text
    assert "id=X" in caplog.text
    assert any("appointment_id=OK" in m for m in caplog.messages)