"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now). Pure: no I/O, no mutation.

ASSUMPTION (opt-out semantics, needs client confirmation): the brief says
"text them if optout_sms_v2 is true", but the field name suggests True means
the customer has opted OUT. Default here: True means opted out, so SMS is sent
only when the phone is non-blank and optout_sms_v2 is exactly False. A missing
or None flag counts as opted out. To flip the meaning, change
OPTOUT_TRUE_MEANS_OPTED_OUT (used only in _sms_allowed). A missing or None
flag never sends, whichever way it is set.

Other notes:
- The legacy opt_out field is ignored.
- The email channel is off by default (EMAIL_CHANNEL_ENABLED) and is not
  implemented: the email field is never read, and email is never a fallback.
- Logging carries only the appointment id, the channel and a reason code. The
  phone number is deliberately not logged, because the no-PII rule is stricter
  than the usual delivery-trace line.
- Day of month is not zero padded ("5 Oct 2026").
"""
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Dublin")
EMAIL_CHANNEL_ENABLED = False
OPTOUT_TRUE_MEANS_OPTED_OUT = True  # flip here if the CRM means the opposite
SMS_MAX = 160
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"


def _sms_allowed(appt):
    """Single place deciding SMS eligibility (phone present and not opted out)."""
    phone = appt.get("phone")
    if not isinstance(phone, str) or not phone.strip():
        return False
    flag = appt.get("optout_sms_v2")
    if not isinstance(flag, bool):
        return False  # missing/None counts as opted out
    return flag is (not OPTOUT_TRUE_MEANS_OPTED_OUT)


def _require_aware(dt, label):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {label}")


def _in_quiet(dt):
    h = dt.astimezone(TZ).hour
    return h >= 21 or h < 8


def _quiet_shift(dt):
    local = dt.astimezone(TZ)
    if local.hour >= 21:
        day = local.date()
    elif local.hour < 8:
        day = local.date() - timedelta(days=1)
    else:
        return dt
    return datetime.combine(day, time(20), tzinfo=TZ)


def _next_open(dt):
    local = dt.astimezone(TZ)
    day = local.date() + timedelta(days=1 if local.hour >= 21 else 0)
    return datetime.combine(day, time(8), tzinfo=TZ)


def _build_text(name, country, start):
    local = start.astimezone(TZ)
    date = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    hhmm = local.strftime("%H:%M")
    is_pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = SIG_PL if is_pl else SIG_DEFAULT
    parts = " ".join(name.split()) if isinstance(name, str) else ""
    tokens = parts.split()
    options = []
    if tokens:
        options.append(parts)
        if len(tokens) > 1:
            options.append(f"{tokens[0]} {tokens[-1][0]}.")
        options.append(tokens[0])
    options.append("")
    text = ""
    for opt in options:
        greeting = f"Hi {opt}," if opt else "Hi,"
        text = (f"{greeting} reminder: your Brennan Opticians appointment "
                f"is on {date} at {hhmm}. {sig}")
        if len(text) <= SMS_MAX:
            break
    return text


def _plan_one(appt, now):
    if not isinstance(appt, dict):
        logger.warning("skipped appointment id=- reason=INVALID")
        return []
    aid = appt.get("id")
    start = appt.get("starts_at")
    if (aid is None or (isinstance(aid, str) and not aid.strip())
            or not isinstance(start, datetime)):
        logger.warning("skipped appointment id=%s reason=INVALID",
                       aid if aid not in (None, "") else "-")
        return []
    _require_aware(start, "starts_at")
    status = appt.get("status")
    if isinstance(status, str) and status.strip().casefold() == "cancelled":
        return []
    if start <= now or not _sms_allowed(appt):
        return []

    text = _build_text(appt.get("customer_name"), appt.get("country"), start)
    start_utc = start.astimezone(timezone.utc)
    planned = []
    for code, hours in (("48H", 48), ("2H", 2)):
        raw = start_utc - timedelta(hours=hours)
        if code == "2H" and raw < now:
            continue
        send = _quiet_shift(raw)
        if send < now:
            send = now
            if _in_quiet(send):
                send = _next_open(send)
                if send >= start:
                    continue
        if any(send == s for s, _ in planned):
            continue
        planned.append((send, code))

    out = []
    for send, code in planned:
        logger.info("reminder planned appointment_id=%s channel=sms reason=%s",
                    aid, code)
        out.append({"appointment_id": aid, "channel": "sms",
                    "send_at": send.astimezone(TZ), "text": text})
    return out


def plan_reminders(appointments, now):
    """Return reminder dicts sorted by send_at (stable). See module docstring."""
    _require_aware(now, "now")
    out = []
    for appt in appointments:
        out.extend(_plan_one(appt, now))
    out.sort(key=lambda r: r["send_at"])
    return out


# ----------------------------- tests (pytest) -----------------------------
EMAIL = "secret.person@example.com"


def _u(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def _appt(**kw):
    base = {"id": "a1", "customer_name": "Mary Murphy", "email": EMAIL,
            "phone": "+353871234567", "country": "IE", "status": "booked",
            "starts_at": _u(2026, 1, 20, 12), "optout_sms_v2": False}
    base.update(kw)
    return base


def _sends(res):
    return [r["send_at"] for r in res]


def test_thirty_hour_case():
    now = _u(2026, 6, 1, 9)
    start = now + timedelta(hours=30)
    res = plan_reminders([_appt(starts_at=start)], now)
    assert _sends(res) == [now, start - timedelta(hours=2)]
    assert res[0]["send_at"].tzinfo is not None
    assert set(res[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert "2 Jun 2026 at 16:00." in res[0]["text"]


def test_dst_spring_forward_uses_elapsed_time():
    start = datetime(2026, 3, 30, 10, tzinfo=TZ)  # BST, 09:00 UTC
    res = plan_reminders([_appt(starts_at=start)], _u(2026, 3, 1))
    assert _sends(res) == [_u(2026, 3, 28, 9), _u(2026, 3, 30, 7)]


def test_dst_fall_back_uses_elapsed_time():
    start = datetime(2026, 10, 26, 10, tzinfo=TZ)  # GMT, 10:00 UTC
    res = plan_reminders([_appt(starts_at=start)], _u(2026, 10, 1))
    assert _sends(res) == [_u(2026, 10, 24, 10), _u(2026, 10, 26, 8)]


def test_quiet_window_21_moved_08_not():
    now = _u(2026, 1, 1)
    res = plan_reminders([_appt(starts_at=_u(2026, 1, 20, 23))], now)
    assert _sends(res) == [_u(2026, 1, 18, 20), _u(2026, 1, 20, 20)]
    res = plan_reminders([_appt(starts_at=_u(2026, 1, 20, 10))], now)
    assert _sends(res) == [_u(2026, 1, 18, 10), _u(2026, 1, 20, 8)]
    res = plan_reminders([_appt(starts_at=_u(2026, 1, 20, 9, 59))], now)
    assert _sends(res)[1] == _u(2026, 1, 19, 20)


def test_clamp_to_now_and_dedup():
    now = _u(2026, 1, 20, 20, 30)
    res = plan_reminders([_appt(starts_at=_u(2026, 1, 20, 23))], now)
    assert _sends(res) == [now]


def test_clamped_now_in_quiet_window():
    now = _u(2026, 1, 20, 22)
    res = plan_reminders([_appt(starts_at=_u(2026, 1, 21, 12))], now)
    assert _sends(res) == [_u(2026, 1, 21, 8), _u(2026, 1, 21, 10)]
    assert plan_reminders([_appt(starts_at=_u(2026, 1, 21, 7))], now) == []


def test_pl_signature_and_default():
    now = _u(2026, 1, 1)
    pl = plan_reminders([_appt(country=" pl ")], now)
    assert pl[0]["text"].endswith("Grzegorz Szczepański")
    ie = plan_reminders([_appt()], now)
    assert ie[0]["text"].endswith("Siobhán Ní Dhuibhir")


def test_long_name_truncation():
    now = _u(2026, 1, 1)
    r = plan_reminders([_appt(customer_name="Maximilian " + "Z" * 150)], now)
    assert r[0]["text"].startswith("Hi Maximilian Z.,")
    r = plan_reminders([_appt(customer_name="F" * 200 + " Last")], now)[0]
    assert r["text"].startswith("Hi, reminder")
    for name in (None, "   ", "F" * 300):
        t = plan_reminders([_appt(customer_name=name)], now)[0]["text"]
        assert len(t) <= SMS_MAX and "20 Jan 2026 at 12:00." in t
        assert t.endswith(SIG_DEFAULT)


def test_sorting_and_stable_ties():
    now = _u(2026, 1, 1)
    a = [_appt(id="late", starts_at=_u(2026, 1, 25, 12)),
         _appt(id="b"), _appt(id="a")]
    res = plan_reminders(a, now)
    assert _sends(res) == sorted(_sends(res))
    assert [r["appointment_id"] for r in res] == [
        "b", "a", "late", "b", "a", "late"]


def test_skips_and_no_mutation():
    import copy
    now = _u(2026, 1, 1)
    items = [_appt(status=" Cancelled "), _appt(optout_sms_v2=True),
             _appt(optout_sms_v2=None), _appt(phone="  "),
             _appt(starts_at=now), _appt(opt_out=True, id="ok")]
    items[2].pop("optout_sms_v2")
    before = copy.deepcopy(items)
    res = plan_reminders(items, now)
    assert {r["appointment_id"] for r in res} == {"ok"}
    assert items == before


def test_naive_raises_and_no_pii_in_logs(caplog):
    import pytest
    caplog.set_level(logging.DEBUG)
    now = _u(2026, 1, 1)
    items = [_appt(id=None), _appt(starts_at=None), _appt()]
    res = plan_reminders(items, now)
    assert len(res) == 2
    assert EMAIL not in caplog.text
    with pytest.raises(ValueError) as e:
        plan_reminders([_appt(starts_at=datetime(2026, 2, 1, 10))], now)
    assert EMAIL not in str(e.value)
    with pytest.raises(ValueError) as e:
        plan_reminders([_appt()], datetime(2026, 1, 1))
    assert EMAIL not in str(e.value) and EMAIL not in caplog.text