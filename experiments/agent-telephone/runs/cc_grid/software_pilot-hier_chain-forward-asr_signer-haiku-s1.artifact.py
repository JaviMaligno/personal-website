"""Appointment reminder planner for Brennan Opticians.

Test status: the accompanying test file was written but not executed in this session.

Open questions, each implemented as the stated default:
1. Missing or None optout_sms_v2 counts as opted out (_is_opted_out).
2. If the 2h slot has already passed while the appointment is still in the future, the 2h reminder is skipped (plan_reminders).
3. If a quiet-hours shift lands before now, the reminder is dropped (plan_reminders).
4. SMS length is measured with len() on the str (SMS_LIMIT).
5. Truncation marker is "..." and date format is "<day> <Mon> <year>" with unpadded day, e.g. "3 Oct 2026" (ELLIPSIS, _format_date). The brief's example "13 Oct 2026" is consistent with this.
6. If the name is removed entirely and the SMS is still over the limit, the SMS is skipped with no email fallback (_build_text).
7. Naive starts_at or now raises ValueError (_check_aware).
8. send_at is returned in UTC (UTC).

Conflicts with the house logging rule and the brief:
- The house rule asks for the contact in each INFO line. The brief and the DPC audit forbid logging email, name or phone. Only appointment_id and channel are logged.
- Product has not supplied template wording. The default template is kept in TEMPLATE.
- A missing or blank customer_name renders as "there". This is not specified in the brief.
- The legacy SMS folder was not read or ported.
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
ELLIPSIS = "..."
TEMPLATE = "Hi {name}, your Brennan Opticians appointment is on {date} at {time}. {signature}"
SIGNATURE_DEFAULT = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SLOT_48H = timedelta(hours=48)
SLOT_2H = timedelta(hours=2)
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
QUIET_SHIFT_HOUR = 20


def _usable(value):
    return isinstance(value, str) and value.strip() != ""


def _is_opted_out(appt):
    # Open question 1: anything other than exactly False counts as opted out.
    return appt.get("optout_sms_v2") is not False


def _channel(appt):
    if _usable(appt.get("phone")) and not _is_opted_out(appt):
        return "sms"
    if _usable(appt.get("email")):
        return "email"
    return None


def _is_cancelled(appt):
    status = appt.get("status")
    return isinstance(status, str) and status.strip().casefold() == "cancelled"


def _signature(appt):
    country = appt.get("country")
    if isinstance(country, str) and country.strip().casefold() == "pl":
        return SIGNATURE_PL
    return SIGNATURE_DEFAULT


def _check_aware(value, field):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")


def _quiet_shift(send_utc):
    local = send_utc.astimezone(DUBLIN)
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    elif local.hour < QUIET_END_HOUR:
        day = local.date() - timedelta(days=1)
    else:
        return send_utc
    shifted = datetime(day.year, day.month, day.day, QUIET_SHIFT_HOUR, 0, tzinfo=DUBLIN)
    return shifted.astimezone(UTC)


def _format_date(local):
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}"


def _build_text(appt, starts_local, sms):
    name = appt.get("customer_name")
    name = name.strip() if isinstance(name, str) else ""
    name = name or "there"
    fields = {
        "date": _format_date(starts_local),
        "time": f"{starts_local.hour:02d}:{starts_local.minute:02d}",
        "signature": _signature(appt),
    }
    text = TEMPLATE.format(name=name, **fields)
    if not sms or len(text) <= SMS_LIMIT:
        return text
    empty_len = len(TEMPLATE.format(name="", **fields))
    room = SMS_LIMIT - empty_len - len(ELLIPSIS)
    short = name[:room].rstrip() if room > 0 else ""
    if not short:
        return None
    return TEMPLATE.format(name=short + ELLIPSIS, **fields)


def plan_reminders(appointments, now):
    """Return reminder dicts sorted by send_at, then appointment_id, then channel.

    Inputs are not mutated. Raises ValueError for naive datetimes.
    """
    _check_aware(now, "now")
    planned = []
    for appt in appointments:
        appt_id = appt.get("id")
        starts = appt.get("starts_at")
        _check_aware(starts, "starts_at")

        if _is_cancelled(appt):
            log.info("skip id=%s rule=cancelled", appt_id)
            continue
        if starts <= now:
            log.info("skip id=%s rule=past", appt_id)
            continue
        channel = _channel(appt)
        if channel is None:
            log.info("skip id=%s rule=no_usable_channel", appt_id)
            continue

        slots = [("48h", starts - SLOT_48H)]
        if starts - SLOT_2H < now:
            log.info("skip id=%s slot=2h rule=2h_slot_passed", appt_id)
        else:
            slots.append(("2h", starts - SLOT_2H))

        starts_local = starts.astimezone(DUBLIN)
        for slot, candidate in slots:
            send_at = max(candidate, now).astimezone(UTC)
            send_at = _quiet_shift(send_at)
            if send_at < now:
                log.info("drop id=%s slot=%s rule=quiet_shift_before_now", appt_id, slot)
                continue
            text = _build_text(appt, starts_local, channel == "sms")
            if text is None:
                log.info("skip id=%s slot=%s rule=sms_too_long_name_removed", appt_id, slot)
                continue
            planned.append({
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            log.info("planned id=%s channel=%s", appt_id, channel)

    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    log.info("reminders planned=%d", len(planned))
    return planned


# ===== test_brennan_reminders.py =====

import copy
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

import brennan_reminders as br

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
NAME = "Pádraig Murphy"
EMAIL = "pat@example.com"
PHONE = "+353851234567"


def appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": NAME,
        "email": EMAIL,
        "phone": PHONE,
        "country": "IE",
        "status": "booked",
        "starts_at": NOW + timedelta(days=5),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


def times(out):
    return [r["send_at"] for r in out]


def test_empty_input():
    assert br.plan_reminders([], NOW) == []


def test_naive_now_raises():
    with pytest.raises(ValueError):
        br.plan_reminders([], datetime(2026, 10, 13, 12))


def test_naive_starts_raises_without_echoing_contact():
    with pytest.raises(ValueError) as exc:
        br.plan_reminders([appt(starts_at=datetime(2026, 10, 20, 12))], NOW)
    assert EMAIL not in str(exc.value)
    assert PHONE not in str(exc.value)


@pytest.mark.parametrize("phone", [None, "", "   "])
def test_unusable_phone_uses_email(phone):
    out = br.plan_reminders([appt(phone=phone)], NOW)
    assert len(out) == 2
    assert all(r["channel"] == "email" for r in out)


def test_missing_phone_key_uses_email():
    a = appt()
    del a["phone"]
    out = br.plan_reminders([a], NOW)
    assert out and all(r["channel"] == "email" for r in out)


def test_missing_email_with_usable_phone_uses_sms():
    out = br.plan_reminders([appt(email=None)], NOW)
    assert out and all(r["channel"] == "sms" for r in out)


def test_both_unusable_no_reminder():
    assert br.plan_reminders([appt(phone=" ", email="")], NOW) == []


def test_optout_true_with_email_goes_email():
    out = br.plan_reminders([appt(optout_sms_v2=True)], NOW)
    assert out and all(r["channel"] == "email" for r in out)


def test_optout_true_no_email_no_reminder():
    assert br.plan_reminders([appt(optout_sms_v2=True, email=None)], NOW) == []


@pytest.mark.parametrize("value", ["absent", None])
def test_optout_absent_or_none_is_opted_out(value):
    a = appt()
    if value == "absent":
        del a["optout_sms_v2"]
    else:
        a["optout_sms_v2"] = None
    out = br.plan_reminders([a], NOW)
    assert out and all(r["channel"] == "email" for r in out)


@pytest.mark.parametrize("status", ["cancelled", "Cancelled", " cancelled "])
def test_cancelled_variants_excluded(status):
    assert br.plan_reminders([appt(status=status)], NOW) == []


def test_past_appointment_no_reminders():
    assert br.plan_reminders([appt(starts_at=NOW - timedelta(hours=1))], NOW) == []
    assert br.plan_reminders([appt(starts_at=NOW)], NOW) == []


def test_within_two_hours_only_48h_at_now():
    out = br.plan_reminders([appt(starts_at=NOW + timedelta(hours=1))], NOW)
    assert times(out) == [NOW]


def test_between_2h_and_48h():
    out = br.plan_reminders([appt(starts_at=NOW + timedelta(hours=6))], NOW)
    assert times(out) == [NOW, NOW + timedelta(hours=4)]


def test_more_than_48h_exact_times():
    starts = datetime(2026, 10, 20, 12, 0, tzinfo=DUBLIN)
    out = br.plan_reminders([appt(starts_at=starts)], NOW)
    assert times(out) == [
        datetime(2026, 10, 18, 11, 0, tzinfo=UTC),
        datetime(2026, 10, 20, 9, 0, tzinfo=UTC),
    ]


def test_quiet_21_shifts_to_2000_same_day():
    starts = datetime(2026, 10, 14, 22, 0, tzinfo=UTC)  # 23:00 IST, 2h slot 21:00 IST
    out = br.plan_reminders([appt(starts_at=starts)], NOW)
    assert times(out) == [NOW, datetime(2026, 10, 14, 19, 0, tzinfo=UTC)]


def test_quiet_2059_stays():
    starts = datetime(2026, 10, 14, 21, 59, tzinfo=UTC)  # 2h slot 20:59 IST
    out = br.plan_reminders([appt(starts_at=starts)], NOW)
    assert times(out)[-1] == datetime(2026, 10, 14, 19, 59, tzinfo=UTC)


def test_quiet_0759_shifts_to_2000_previous_day():
    starts = datetime(2026, 10, 14, 8, 59, tzinfo=UTC)  # 2h slot 07:59 IST
    out = br.plan_reminders([appt(starts_at=starts)], NOW)
    assert times(out) == [NOW, datetime(2026, 10, 13, 19, 0, tzinfo=UTC)]


def test_quiet_0800_stays():
    starts = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)  # 2h slot 08:00 IST
    out = br.plan_reminders([appt(starts_at=starts)], NOW)
    assert times(out)[-1] == datetime(2026, 10, 14, 7, 0, tzinfo=UTC)


def test_quiet_shift_before_now_dropped():
    now = datetime(2026, 10, 13, 20, 30, tzinfo=UTC)  # 21:30 IST
    starts = datetime(2026, 10, 14, 15, 0, tzinfo=DUBLIN)
    out = br.plan_reminders([appt(starts_at=starts)], now)
    assert times(out) == [datetime(2026, 10, 14, 12, 0, tzinfo=UTC)]


def test_dst_spring_absolute_48h():
    now = datetime(2026, 3, 27, 12, 0, tzinfo=UTC)
    starts = datetime(2026, 3, 30, 10, 0, tzinfo=DUBLIN)  # IST, 09:00 UTC
    out = br.plan_reminders([appt(starts_at=starts)], now)
    assert times(out) == [
        datetime(2026, 3, 28, 9, 0, tzinfo=UTC),
        datetime(2026, 3, 30, 7, 0, tzinfo=UTC),
    ]


def test_dst_fall_back_quiet_shifts_across_transition():
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    starts = datetime(2026, 10, 25, 2, 30, tzinfo=UTC)  # GMT after 01:00 UTC
    out = br.plan_reminders([appt(starts_at=starts)], now)
    assert times(out) == [
        datetime(2026, 10, 22, 19, 0, tzinfo=UTC),
        datetime(2026, 10, 24, 19, 0, tzinfo=UTC),
    ]


def test_non_utc_input_converted():
    starts = datetime(2026, 10, 20, 17, 0, tzinfo=timezone(timedelta(hours=5)))
    out = br.plan_reminders([appt(starts_at=starts)], NOW)
    assert times(out) == [
        datetime(2026, 10, 18, 12, 0, tzinfo=UTC),
        datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
    ]
    assert all("20 Oct 2026 at 13:00" in r["text"] for r in out)


@pytest.mark.parametrize("country, sig", [
    ("PL", "Grzegorz Szczepański"),
    (" pl ", "Grzegorz Szczepański"),
    ("IE", "Chevonne Nee Divver"),
    (None, "Chevonne Nee Divver"),
])
def test_signature_by_country(country, sig):
    out = br.plan_reminders([appt(country=country)], NOW)
    assert out and all(r["text"].endswith(sig) for r in out)


def test_sms_short_name_unchanged():
    out = br.plan_reminders([appt(customer_name="Pádraig")], NOW)
    assert out and all("Hi Pádraig, your" in r["text"] for r in out)


def test_sms_long_name_truncated_and_within_limit():
    out = br.plan_reminders([appt(customer_name="A" * 300)], NOW)
    assert out
    for r in out:
        assert r["channel"] == "sms"
        assert len(r["text"]) <= 160
        assert "..." in r["text"]
        assert r["text"].endswith(" Chevonne Nee Divver")
        assert "18 Oct 2026" in r["text"]
        assert "at 13:00" in r["text"]


def test_sms_name_gone_is_skipped_without_email_fallback(monkeypatch):
    monkeypatch.setattr(br, "TEMPLATE", "X" * 170 + " {name} {date} {time} {signature}")
    out = br.plan_reminders([appt(email=None)], NOW)
    assert out == []
    out = br.plan_reminders([appt()], NOW)
    assert out == []


def test_input_order_does_not_affect_output():
    a = appt(id="B")
    b = appt(id="A")
    assert br.plan_reminders([a, b], NOW) == br.plan_reminders([b, a], NOW)


def test_output_sorted_by_send_at():
    items = [appt(id=str(h), starts_at=NOW + timedelta(hours=h)) for h in (72, 6, 30, 200)]
    out = br.plan_reminders(items, NOW)
    assert times(out) == sorted(times(out))


def test_each_appointment_uses_one_channel():
    out = br.plan_reminders([appt(id="X")], NOW)
    assert len({r["channel"] for r in out}) == 1


def test_inputs_not_mutated():
    items = [appt(), appt(id="A2", optout_sms_v2=True)]
    snapshot = copy.deepcopy(items)
    br.plan_reminders(items, NOW)
    assert items == snapshot


@pytest.mark.parametrize("hours", [1, 3, 6, 12, 30, 47, 49, 72, 200])
def test_invariants_for_many_offsets(hours):
    out = br.plan_reminders(
        [appt(starts_at=NOW + timedelta(hours=hours), customer_name="X" * 200)], NOW
    )
    for r in out:
        assert r["send_at"] >= NOW
        assert r["send_at"].utcoffset() == timedelta(0)
        if r["channel"] == "sms":
            assert len(r["text"]) <= 160


def test_no_pii_in_logs(caplog):
    caplog.set_level(logging.DEBUG)
    items = [
        appt(id="A1"),
        appt(id="A2", status="cancelled"),
        appt(id="A3", starts_at=NOW - timedelta(hours=1)),
        appt(id="A4", phone=None, email=None),
    ]
    out = br.plan_reminders(items, NOW)
    assert out
    for pii in (NAME, EMAIL, PHONE):
        assert pii not in caplog.text
    assert "planned id=A1 channel=sms" in caplog.text


def test_no_pii_in_exception_messages():
    with pytest.raises(ValueError) as exc:
        br.plan_reminders([appt(starts_at=datetime(2026, 10, 20, 12))], NOW)
    for pii in (NAME, EMAIL, PHONE):
        assert pii not in str(exc.value)