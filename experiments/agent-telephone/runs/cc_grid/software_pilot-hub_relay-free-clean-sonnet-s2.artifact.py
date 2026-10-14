# ===== FILE: reminders.py =====
"""Brennan Opticians appointment reminder planning.

Entry point: plan_reminders(appointments, now). Pure, standard library only.

Defaults chosen where the brief was silent:
- Date format is "14 Oct 2026" (day not zero-padded, English month names
  hard-coded); time is zero-padded 24h HH:MM, both in Europe/Dublin.
- Missing or None optout_sms_v2 means opted out, and so does any value other
  than False. SMS needs a non-blank phone and optout_sms_v2 is False.
- Quiet-hours fallback when the 20:00 shift is already past is the earliest
  allowed instant at or after now (now, else the next 08:00 Dublin).
- MIN_LEAD is zero. Reminders must be strictly before starts_at.
- All appointments are treated as Dublin time, even for country PL.
- The SMS name shrink goes full name, first name, first name truncated to the
  longest prefix that fits, no name.
- Ties in ordering compare str(appointment_id).

Operational notes:
- SMS text containing a, i, n with accents is sent as Unicode (70 chars per
  segment), so a 160-char message is billed as several segments.
- The function is stateless and reminders carry no recipient field or
  first/second marker. Callers must de-duplicate across repeated runs.
- House rule vs privacy: the INFO line per reminder records appointment id,
  channel and send time, but not the contact value itself, because the brief
  forbids logging emails, phones and names. Support can look the contact up
  by appointment id.
- The tests in test_reminders.py were written without the ability to execute
  them in this session, so they have not been run.
"""
from __future__ import annotations

import logging
import unicodedata
from collections.abc import Mapping
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

MIN_LEAD = timedelta(0)
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START_HOUR = 21  # >= is quiet
QUIET_END_HOUR = 8     # < is quiet
SHIFT_HOUR = 20
SMS_MAX_CHARS = 160

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIGNATURE_DEFAULT = unicodedata.normalize("NFC", "Siobhán Ní Dhuibhir")
SIGNATURE_PL = unicodedata.normalize("NFC", "Grzegorz Szczepański")


def _aware(value) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None


def _nonblank(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_quiet(instant: datetime) -> bool:
    hour = instant.astimezone(DUBLIN).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _local_to_utc(day, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=DUBLIN).astimezone(UTC)


def _earliest_allowed(now: datetime) -> datetime:
    if not _is_quiet(now):
        return now
    local = now.astimezone(DUBLIN)
    day = local.date() if local.hour < QUIET_END_HOUR else local.date() + timedelta(days=1)
    return _local_to_utc(day, QUIET_END_HOUR)


def _adjust_quiet(candidate: datetime, now: datetime) -> datetime:
    if not _is_quiet(candidate):
        return candidate
    local = candidate.astimezone(DUBLIN)
    day = local.date() if local.hour >= QUIET_START_HOUR else local.date() - timedelta(days=1)
    shifted = _local_to_utc(day, SHIFT_HOUR)
    if shifted < now:
        return _earliest_allowed(now)
    return shifted


def _clean_name(value) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFC", value)
    kept = []
    for ch in text:
        if ch.isspace():
            kept.append(" ")
        elif unicodedata.category(ch)[0] != "C":
            kept.append(ch)
    return unicodedata.normalize("NFC", " ".join("".join(kept).split()))


def _name_options(name: str):
    if not name:
        return
    yield name
    first = name.split(" ")[0]
    if first != name:
        yield first
    for k in range(len(first) - 1, 0, -1):
        yield first[:k]


def _build_text(name: str, local: datetime, signature: str, limit: int | None) -> str:
    date = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    tail = (f" a reminder of your appointment at Brennan Opticians on {date} "
            f"at {local.hour:02d}:{local.minute:02d}. {signature}")

    def make(n: str) -> str:
        head = f"Hi {n}," if n else "Hi,"
        return unicodedata.normalize("NFC", head + tail)

    if limit is None:
        return make(name)
    for option in _name_options(name):
        text = make(option)
        if len(text) <= limit:
            return text
    return make("")


def _validate(appt):
    """Return (id, start_utc) or None after logging a warning."""
    if not isinstance(appt, Mapping):
        log.warning("skipping malformed record reason=not_a_mapping")
        return None
    appt_id = appt.get("id")
    if appt_id is None or (isinstance(appt_id, str) and not appt_id.strip()):
        log.warning("skipping malformed record reason=missing_id")
        return None
    start = appt.get("starts_at")
    if start is None:
        log.warning("skipping malformed record id=%s reason=missing_starts_at", appt_id)
        return None
    if not _aware(start):
        reason = "naive_starts_at" if isinstance(start, datetime) else "invalid_starts_at"
        log.warning("skipping malformed record id=%s reason=%s", appt_id, reason)
        return None
    return appt_id, start.astimezone(UTC)


def _channel(appt) -> str | None:
    if _nonblank(appt.get("phone")) and appt.get("optout_sms_v2") is False:
        return "sms"
    if _nonblank(appt.get("email")):
        return "email"
    return None


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)

    planned = []  # (send_utc, str_id, kind, appt_id, channel, text)
    for appt in appointments:
        valid = _validate(appt)
        if valid is None:
            continue
        appt_id, start = valid

        status = appt.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            continue
        if start <= now_utc:
            continue

        channel = _channel(appt)
        if channel is None:
            log.warning("no reminders id=%s reason=no_contact", appt_id)
            continue

        country = appt.get("country")
        is_pl = isinstance(country, str) and country.strip().casefold() == "pl"
        signature = SIGNATURE_PL if is_pl else SIGNATURE_DEFAULT
        name = _clean_name(appt.get("customer_name"))
        limit = SMS_MAX_CHARS if channel == "sms" else None

        candidates = {}
        first = start - FIRST_OFFSET  # elapsed time: subtract in UTC
        if first < now_utc:
            first = now_utc
        candidates[0] = first
        second = start - SECOND_OFFSET
        if second >= now_utc:
            candidates[1] = second

        sends = {}
        for kind, cand in candidates.items():
            send = _adjust_quiet(cand, now_utc)
            if send + MIN_LEAD < start:
                sends[kind] = send
        if 0 in sends and 1 in sends and sends[0] == sends[1]:
            del sends[0]

        text = _build_text(name, start.astimezone(DUBLIN), signature, limit)
        for kind, send in sends.items():
            planned.append((send, str(appt_id), kind, appt_id, channel, text))

    planned.sort(key=lambda p: (p[0], p[1], p[2]))

    result = []
    for send, _sid, kind, appt_id, channel, text in planned:
        local_send = send.astimezone(DUBLIN)
        log.info("planned reminder id=%s kind=%s channel=%s send_at=%s",
                 appt_id, "first" if kind == 0 else "second", channel,
                 local_send.isoformat())
        result.append({
            "appointment_id": appt_id,
            "channel": channel,
            "send_at": local_send,
            "text": text,
        })
    return result


# ===== FILE: test_reminders.py =====
import copy
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from reminders import plan_reminders

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIG = "Siobh\u00e1n N\u00ed Dhuibhir"
SIG_PL = "Grzegorz Szczepa\u0144ski"


def d(y, mo, da, h=0, mi=0, tz=DUB):
    return datetime(y, mo, da, h, mi, tzinfo=tz)


def appt(**kw):
    base = dict(id="A1", customer_name="Mary Murphy", email="mary@example.com",
                phone="+353871234567", country="IE", status="booked",
                starts_at=d(2026, 11, 10, 14), optout_sms_v2=False)
    base.update(kw)
    return base


def quiet(dt):
    h = dt.astimezone(DUB).hour
    return h >= 21 or h < 8


def test_naive_now_raises():
    with pytest.raises(ValueError):
        plan_reminders([], datetime(2026, 1, 1))


@pytest.mark.parametrize("status", [" Cancelled ", "CANCELLED", "cancelled"])
def test_cancelled_gets_nothing(status):
    assert plan_reminders([appt(status=status)], d(2026, 11, 1)) == []


@pytest.mark.parametrize("status", ["Confirmed", None, "weird", ""])
def test_other_status_active(status):
    assert plan_reminders([appt(status=status)], d(2026, 11, 1))


def test_past_or_started_gets_nothing():
    now = d(2026, 11, 10, 14)
    assert plan_reminders([appt()], now) == []
    assert plan_reminders([appt()], now + timedelta(hours=1)) == []


def test_no_contact_warns_with_id_only(caplog):
    caplog.set_level(logging.DEBUG)
    a = appt(phone=None, email="  ", customer_name="Hidden Person")
    assert plan_reminders([a], d(2026, 11, 1)) == []
    assert "A1" in caplog.text
    assert "Hidden" not in caplog.text


def test_more_than_48h_away():
    r = plan_reminders([appt()], d(2026, 11, 1, 12))
    assert [x["send_at"] for x in r] == [d(2026, 11, 8, 14), d(2026, 11, 10, 12)]


def test_30h_away():
    now = d(2026, 11, 9, 8)
    r = plan_reminders([appt()], now)
    assert [x["send_at"] for x in r] == [now, d(2026, 11, 10, 12)]


def test_1h_away_single_reminder_now():
    now = d(2026, 11, 10, 13)
    r = plan_reminders([appt()], now)
    assert [x["send_at"] for x in r] == [now]


def test_invariants_sweep():
    starts = [d(2026, 11, 10, 14), d(2026, 11, 10, 9), d(2026, 11, 10, 0, 30),
              d(2026, 11, 10, 22), d(2026, 11, 10, 7, 59), d(2026, 11, 10, 8),
              d(2026, 10, 26, 10), d(2026, 10, 25, 9), d(2027, 3, 29, 10),
              d(2027, 3, 28, 9)]
    for start in starts:
        for mins in range(1, 3600, 37):
            now = start - timedelta(minutes=mins)
            r = plan_reminders([appt(starts_at=start)], now)
            assert len(r) <= 2
            assert len({x["send_at"] for x in r}) == len(r)
            for x in r:
                assert now <= x["send_at"] < start
                assert not quiet(x["send_at"])


def test_nine_am_before_2000():
    start = d(2026, 11, 10, 9)
    now = d(2026, 11, 9, 15)
    r = plan_reminders([appt(starts_at=start)], now)
    assert [x["send_at"] for x in r] == [now, d(2026, 11, 9, 20)]


def test_nine_am_between_2000_and_2100():
    start = d(2026, 11, 10, 9)
    now = d(2026, 11, 9, 20, 30)
    r = plan_reminders([appt(starts_at=start)], now)
    assert [x["send_at"] for x in r] == [now]


def test_nine_am_at_2130_goes_to_0800():
    start = d(2026, 11, 10, 9)
    r = plan_reminders([appt(starts_at=start)], d(2026, 11, 9, 21, 30))
    assert [x["send_at"] for x in r] == [d(2026, 11, 10, 8)]


def test_nine_am_early_morning_now():
    start = d(2026, 11, 10, 9)
    r = plan_reminders([appt(starts_at=start)], d(2026, 11, 9, 6))
    assert [x["send_at"] for x in r] == [d(2026, 11, 9, 8), d(2026, 11, 9, 20)]


@pytest.mark.parametrize("kw,expected", [
    ({}, "sms"),
    ({"optout_sms_v2": True}, "email"),
    ({"optout_sms_v2": None}, "email"),
    ({"phone": "   "}, "email"),
    ({"phone": None}, "email"),
    ({"phone": 12345}, "email"),
    ({"opt_out": True}, "sms"),
    ({"opt_out": False, "optout_sms_v2": True}, "email"),
])
def test_channel_selection(kw, expected):
    r = plan_reminders([appt(**kw)], d(2026, 11, 1))
    assert {x["channel"] for x in r} == {expected}
    assert len(r) == 2


def test_missing_optout_field_means_opted_out():
    a = appt()
    del a["optout_sms_v2"]
    assert {x["channel"] for x in plan_reminders([a], d(2026, 11, 1))} == {"email"}


def test_opted_out_without_email_gets_nothing():
    assert plan_reminders([appt(optout_sms_v2=True, email=None)], d(2026, 11, 1)) == []


def test_signatures():
    r = plan_reminders([appt()], d(2026, 11, 1))
    assert all(x["text"].endswith(SIG) for x in r)
    for c in ("PL", " pl ", "Pl"):
        r = plan_reminders([appt(country=c)], d(2026, 11, 1))
        assert all(x["text"].endswith(SIG_PL) for x in r)


def test_dublin_display_from_utc():
    start = datetime(2026, 7, 14, 8, 30, tzinfo=UTC)
    r = plan_reminders([appt(starts_at=start)], datetime(2026, 7, 1, tzinfo=UTC))
    assert r[0]["text"].startswith(
        "Hi Mary Murphy, a reminder of your appointment at Brennan Opticians "
        "on 14 Jul 2026 at 09:30.")
    assert r[0]["send_at"].tzinfo.key == "Europe/Dublin"
    assert r[0]["send_at"] == datetime(2026, 7, 12, 8, 30, tzinfo=UTC)
    assert r[0]["send_at"].hour == 9


def test_autumn_dst():
    r = plan_reminders([appt(starts_at=d(2026, 10, 26, 10))], d(2026, 10, 1, 12))
    assert r[0]["send_at"] == d(2026, 10, 24, 11)
    assert r[0]["send_at"].hour == 11
    assert r[1]["send_at"] == d(2026, 10, 26, 8)


def test_spring_dst():
    r = plan_reminders([appt(starts_at=d(2027, 3, 29, 10))], d(2027, 3, 1, 12))
    assert r[0]["send_at"] == datetime(2027, 3, 27, 9, tzinfo=UTC)
    assert r[0]["send_at"].hour == 9
    assert r[1]["send_at"] == d(2027, 3, 29, 8)


def test_sorting_and_keys():
    items = [appt(id="B"), appt(id="A"), appt(id="C", starts_at=d(2026, 11, 9, 14))]
    r = plan_reminders(items, d(2026, 11, 1))
    keys = [(x["send_at"].astimezone(UTC), str(x["appointment_id"])) for x in r]
    assert keys == sorted(keys)
    assert [x["appointment_id"] for x in r][:3] == ["C", "A", "B"]
    for x in r:
        assert set(x) == {"appointment_id", "channel", "send_at", "text"}


def test_inputs_unchanged():
    items = [appt(), appt(id="B", status="cancelled"), appt(id="C", optout_sms_v2=True)]
    before = copy.deepcopy(items)
    plan_reminders(items, d(2026, 11, 1))
    assert items == before


def test_sms_length_limit_long_names():
    long_name = " ".join(["Bartholomew-Maximilian"] * 20)
    for country, sig in (("IE", SIG), ("PL", SIG_PL)):
        for name in (long_name, "C" * 300 + " Smith", "Aaaa " + "B" * 300):
            for x in plan_reminders([appt(customer_name=name, country=country)],
                                    d(2026, 11, 1)):
                assert len(x["text"]) <= 160
                assert x["text"].endswith(sig)
                assert "10 Nov 2026 at 14:00. " in x["text"]


def test_sms_shrink_steps():
    r = plan_reminders([appt(customer_name="Aaaa " + "B" * 300)], d(2026, 11, 1))
    assert r[0]["text"].startswith("Hi Aaaa, a reminder")
    r = plan_reminders([appt(customer_name="C" * 300 + " Smith")], d(2026, 11, 1))
    assert r[0]["text"].startswith("Hi CCCC") and len(r[0]["text"]) == 160


def test_email_never_shortened():
    name = " ".join(["Bartholomew"] * 30)
    r = plan_reminders([appt(customer_name=name, optout_sms_v2=True)], d(2026, 11, 1))
    assert name in r[0]["text"] and len(r[0]["text"]) > 160


def test_blank_name_neutral_greeting():
    for n in ("   ", None, "\x00\t"):
        r = plan_reminders([appt(customer_name=n)], d(2026, 11, 1))
        assert r[0]["text"].startswith("Hi, a reminder of your appointment")


def test_name_cleaning_and_nfc():
    r = plan_reminders([appt(customer_name="  Mary\t\n  Mur\x00phy\x07 ")], d(2026, 11, 1))
    assert r[0]["text"].startswith("Hi Mary Murphy, a reminder")
    r = plan_reminders([appt(customer_name="Sine\u0301ad")], d(2026, 11, 1))
    assert "Hi Sin\u00e9ad," in r[0]["text"]


def test_malformed_records_skipped(caplog):
    caplog.set_level(logging.DEBUG)
    bad = [
        {"customer_name": "x", "starts_at": d(2026, 11, 10, 14)},
        {"id": "M1", "email": "m1@example.com"},
        {"id": "M2", "email": "m2@example.com", "starts_at": datetime(2026, 11, 10, 14)},
        None,
    ]
    r = plan_reminders(bad + [appt()], d(2026, 11, 1))
    assert {x["appointment_id"] for x in r} == {"A1"}
    assert "M1" in caplog.text and "M2" in caplog.text


def test_info_line_per_reminder(caplog):
    caplog.set_level(logging.INFO)
    r = plan_reminders([appt()], d(2026, 11, 1))
    infos = [x for x in caplog.records if x.levelno == logging.INFO]
    assert len(infos) == len(r) == 2
    assert all("A1" in x.getMessage() and "sms" in x.getMessage() for x in infos)


def test_logs_never_contain_contact_details(caplog):
    caplog.set_level(logging.DEBUG)
    secrets = ["leak-check-1@secret-domain.example", "leak-check-2@secret-domain.example",
               "leak-check-3@secret-domain.example", "leak-check-4@secret-domain.example",
               "+353 87 999 0001", "Zebediah Quillfeather"]
    items = [
        appt(id="S1", email=secrets[0], phone=secrets[4], customer_name=secrets[5]),
        appt(id="E1", email=secrets[1], optout_sms_v2=True, customer_name=secrets[5]),
        appt(id="N1", email="  ", phone=None, customer_name=secrets[5]),
        {"id": "M1", "email": secrets[2], "phone": secrets[4],
         "customer_name": secrets[5], "starts_at": datetime(2026, 11, 10, 14)},
        {"email": secrets[3], "customer_name": secrets[5]},
    ]
    plan_reminders(items, d(2026, 11, 1))
    assert caplog.records
    blob = caplog.text + "\n".join(r.getMessage() for r in caplog.records)
    for s in secrets:
        assert s not in blob
    assert "leak-check" not in blob and "@" not in blob
    assert all(r.exc_info is None for r in caplog.records)
```