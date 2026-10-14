"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now). Pure function, stdlib only.
Pytest tests are included at the bottom of this module.

Assumptions for the client to confirm:
 1. Only the exact status "cancelled" (case-insensitive, trimmed) suppresses
    reminders. "canceled" (US spelling) and missing status count as active.
 2. optout_sms_v2 must be exactly False to allow SMS. Missing, None or any
    non-bool value is treated as opted out.
 3. A usable email is a non-empty string containing "@". No stronger validation.
 4. A phone is usable if it is a non-blank string. No format validation.
 5. When both the 48h and 2h points have passed, the single reminder at now
    stands in for the 2h reminder.
 6. A reminder moved out of quiet hours and then pushed forward to 08:00 may
    land after its nominal time, but always before starts_at.
 7. A naive starts_at raises ValueError (as does naive now). A starts_at that is
    not a datetime at all, or a missing/blank id, is "malformed" and is skipped.
 8. Missing customer_name is allowed; the greeting becomes "Hi,".
 9. Name shortening: full name, first name, initial ("J."), then no name.
10. The 160-character limit is applied to len() of the final text.
11. Log lines never contain the email. "Contact" is the masked phone (last 3
    digits) for SMS, or the literal "email-on-file" for email. The customer
    name is not logged.
12. send_at values are returned in UTC.
"""
import copy
import logging
from datetime import datetime, time, timedelta, timezone

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"


def _quiet_adjust(t, now, starts):
    """Apply quiet hours (21:00 <= local < 08:00). Return UTC datetime or None."""
    local = t.astimezone(TZ)
    h = local.hour
    if 8 <= h < 21:
        return t
    d = local.date()
    if h >= 21:
        back_d, fwd_d = d, d + timedelta(days=1)
    else:
        back_d, fwd_d = d - timedelta(days=1), d
    back = datetime.combine(back_d, time(20, 0), TZ).astimezone(UTC)
    if back >= now:
        return back
    fwd = datetime.combine(fwd_d, time(8, 0), TZ).astimezone(UTC)
    return fwd if fwd < starts else None


def _text(name, starts_local, signature, sms):
    when = (f"{starts_local.day} {_MONTHS[starts_local.month - 1]} "
            f"{starts_local.year} at {starts_local:%H:%M}")

    def build(n):
        greet = f"Hi {n}," if n else "Hi,"
        return (f"{greet} your Brennan Opticians appointment is on "
                f"{when}. {signature}")

    parts = name.split()
    variants = [name]
    if parts:
        variants += [parts[0], parts[0][0].upper() + "."]
    variants.append("")
    if not sms:
        return build(variants[0])
    for v in variants:
        text = build(v)
        if len(text) <= SMS_LIMIT:
            return text
    return build("")


def _usable_str(v):
    return isinstance(v, str) and v.strip() != ""


def _safe_id(a):
    try:
        i = a.get("id")
        return str(i) if isinstance(i, (str, int)) else "?"
    except Exception:
        return "?"


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    out = []
    for a in appointments or []:
        try:
            if not hasattr(a, "get"):
                raise TypeError
            aid = a.get("id")
            starts = a.get("starts_at")
            if isinstance(aid, bool) or not isinstance(aid, (str, int)) or aid == "":
                raise TypeError
            if not isinstance(starts, datetime):
                raise TypeError
        except Exception:
            logger.info("skipped malformed appointment id=%s", _safe_id(a) if hasattr(a, "get") else "?")
            continue
        if starts.tzinfo is None or starts.utcoffset() is None:
            raise ValueError("starts_at must be a timezone-aware datetime")
        status = a.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            continue
        starts = starts.astimezone(UTC)
        if starts <= now:
            continue

        phone = a.get("phone")
        email = a.get("email")
        if _usable_str(phone) and a.get("optout_sms_v2") is False:
            channel = "sms"
            digits = "".join(c for c in phone if c.isdigit())
            contact = "phone ***" + digits[-3:]
        elif _usable_str(email) and "@" in email:
            channel = "email"
            contact = "email-on-file"
        else:
            continue

        t48, t2 = starts - timedelta(hours=48), starts - timedelta(hours=2)
        if t48 >= now:
            points = [t48, t2]
        elif t2 >= now:
            points = [now, t2]
        else:
            points = [now]

        name = a.get("customer_name")
        name = " ".join(name.split()) if isinstance(name, str) else ""
        country = a.get("country")
        pl = isinstance(country, str) and country.strip().casefold() == "pl"
        text = _text(name, starts.astimezone(TZ), _SIG_PL if pl else _SIG_DEFAULT,
                     channel == "sms")

        for p in points:
            send_at = _quiet_adjust(p, now, starts)
            if send_at is None or send_at < now:
                continue
            logger.info("reminder planned appointment_id=%s channel=%s contact=%s send_at=%s",
                        aid, channel, contact, send_at.isoformat())
            out.append({"appointment_id": aid, "channel": channel,
                        "send_at": send_at, "text": text})
    out.sort(key=lambda r: r["send_at"])
    return out


# ----------------------------- tests (pytest) -----------------------------

def _u(*a):
    return datetime(*a, tzinfo=UTC)


def _appt(**kw):
    base = {"id": "A1", "customer_name": "Aoife Murphy", "email": "aoife@example.com",
            "phone": "+353851234567", "country": "IE", "status": "booked",
            "starts_at": _u(2026, 6, 10, 15), "optout_sms_v2": False}
    base.update(kw)
    return base


_FAR = _u(2020, 1, 1)


def test_two_reminders_normal():
    r = plan_reminders([_appt()], _u(2026, 6, 1))
    assert [x["send_at"] for x in r] == [_u(2026, 6, 8, 15), _u(2026, 6, 10, 13)]
    assert set(r[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert r[0]["channel"] == "sms"
    assert "10 Jun 2026 at 16:00" in r[0]["text"]
    assert r[0]["text"].endswith(_SIG_DEFAULT)


def test_quiet_edges_winter():
    s = _u(2030, 1, 1)
    assert _quiet_adjust(_u(2026, 1, 10, 20, 59), _FAR, s) == _u(2026, 1, 10, 20, 59)
    assert _quiet_adjust(_u(2026, 1, 10, 21, 0), _FAR, s) == _u(2026, 1, 10, 20, 0)
    assert _quiet_adjust(_u(2026, 1, 11, 7, 59), _FAR, s) == _u(2026, 1, 10, 20, 0)
    assert _quiet_adjust(_u(2026, 1, 11, 8, 0), _FAR, s) == _u(2026, 1, 11, 8, 0)


def test_quiet_edges_summer_and_dst():
    s = _u(2030, 1, 1)
    assert _quiet_adjust(_u(2026, 6, 10, 19, 59), _FAR, s) == _u(2026, 6, 10, 19, 59)
    assert _quiet_adjust(_u(2026, 6, 10, 20, 0), _FAR, s) == _u(2026, 6, 10, 19, 0)
    assert _quiet_adjust(_u(2026, 3, 29, 0, 30), _FAR, s) == _u(2026, 3, 28, 20, 0)
    assert _quiet_adjust(_u(2026, 3, 29, 1, 30), _FAR, s) == _u(2026, 3, 28, 20, 0)
    assert _quiet_adjust(_u(2026, 3, 29, 6, 59), _FAR, s) == _u(2026, 3, 28, 20, 0)
    assert _quiet_adjust(_u(2026, 3, 29, 7, 0), _FAR, s) == _u(2026, 3, 29, 7, 0)


def test_48h_is_absolute_across_dst():
    r = plan_reminders([_appt(starts_at=_u(2026, 3, 30, 12))], _u(2026, 3, 1))
    assert r[0]["send_at"] == _u(2026, 3, 28, 12)
    assert "at 13:00" in r[0]["text"]


def test_now_in_quiet_hours_pushed_forward():
    a = _appt(starts_at=_u(2026, 1, 11, 12))
    r = plan_reminders([a], _u(2026, 1, 10, 22))
    assert [x["send_at"] for x in r] == [_u(2026, 1, 11, 8), _u(2026, 1, 11, 10)]


def test_quiet_push_dropped_when_after_start():
    a = _appt(starts_at=_u(2026, 1, 11, 7))
    assert plan_reminders([a], _u(2026, 1, 10, 22)) == []


def test_both_passed_single_reminder():
    a = _appt(starts_at=_u(2026, 1, 12, 10))
    r = plan_reminders([a], _u(2026, 1, 12, 9))
    assert len(r) == 1 and r[0]["send_at"] == _u(2026, 1, 12, 9)


def test_started_or_past_nothing():
    assert plan_reminders([_appt()], _u(2026, 6, 10, 15)) == []


def test_channels():
    now = _u(2026, 6, 1)
    assert plan_reminders([_appt()], now)[0]["channel"] == "sms"
    assert plan_reminders([_appt(optout_sms_v2=True)], now)[0]["channel"] == "email"
    assert plan_reminders([_appt(phone=None)], now)[0]["channel"] == "email"
    a = _appt()
    del a["optout_sms_v2"]
    a["opt_out"] = False
    assert plan_reminders([a], now)[0]["channel"] == "email"
    assert plan_reminders([_appt(optout_sms_v2=None)], now)[0]["channel"] == "email"
    assert plan_reminders([_appt(optout_sms_v2=True, email="")], now) == []
    assert plan_reminders([_appt(phone="", email=None)], now) == []


def test_cancelled():
    assert plan_reminders([_appt(status=" CANCELLED ")], _u(2026, 6, 1)) == []


def test_pl_signature():
    r = plan_reminders([_appt(country=" pl ")], _u(2026, 6, 1))
    assert all(x["text"].endswith(_SIG_PL) for x in r)


def test_long_name_sms_shortening():
    now = _u(2026, 1, 1)
    base = {"starts_at": _u(2026, 1, 12, 10)}
    r = plan_reminders([_appt(customer_name="Maximilian " + "X" * 120, **base)], now)
    t = r[0]["text"]
    assert len(t) <= 160 and t.startswith("Hi Maximilian,") and "at 10:00" in t
    r = plan_reminders([_appt(customer_name="y" * 200, **base)], now)
    t = r[0]["text"]
    assert len(t) <= 160 and t.startswith("Hi Y.,") and t.endswith(_SIG_DEFAULT)
    r = plan_reminders([_appt(customer_name="A " + "B" * 200, optout_sms_v2=True, **base)], now)
    assert "B" * 200 in r[0]["text"]


def test_ordering_and_no_mutation():
    a = _appt(id="late", starts_at=_u(2026, 6, 10, 15))
    b = _appt(id="early", starts_at=_u(2026, 6, 9, 15))
    items = [a, b]
    snap = copy.deepcopy(items)
    r = plan_reminders(items, _u(2026, 6, 1))
    assert items == snap
    times = [x["send_at"] for x in r]
    assert times == sorted(times) and len(r) == 4
    assert plan_reminders([], _u(2026, 6, 1)) == []


def test_naive_and_malformed():
    import pytest
    with pytest.raises(ValueError):
        plan_reminders([], datetime(2026, 6, 1))
    with pytest.raises(ValueError):
        plan_reminders([_appt(starts_at=datetime(2026, 6, 10, 15))], _u(2026, 6, 1))
    r = plan_reminders([_appt(id="bad", starts_at="tomorrow"), _appt(id="ok")], _u(2026, 6, 1))
    assert {x["appointment_id"] for x in r} == {"ok"}


def test_log_has_one_line_per_reminder_and_no_email(caplog):
    caplog.set_level(logging.INFO, logger=__name__)
    a = _appt(optout_sms_v2=True, email="secret.person@example.com")
    r = plan_reminders([a, _appt(id="bad", starts_at=None)], _u(2026, 6, 1))
    planned = [x for x in caplog.records if "reminder planned" in x.getMessage()]
    assert len(planned) == len(r) == 2
    assert "secret.person" not in caplog.text and "@" not in caplog.text
    assert "channel=email" in planned[0].getMessage()