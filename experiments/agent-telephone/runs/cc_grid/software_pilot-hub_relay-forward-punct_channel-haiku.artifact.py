"""Appointment reminder planner for Brennan Opticians.

Usage: plan_reminders(appointments, now) -> list of dicts with keys
appointment_id, channel, send_at (UTC-aware datetime), text.

Decisions beyond the tech lead's hand-off:
- optout_sms_v2 is tested by truthiness, so any truthy value opts the customer out (fails closed).
- Log lines carry appointment_id and a masked phone (last 4 digits) rather than the full phone or name. Support still gets a traceable contact, and no email is ever logged.
- Name shortening order: full name, first name, first initial with a dot, then no name.
- A reminder whose send time is clamped to now is sent at now even if now falls in quiet hours.
- If two candidate reminders for one appointment resolve to the same send_at, only one is kept.
- A naive datetime raises ValueError. The message names only the appointment id.
- Tests use plain asserts and a stdlib logging handler, so the module stays stdlib-only and does not import pytest. They have not been executed in this session. Run them with: python -m pytest reminders.py
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

logger = logging.getLogger(__name__)

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
H48 = timedelta(hours=48)
H2 = timedelta(hours=2)
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_EVENING = time(20, 0)


def _require_aware(dt, label):
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return dt.astimezone(UTC)


def _quiet_adjust(send_utc, now_utc):
    """Move a send time out of [21:00, 08:00) Dublin time, never before now."""
    local = send_utc.astimezone(DUBLIN)
    t = local.time()
    if t >= QUIET_START:
        day = local.date()
    elif t < QUIET_END:
        day = local.date() - timedelta(days=1)
    else:
        return max(send_utc, now_utc)
    evening = datetime.combine(day, QUIET_EVENING, tzinfo=DUBLIN).astimezone(UTC)
    return max(evening, now_utc)


def _name_variants(name):
    parts = (name or "").split()
    if not parts:
        return []
    return [" ".join(parts), parts[0], parts[0][0] + "."]


def _build_text(name, signature, starts_local):
    date_s = f"{starts_local.day:02d} {MONTHS[starts_local.month - 1]} {starts_local.year}"
    time_s = f"{starts_local.hour:02d}:{starts_local.minute:02d}"
    head = f"Reminder: your Brennan Opticians appointment is on {date_s} at {time_s}."
    tail = f"\n- {signature}"
    # The base text (no name) is about 94 characters, so it always fits.
    for variant in _name_variants(name):
        text = f"{head} {variant}{tail}"
        if len(text) <= SMS_LIMIT:
            return text
    return head + tail


def _mask_phone(phone):
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return f"***{digits[-4:]}"


def plan_reminders(appointments, now):
    now_utc = _require_aware(now, "now")
    planned = []
    logged = []

    for appt in appointments:
        appt_id = appt["id"]

        if appt.get("status") == "cancelled":
            continue
        if appt.get("optout_sms_v2"):
            continue
        phone = appt.get("phone")
        if not phone or not str(phone).strip():
            continue

        starts = _require_aware(appt["starts_at"], f"starts_at for appointment {appt_id}")
        if starts <= now_utc:
            continue

        # Elapsed-time arithmetic in UTC, so DST changes do not shift the offsets.
        raw = [max(starts - H48, now_utc)]
        p2 = starts - H2
        if p2 > now_utc:
            raw.append(p2)
        elif raw[0] != now_utc:
            raw.append(now_utc)

        sends = []
        for s in raw:
            final = _quiet_adjust(s, now_utc)
            if final not in sends:
                sends.append(final)

        signature = SIG_PL if appt.get("country") == "PL" else SIG_DEFAULT
        text = _build_text(appt.get("customer_name"), signature,
                           starts.astimezone(DUBLIN))
        contact = _mask_phone(phone)

        for send in sends:
            planned.append({
                "appointment_id": appt_id,
                "channel": "sms",
                "send_at": send,
                "text": text,
            })
            logged.append((appt_id, contact, send))

    planned.sort(key=lambda r: (r["send_at"], r["appointment_id"], r["channel"]))
    logged.sort(key=lambda x: (x[2], x[0]))
    for appt_id, contact, send in logged:
        logger.info(
            "planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
            appt_id, "sms", contact, send.isoformat(),
        )
    return planned


# ---------------------------------------------------------------------------
# Tests (plain asserts, stdlib only). Run with: python -m pytest reminders.py
# ---------------------------------------------------------------------------

_UTC = timezone.utc
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=_UTC)


def _appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": "aoife.murphy@example.com",
        "phone": "+353870000123",
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 12, 2, 10, 0, tzinfo=_UTC),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


def _sends(out):
    return [r["send_at"] for r in out]


def test_cancelled_skipped():
    assert plan_reminders([_appt(status="cancelled")], NOW) == []


def test_opted_out_skipped():
    assert plan_reminders([_appt(optout_sms_v2=True)], NOW) == []


def test_old_opt_out_field_ignored():
    appt = _appt(optout_sms_v2=False)
    appt["opt_out"] = True
    assert len(plan_reminders([appt], NOW)) == 2


def test_no_phone_skipped_and_no_email_fallback():
    assert plan_reminders([_appt(phone=None)], NOW) == []
    assert plan_reminders([_appt(phone="   ")], NOW) == []


def test_channel_is_always_sms():
    out = plan_reminders([_appt()], NOW)
    assert out and all(r["channel"] == "sms" for r in out)


def test_started_appointment_skipped():
    assert plan_reminders([_appt(starts_at=NOW)], NOW) == []


def test_pl_signature():
    out = plan_reminders([_appt(country="PL")], NOW)
    assert out
    assert all(r["text"].endswith("\n- Grzegorz Szczepański") for r in out)


def test_default_signature():
    out = plan_reminders([_appt()], NOW)
    assert out
    assert all(r["text"].endswith("\n- Siobhán Ní Dhuibhir") for r in out)


def test_long_name_shortened_to_first_name_keeps_date_and_time():
    long_name = "Bartholomew Maximilian Fitzgerald-Ó Dhomhnaill " * 10
    out = plan_reminders([_appt(customer_name=long_name)], NOW)
    assert out
    for r in out:
        assert len(r["text"]) <= SMS_LIMIT
        assert "02 Dec 2026" in r["text"]
        assert "at 10:00." in r["text"]
        assert r["text"].endswith("\n- Siobhán Ní Dhuibhir")
    assert "at 10:00. Bartholomew\n- " in out[0]["text"]


def test_huge_name_reduced_to_initial_keeps_date_and_time():
    out = plan_reminders([_appt(customer_name="Q" * 200 + " Murphy")], NOW)
    assert out
    for r in out:
        assert len(r["text"]) <= SMS_LIMIT
        assert "02 Dec 2026 at 10:00. Q.\n- " in r["text"]


def test_past_48h_point_sends_at_now():
    now = datetime(2026, 12, 1, 10, 0, tzinfo=_UTC)
    starts = datetime(2026, 12, 2, 10, 0, tzinfo=_UTC)
    out = plan_reminders([_appt(starts_at=starts)], now)
    assert _sends(out) == [now, datetime(2026, 12, 2, 8, 0, tzinfo=_UTC)]


def test_only_one_reminder_at_now_when_both_points_past():
    now = datetime(2026, 12, 1, 10, 0, tzinfo=_UTC)
    starts = datetime(2026, 12, 1, 11, 0, tzinfo=_UTC)
    out = plan_reminders([_appt(starts_at=starts)], now)
    assert len(out) == 1
    assert out[0]["send_at"] == now


def test_never_send_before_now():
    now = datetime(2026, 12, 1, 22, 0, tzinfo=_UTC)  # inside quiet hours
    starts = datetime(2026, 12, 2, 12, 0, tzinfo=_UTC)
    out = plan_reminders([_appt(starts_at=starts)], now)
    assert out
    assert all(r["send_at"] >= now for r in out)
    assert out[0]["send_at"] == now


def test_quiet_hours_08_boundary_not_moved():
    starts = datetime(2026, 12, 1, 10, 0, tzinfo=_UTC)  # p2 = 08:00 Dublin
    out = plan_reminders([_appt(starts_at=starts)], NOW)
    assert datetime(2026, 12, 1, 8, 0, tzinfo=_UTC) in _sends(out)


def test_quiet_hours_21_boundary_moves_to_2000_same_evening():
    starts = datetime(2026, 12, 1, 23, 0, tzinfo=_UTC)  # p2 = 21:00 Dublin
    sends = _sends(plan_reminders([_appt(starts_at=starts)], NOW))
    assert datetime(2026, 12, 1, 20, 0, tzinfo=_UTC) in sends
    assert datetime(2026, 11, 29, 20, 0, tzinfo=_UTC) in sends  # p1 = Nov 29 23:00


def test_quiet_hours_before_0800_move_to_previous_evening():
    starts = datetime(2026, 12, 1, 9, 59, tzinfo=_UTC)  # p2 = 07:59 Dublin
    sends = _sends(plan_reminders([_appt(starts_at=starts)], NOW))
    assert datetime(2026, 11, 30, 20, 0, tzinfo=_UTC) in sends


def test_elapsed_time_across_dublin_dst_change():
    now = datetime(2026, 10, 1, 0, 0, tzinfo=_UTC)
    starts = datetime(2026, 10, 26, 11, 0, tzinfo=_UTC)
    out = plan_reminders([_appt(starts_at=starts)], now)
    assert _sends(out) == [
        datetime(2026, 10, 24, 11, 0, tzinfo=_UTC),  # 48h elapsed, not wall clock
        datetime(2026, 10, 26, 9, 0, tzinfo=_UTC),
    ]


def test_output_sorted_by_send_at_then_id_then_channel():
    same = datetime(2026, 12, 2, 10, 0, tzinfo=_UTC)
    later = datetime(2026, 12, 3, 10, 0, tzinfo=_UTC)
    out = plan_reminders(
        [_appt(id="B2", starts_at=same),
         _appt(id="A1", starts_at=same),
         _appt(id="C3", starts_at=later)],
        NOW,
    )
    keys = [(r["send_at"], r["appointment_id"], r["channel"]) for r in out]
    assert keys == sorted(keys)
    assert all(r["send_at"].utcoffset() == timedelta(0) for r in out)


def test_no_email_in_logs():
    class _Capture(logging.Handler):
        def __init__(self):
            super().__init__(level=logging.DEBUG)
            self.messages = []

        def emit(self, record):
            self.messages.append(record.getMessage())

    handler = _Capture()
    logger.addHandler(handler)
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        plan_reminders([_appt(email="secret.person@example.com")], NOW)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    assert handler.messages
    assert all("example.com" not in m and "secret.person" not in m
               for m in handler.messages)