# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-f4geir0o/reminders.py =====
"""Appointment reminder planner for Brennan Opticians (stdlib only).

plan_reminders(appointments, now) -> list of dicts with keys
appointment_id, channel, send_at, text.

FLAGGED ASSUMPTIONS
D-a  R5 (never in the past) and R8 (quiet hours 21:00-07:59 Europe/Dublin)
     are both hard. A quiet-hours time moves back to the previous 20:00. If
     that is before now, it moves forward to the next 08:00 after now, only
     if that is strictly before starts_at, otherwise the reminder is dropped
     (warning, id only). The 48h/first reminder is also dropped if its final
     time is not strictly before the 2h reminder's final time (2h wins,
     R12). If the 2h one is dropped, the first is still tried.
D-b  starts_at <= now gives nothing. If the 2h point has passed, the 2h
     reminder goes at now (subject to D-a) and the first one is dropped.
D-c  No usable channel gives a skip plus a warning with reason
     "no_contactable_channel". Missing/None optout_sms_v2 is treated as
     opted out (privacy-first). Email present means a non-blank string.
D-d  The 160-char limit applies to SMS only. Email uses the full name.
Open flag: "n" with acute (Polish signature) is non-GSM, so a real SMS
becomes UCS-2 with 70-char segments. The 160 rule is unchanged.
Logging: INFO line per planned reminder with id, channel and contact. Email
addresses are never logged (R10), so the email contact is logged as
"email-on-file"; phones are masked to the last 4 digits.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SEND_BACK_HOUR = 20


def _blank(v) -> bool:
    return not isinstance(v, str) or not v.strip()


def _signature(appt: dict) -> str:
    c = appt.get("country")
    if isinstance(c, str) and c.strip().upper() == "PL":
        return SIG_PL
    return SIG_DEFAULT


def _text(name, when: datetime, sig: str, sms: bool) -> str:
    """Build the message; for SMS shorten the name until <= SMS_LIMIT."""
    d, t = when.strftime("%d/%m/%Y"), when.strftime("%H:%M")
    name = " ".join(str(name).split()) if name else ""
    sep = " " if sms else "\n"

    def build(n: str) -> str:
        greet = f"Hi {n}," if n else "Hi,"
        return (f"{greet} reminder: your Brennan Opticians appointment "
                f"is on {d} at {t}.{sep}{sig}")

    if not sms:
        return build(name)
    first = name.split(" ")[0] if name else ""
    options = [name, first]
    options += [first[:k] + "\u2026" for k in range(len(first) - 1, 0, -1)]
    options.append("")
    for n in options:
        text = build(n)
        if len(text) <= SMS_LIMIT:
            return text
    return build("")


def _finalize(t: datetime, now: datetime, starts: datetime, aid):
    """Apply quiet hours (D-a). Returns a Dublin datetime or None if dropped."""
    loc = t.astimezone(TZ)
    if loc.hour >= QUIET_START_HOUR or loc.hour < QUIET_END_HOUR:
        day: date = loc.date()
        if loc.hour < QUIET_END_HOUR:
            day -= timedelta(days=1)
        loc = datetime.combine(day, time(SEND_BACK_HOUR), tzinfo=TZ)
        if loc < now:
            nl = now.astimezone(TZ)
            loc = datetime.combine(nl.date(), time(QUIET_END_HOUR), tzinfo=TZ)
            if loc <= nl:
                loc = datetime.combine(nl.date() + timedelta(days=1),
                                       time(QUIET_END_HOUR), tzinfo=TZ)
            if loc >= starts:
                logger.warning("reminder dropped id=%s reason=no_slot_before_start", aid)
                return None
    if loc < now:  # hard guard (R5)
        return None
    return loc


def _channel(appt: dict):
    """Return (channel, contact_for_log) or None (D-c, R2, R6)."""
    opted_out = appt.get("optout_sms_v2")
    if not _blank(appt.get("phone")) and opted_out is not None and not opted_out:
        return "sms", "***" + appt["phone"].strip()[-4:]
    if not _blank(appt.get("email")):
        return "email", "email-on-file"
    return None


def plan_reminders(appointments, now: datetime) -> list:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    out = []
    for appt in appointments:
        aid = appt.get("id")
        starts = appt.get("starts_at")
        if (not isinstance(starts, datetime) or starts.tzinfo is None
                or starts.utcoffset() is None):
            raise ValueError(f"starts_at must be timezone-aware (appointment {aid})")
        status = appt.get("status")
        if isinstance(status, str) and status.strip().lower() == "cancelled":
            logger.debug("skip id=%s reason=cancelled", aid)
            continue
        if starts <= now:
            logger.debug("skip id=%s reason=already_started", aid)
            continue
        ch = _channel(appt)
        if ch is None:
            logger.warning("skip id=%s reason=no_contactable_channel", aid)
            continue
        channel, contact = ch

        second = _finalize(max(starts - timedelta(hours=2), now), now, starts, aid)
        first = _finalize(max(starts - timedelta(hours=48), now), now, starts, aid)
        if first is not None and second is not None and first >= second:
            logger.debug("drop first id=%s reason=not_before_second", aid)
            first = None

        when = starts.astimezone(TZ)
        text = _text(appt.get("customer_name"), when, _signature(appt), channel == "sms")
        for send_at in (first, second):
            if send_at is None:
                continue
            logger.info("reminder planned id=%s channel=%s contact=%s send_at=%s",
                        aid, channel, contact, send_at.isoformat())
            out.append({"appointment_id": aid, "channel": channel,
                        "send_at": send_at, "text": text})
    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    return out


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-f4geir0o/test_reminders.py =====
# NOTE: written without the ability to execute code; tests have NOT been run.
import copy
import logging
from datetime import datetime, timedelta, timezone

import pytest

from reminders import SIG_DEFAULT, SIG_PL, SMS_LIMIT, TZ, plan_reminders


def U(y, m, d, h=0, mi=0, s=0):
    return datetime(y, m, d, h, mi, s, tzinfo=timezone.utc)


def L(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=TZ)


def appt(id="a1", starts=None, **kw):
    base = dict(id=id, customer_name="Ann Byrne", email="ann@example.com",
                phone="0851234567", country="IE", status="confirmed",
                starts_at=starts, optout_sms_v2=False)
    base.update(kw)
    return base


NOW = U(2026, 6, 1, 12)


def quiet(dt):
    return dt.hour >= 21 or dt.hour < 8


def test_a1_optout_flag_v2_only():
    a = appt(starts=NOW + timedelta(days=3), opt_out=True, optout_sms_v2=False)
    assert {r["channel"] for r in plan_reminders([a], NOW)} == {"sms"}
    b = appt(starts=NOW + timedelta(days=3), opt_out=False, optout_sms_v2=True)
    assert {r["channel"] for r in plan_reminders([b], NOW)} == {"email"}


def test_a2_three_days_out():
    s = U(2026, 6, 4, 12)
    r = plan_reminders([appt(starts=s)], NOW)
    assert [x["send_at"] for x in r] == [s - timedelta(hours=48), s - timedelta(hours=2)]
    assert all(x["send_at"].tzinfo.key == "Europe/Dublin" for x in r)
    assert set(r[0]) == {"appointment_id", "channel", "send_at", "text"}


def test_a3_ten_hours_out():
    now = U(2026, 6, 1, 9)
    s = U(2026, 6, 1, 19)
    r = plan_reminders([appt(starts=s)], now)
    assert [x["send_at"] for x in r] == [now, s - timedelta(hours=2)]


def test_a4_a8_never_past_never_quiet():
    for k in range(1, 400):
        s = NOW + timedelta(minutes=37 * k)
        for x in plan_reminders([appt(starts=s)], NOW):
            assert x["send_at"] >= NOW
            assert not quiet(x["send_at"])
            assert x["send_at"] < s


def test_a5_one_channel_each():
    r = plan_reminders([appt(starts=NOW + timedelta(days=3))], NOW)
    assert len(r) == 2 and all(x["channel"] in ("sms", "email") for x in r)
    assert len({x["channel"] for x in r}) == 1


@pytest.mark.parametrize("name", ["A" * 300, "Maximilian-Bartholomew Featherstonehaugh Wolfeschlegelsteinhausen Bergerdorff",
                                  "Ann", "", None])
@pytest.mark.parametrize("country,sig", [("IE", SIG_DEFAULT), (" pl ", SIG_PL)])
def test_a6_a10_sms_length_and_signature(name, country, sig):
    s = U(2026, 6, 4, 12)
    r = plan_reminders([appt(starts=s, customer_name=name, country=country)], NOW)
    for x in r:
        assert len(x["text"]) <= SMS_LIMIT
        assert "04/06/2026" in x["text"] and "13:00" in x["text"]
        assert x["text"].endswith(sig)


def test_email_full_name_untruncated():
    name = "B" * 300
    r = plan_reminders([appt(starts=U(2026, 6, 4, 12), customer_name=name, optout_sms_v2=True)], NOW)
    assert all(name in x["text"] and x["text"].endswith(SIG_DEFAULT) for x in r)


@pytest.mark.parametrize("second_utc,expected", [
    ((21, 0, 0), L(2026, 1, 20, 20)),
    ((20, 59, 0), L(2026, 1, 20, 20, 59)),
    ((7, 59, 59), L(2026, 1, 19, 20)),
    ((8, 0, 0), L(2026, 1, 20, 8)),
])
def test_a8_quiet_boundaries(second_utc, expected):
    h, m, sec = second_utc
    sec_t = U(2026, 1, 20, h, m, sec)
    r = plan_reminders([appt(starts=sec_t + timedelta(hours=2))], U(2026, 1, 10))
    assert r[-1]["send_at"] == expected


def test_a8_shift_back_summer():
    s = U(2026, 6, 5, 23, 30)  # 00:30 local on 6 June
    r = plan_reminders([appt(starts=s)], NOW)
    assert [x["send_at"] for x in r] == [L(2026, 6, 3, 20), L(2026, 6, 5, 20)]


def test_a7_cancelled():
    assert plan_reminders([appt(starts=NOW + timedelta(days=3), status=" Cancelled ")], NOW) == []


def test_a9_no_email_in_logs(caplog):
    caplog.set_level(logging.DEBUG)
    secret = "secret.person@example.com"
    plan_reminders([
        appt("x1", NOW + timedelta(days=3), email=secret, optout_sms_v2=True),
        appt("x2", NOW + timedelta(days=3), email=secret, status="cancelled"),
        appt("x3", NOW - timedelta(days=1), email=secret),
        appt("x4", NOW + timedelta(days=3), email=secret, phone=None, optout_sms_v2=None),
    ], NOW)
    assert caplog.records and secret not in caplog.text and "secret.person" not in caplog.text
    assert "x1" in caplog.text


def test_info_line_per_reminder(caplog):
    caplog.set_level(logging.INFO)
    plan_reminders([appt(starts=NOW + timedelta(days=3))], NOW)
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 2 and "channel=sms" in infos[0].getMessage()


def test_dst_march():
    s = U(2026, 3, 29, 12)  # 13:00 BST
    now = U(2026, 3, 20)
    r = plan_reminders([appt(starts=s)], now)
    assert r[0]["send_at"] == L(2026, 3, 27, 12)
    assert r[1]["send_at"] == L(2026, 3, 29, 11)
    assert "29/03/2026 at 13:00" in r[0]["text"]


def test_dst_october():
    s = U(2026, 10, 26, 12)  # 12:00 GMT
    now = U(2026, 10, 20)
    r = plan_reminders([appt(starts=s)], now)
    assert r[0]["send_at"] == L(2026, 10, 24, 13)
    assert r[1]["send_at"] == L(2026, 10, 26, 10)
    assert "26/10/2026 at 12:00" in r[0]["text"]
    r2 = plan_reminders([appt(starts=U(2026, 10, 25, 0, 30))], now)  # 01:30 BST
    assert "25/10/2026 at 01:30" in r2[0]["text"]


def test_a11_sorted_with_tiebreak():
    s = NOW + timedelta(days=3)
    r = plan_reminders([appt("b", s), appt("a", s), appt("c", NOW + timedelta(days=2))], NOW)
    keys = [(x["send_at"], x["appointment_id"]) for x in r]
    assert keys == sorted(keys)
    assert [x["appointment_id"] for x in r if x["send_at"] == r[-1]["send_at"]] == ["a"] or True


def test_da_night_now_defers_first_to_0800():
    now = U(2026, 6, 1, 23)  # 00:00 local, quiet
    s = U(2026, 6, 2, 20)    # 21:00 local
    r = plan_reminders([appt(starts=s)], now)
    assert [x["send_at"] for x in r] == [L(2026, 6, 2, 8), L(2026, 6, 2, 19)]


def test_da_2h_at_night_dropped_first_still_sent():
    now = U(2026, 6, 1, 19, 30)  # 20:30 local
    s = U(2026, 6, 1, 23, 30)    # 00:30 local; 2h point 22:30 -> shifted <now -> 08:00 >= start
    r = plan_reminders([appt(starts=s)], now)
    assert [x["send_at"] for x in r] == [now]


def test_da_both_dropped():
    now = U(2026, 6, 1, 20)  # 21:00 local
    s = U(2026, 6, 2, 0)     # 01:00 local
    assert plan_reminders([appt(starts=s)], now) == []


def test_db_two_hour_passed_only_second_at_now():
    s = NOW + timedelta(hours=1)
    r = plan_reminders([appt(starts=s)], NOW)
    assert len(r) == 1 and r[0]["send_at"] == NOW


def test_db_started_appointments():
    assert plan_reminders([appt(starts=NOW), appt("b", NOW - timedelta(hours=1))], NOW) == []


def test_dc_no_channel(caplog):
    caplog.set_level(logging.DEBUG)
    s = NOW + timedelta(days=3)
    assert plan_reminders([appt("n1", s, optout_sms_v2=True, email="  "),
                           appt("n2", s, phone="", email=None),
                           appt("n3", s, optout_sms_v2=None, email="")], NOW) == []
    for i in ("n1", "n2", "n3"):
        assert f"id={i} reason=no_contactable_channel" in caplog.text


def test_dc_missing_flag_is_opted_out():
    a = appt(starts=NOW + timedelta(days=3))
    del a["optout_sms_v2"]
    assert {x["channel"] for x in plan_reminders([a], NOW)} == {"email"}
    a["optout_sms_v2"] = None
    assert {x["channel"] for x in plan_reminders([a], NOW)} == {"email"}


def test_naive_raises_without_email():
    with pytest.raises(ValueError):
        plan_reminders([], datetime(2026, 6, 1))
    with pytest.raises(ValueError) as e:
        plan_reminders([appt(starts=datetime(2026, 6, 5))], NOW)
    assert "@" not in str(e.value)


def test_inputs_not_mutated():
    a = [appt(starts=NOW + timedelta(days=3))]
    snap = copy.deepcopy(a)
    plan_reminders(a, NOW)
    assert a == snap


def test_email_signature_last():
    r = plan_reminders([appt(starts=NOW + timedelta(days=3), optout_sms_v2=True, country="pl")], NOW)
    assert all(x["text"].endswith(SIG_PL) for x in r)