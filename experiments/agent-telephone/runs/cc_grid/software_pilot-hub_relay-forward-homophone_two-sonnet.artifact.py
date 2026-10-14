"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now) -> list of dicts with exactly
appointment_id, channel ("sms" | "email"), send_at (tz-aware UTC), text.

STATELESS: the function keeps no record of what was already sent. The
immediate reminder (send_at == now) is therefore re-emitted on every run while
the appointment is still upcoming, and the CALLER MUST DE-DUPLICATE (for
example by keying on appointment_id plus reminder slot).

Rules implemented
- Reminders at 48h and 2h before starts_at (offsets are elapsed durations).
  Europe/Dublin is used only for the quiet window and for the text.
- 48h point already past: first reminder is sent at now. 2h point past: dropped.
  starts_at <= now: nothing. send_at is never < now and always < starts_at.
- Status "cancelled"/"canceled" (trimmed, case-insensitive): nothing.
- Channel: non-blank phone and optout_sms_v2 is not True -> sms, else email
  (if an email exists), else skipped. Legacy "opt_out" is ignored.
  Same channel for both reminders of an appointment.
- Quiet window 21:00 <= t < 08:00 Dublin: moved back to the preceding 20:00
  Dublin; if that is before now, moved forward to the next 08:00 Dublin; dropped
  if the result is not before starts_at. Applies to the "now" reminder too.
- Text has date DD/MM/YYYY and time HH:MM (Dublin) and ends with the signature
  (Grzegorz Szczepański for country PL, else Siobhán Ní Dhuibhir). SMS <= 160
  chars: only the name is shortened (full, first + last initial, first,
  first initial, omitted). Emails are never shortened.
- Logging: one INFO line per planned reminder with appointment_id, channel and
  a contact reference. The email address is NEVER logged (DPC audit); for email
  the contact is "email-on-file", for sms the phone is masked to its last 2
  digits. Malformed appointments are logged by list index and reason code only.

Defaults chosen by the PM / developer, NOT confirmed by the client
- "the second one too, hours before" is read as 2 hours.
- Quiet-window fallback (back to 20:00, else forward to 08:00, else drop).
- Date format DD/MM/YYYY and the wording of the message.
- Kraków branch (PL) customers still use Europe/Dublin times in the text and
  quiet window; no Europe/Warsaw conversion.
- Missing optout_sms_v2 flag is treated as not opted out.
- The signature contains non-GSM characters, so an SMS may be sent as UCS-2,
  where one segment holds only 70 characters; 160 is a character count only.
- De-duplication is the caller's responsibility (see above).

Tests are included below; run with: pytest <this_file>.py
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
SMS_LIMIT = 160


def _aware(value) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None


def _nonblank(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _shift_quiet(dt: datetime, now: datetime, starts: datetime):
    loc = dt.astimezone(DUBLIN)
    evening = loc.hour >= 21
    if not (evening or loc.hour < 8):
        return dt
    day = loc.date() if evening else loc.date() - timedelta(days=1)
    out = datetime.combine(day, time(20), tzinfo=DUBLIN).astimezone(UTC)
    if out < now:
        day = loc.date() + timedelta(days=1) if evening else loc.date()
        out = datetime.combine(day, time(8), tzinfo=DUBLIN).astimezone(UTC)
    return out if out < starts else None


def _name_ladder(name) -> list:
    parts = name.split() if isinstance(name, str) else []
    if not parts:
        return [None]
    first = parts[0]
    ladder = [" ".join(parts)]
    if len(parts) > 1:
        ladder.append(f"{first} {parts[-1][0]}.")
    ladder += [first, f"{first[0]}.", None]
    return list(dict.fromkeys(ladder))


def _build_text(name, date_s: str, time_s: str, sig: str, sms: bool) -> str:
    def make(n):
        greeting = f"Hello {n}," if n else "Hello,"
        return f"{greeting} your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"

    ladder = _name_ladder(name)
    if not sms:
        return make(ladder[0])
    for n in ladder:
        text = make(n)
        if len(text) <= SMS_LIMIT:
            return text
    return make(None)


def _mask_phone(phone: str) -> str:
    digits = [c for c in phone if c.isdigit()]
    return "***" + "".join(digits[-2:])


def _plan_one(appt: dict, now: datetime) -> list:
    appt_id = appt["id"]
    starts = appt["starts_at"]
    if not _aware(starts):
        raise ValueError("starts_at")
    status = appt.get("status")
    if status is not None and not isinstance(status, str):
        raise ValueError("status")
    if status and status.strip().lower() in ("cancelled", "canceled"):
        return []
    starts = starts.astimezone(UTC)
    if starts <= now:
        return []

    phone, email = appt.get("phone"), appt.get("email")
    if _nonblank(phone) and appt.get("optout_sms_v2") is not True:
        channel, contact = "sms", _mask_phone(phone)
    elif _nonblank(email):
        channel, contact = "email", "email-on-file"
    else:
        return []

    country = appt.get("country")
    is_pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = SIG_PL if is_pl else SIG_DEFAULT
    local = starts.astimezone(DUBLIN)
    text = _build_text(appt.get("customer_name"), local.strftime("%d/%m/%Y"),
                       local.strftime("%H:%M"), sig, channel == "sms")

    points = [max(starts - timedelta(hours=48), now)]
    t2 = starts - timedelta(hours=2)
    if t2 >= now:
        points.append(t2)

    out = []
    for p in points:
        send_at = _shift_quiet(p, now, starts)
        if send_at is None:
            continue
        out.append(({"appointment_id": appt_id, "channel": channel,
                     "send_at": send_at, "text": text}, contact))
    return out


def plan_reminders(appointments, now):
    """Return the reminders to send, sorted by send_at (stable).

    Stateless: the immediate reminder is re-emitted on every run, so the caller
    must de-duplicate. Raises ValueError if now is not a tz-aware datetime.
    Malformed appointments are skipped. Inputs are never mutated.
    """
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    planned = []
    for index, appt in enumerate(appointments):
        try:
            planned.extend(_plan_one(appt, now))
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            logger.warning("appointment skipped index=%d reason=malformed", index)
    planned.sort(key=lambda item: item[0]["send_at"])
    for rem, contact in planned:
        logger.info("reminder planned appointment_id=%s channel=%s contact=%s send_at=%s",
                    rem["appointment_id"], rem["channel"], contact,
                    rem["send_at"].isoformat())
    return [rem for rem, _ in planned]


# ----------------------------------------------------------------- tests ---
import copy  # noqa: E402

NOW = datetime(2026, 7, 1, 12, tzinfo=UTC)
EMAIL = "mary.obrien@example.com"


def dub(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def appt(**kw):
    base = {"id": "A1", "customer_name": "Mary O'Brien", "email": EMAIL,
            "phone": "+353871234567", "country": "IE", "status": "booked",
            "starts_at": dub(2026, 7, 15, 14), "optout_sms_v2": False}
    base.update(kw)
    return base


def sends(result):
    return [r["send_at"] for r in result]


def test_basic_bst_and_shape():
    res = plan_reminders([appt()], NOW)
    assert len(res) == 2
    assert all(set(r) == {"appointment_id", "channel", "send_at", "text"} for r in res)
    assert sends(res) == [datetime(2026, 7, 13, 13, tzinfo=UTC), datetime(2026, 7, 15, 11, tzinfo=UTC)]
    assert all(r["send_at"].utcoffset() == timedelta(0) for r in res)
    assert "15/07/2026" in res[0]["text"] and "14:00" in res[0]["text"]
    assert res[0]["text"].endswith(SIG_DEFAULT)


def test_gmt_text_time():
    res = plan_reminders([appt(starts_at=dub(2027, 1, 20, 10))], NOW)
    assert "10:00" in res[0]["text"] and "20/01/2027" in res[0]["text"]


def test_dst_change_25_oct_2026_uses_elapsed_hours():
    res = plan_reminders([appt(starts_at=dub(2026, 10, 26, 10))], NOW)
    assert sends(res)[0] == datetime(2026, 10, 24, 10, tzinfo=UTC)
    assert sends(res)[1] == datetime(2026, 10, 26, 8, tzinfo=UTC)
    assert "10:00" in res[0]["text"]


def test_immediate_and_dropped():
    now = dub(2026, 7, 14, 10)
    res = plan_reminders([appt()], now)
    assert sends(res)[0] == now.astimezone(UTC) and len(res) == 2
    res = plan_reminders([appt()], dub(2026, 7, 15, 13))
    assert len(res) == 1 and sends(res)[0] == dub(2026, 7, 15, 13).astimezone(UTC)
    assert plan_reminders([appt()], dub(2026, 7, 15, 14)) == []
    assert plan_reminders([appt()], dub(2026, 7, 16, 14)) == []


def test_cancelled_variants():
    for s in ("cancelled", " CANCELLED ", "Canceled"):
        assert plan_reminders([appt(status=s)], NOW) == []
    assert len(plan_reminders([appt(status="confirmed")], NOW)) == 2
    assert len(plan_reminders([appt(status=None)], NOW)) == 2


def test_quiet_window_moves_back():
    res = plan_reminders([appt(starts_at=dub(2026, 7, 15, 23))], NOW)
    assert sends(res) == [dub(2026, 7, 13, 20).astimezone(UTC), dub(2026, 7, 15, 20).astimezone(UTC)]


def test_quiet_window_boundaries():
    assert sends(plan_reminders([appt(starts_at=dub(2026, 7, 15, 22, 59))], NOW))[1] == dub(2026, 7, 15, 20, 59).astimezone(UTC)
    assert sends(plan_reminders([appt(starts_at=dub(2026, 7, 15, 10))], NOW))[1] == dub(2026, 7, 15, 8).astimezone(UTC)
    assert sends(plan_reminders([appt(starts_at=dub(2026, 7, 15, 9, 59))], NOW))[1] == dub(2026, 7, 14, 20).astimezone(UTC)


def test_quiet_window_forward_and_drop():
    now = dub(2026, 7, 15, 21, 30)
    res = plan_reminders([appt(starts_at=dub(2026, 7, 16, 9))], now)
    assert sends(res) == [dub(2026, 7, 16, 8).astimezone(UTC)] * 2
    assert plan_reminders([appt(starts_at=dub(2026, 7, 16, 7, 30))], now) == []


def test_channel_matrix():
    cases = [("+353871234567", False, EMAIL, "sms"), ("+353871234567", True, EMAIL, "email"),
             ("  ", False, EMAIL, "email"), (None, False, EMAIL, "email"),
             ("+353871234567", True, None, None), ("", False, " ", None),
             ("+353871234567", True, "", None), ("+353871234567", False, None, "sms")]
    for phone, opt, email, expected in cases:
        res = plan_reminders([appt(phone=phone, optout_sms_v2=opt, email=email)], NOW)
        if expected is None:
            assert res == []
        else:
            assert {r["channel"] for r in res} == {expected} and len(res) == 2


def test_missing_flag_and_legacy_field_ignored():
    a = appt()
    del a["optout_sms_v2"]
    assert plan_reminders([a], NOW)[0]["channel"] == "sms"
    assert plan_reminders([appt(opt_out=True)], NOW)[0]["channel"] == "sms"
    assert plan_reminders([appt(opt_out=False, optout_sms_v2=True)], NOW)[0]["channel"] == "email"


def test_sms_length_ladder():
    names = ["Bartholomew Montgomery-Featherstonehaugh Wolfeschlegelstein", "X" * 300, "Al", "", None]
    for country, sig in (("IE", SIG_DEFAULT), (" pl ", SIG_PL)):
        for n in names:
            for r in plan_reminders([appt(customer_name=n, country=country)], NOW):
                assert len(r["text"]) <= 160 and r["text"].endswith(sig)
                assert "15/07/2026" in r["text"] and "14:00" in r["text"]
    long = "Bartholomew Montgomery-Featherstonehaugh Wolfeschlegelstein"
    sms = plan_reminders([appt(customer_name=long)], NOW)[0]["text"]
    assert long not in sms and "Bartholomew" in sms
    em = plan_reminders([appt(customer_name="X" * 300, phone=None)], NOW)[0]
    assert em["channel"] == "email" and "X" * 300 in em["text"]


def test_blank_name_generic_greeting():
    assert plan_reminders([appt(customer_name="  ")], NOW)[0]["text"].startswith("Hello, ")


def test_signature_pl():
    res = plan_reminders([appt(country=" pl ")], NOW)
    assert all(r["text"].endswith(SIG_PL) for r in res)


def test_sorting_stable():
    a = appt(id="A", starts_at=dub(2026, 7, 20, 14))
    b = appt(id="B", starts_at=dub(2026, 7, 15, 14))
    res = plan_reminders([a, b], NOW)
    assert sends(res) == sorted(sends(res))
    assert [r["appointment_id"] for r in res][:2] == ["B", "A"]
    same = plan_reminders([appt(id="X"), appt(id="Y")], NOW)
    assert [r["appointment_id"] for r in same] == ["X", "Y", "X", "Y"]


def test_validation_and_malformed():
    import pytest
    for bad in (datetime(2026, 7, 1, 12), "2026-07-01", None):
        with pytest.raises(ValueError):
            plan_reminders([], bad)
    bads = [{}, "junk", {"id": "B", "starts_at": datetime(2026, 7, 15, 14)},
            appt(starts_at="soon"), appt(status=5)]
    res = plan_reminders(bads + [appt()], NOW)
    assert len(res) == 2


def test_no_mutation():
    data = [appt(), appt(id="B", status="cancelled")]
    snapshot = copy.deepcopy(data)
    plan_reminders(data, NOW)
    assert data == snapshot


def test_logging_has_no_email(caplog):
    with caplog.at_level(logging.DEBUG):
        res = plan_reminders([appt(), appt(id="B", phone=None), appt(id="C", starts_at="bad")], NOW)
    assert EMAIL not in caplog.text and "mary.obrien" not in caplog.text
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == len(res) == 4
    assert any("channel=email" in r.getMessage() and "appointment_id=B" in r.getMessage() for r in infos)
    assert any("channel=sms" in r.getMessage() for r in infos)
    assert "+353871234567" not in caplog.text