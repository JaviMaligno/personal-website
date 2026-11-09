# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-99vajey6/reminders.py
# NOTE: I have no execution tools, so neither file has been run. Run `python3 -m pytest` before relying on them.
"""Appointment reminder planner for Brennan Opticians.

Public entry point: plan_reminders(appointments, now) -> list of dicts
(appointment_id, channel, send_at, text), sorted by send_at.
Also: plan_reminders_detailed(appointments, now) -> (reminders, skipped).

STATELESS: nothing records what was already sent. Repeated runs can re-send
(especially the "first reminder at now" fallback). The CALLER owns idempotency.

LOGGING: only appointment id, channel, contact TYPE ("phone"/"email"), reason
codes and counts are logged. The house rule asks for "channel and contact" per
INFO line, but the regulator requirement (never log email) and design decision
11 (no phone/name) win, so the contact value itself is never logged.

ASSUMPTION - needs client confirmation (numbered as in the design):
 1. Quiet hours = Dublin local t >= 21:00 or t < 08:00. Raw time = start - 48h/2h
    as absolute elapsed time (UTC). ALTERNATIVE: wall-clock subtraction (differs
    across DST changes). If raw < now use now. If in quiet hours move back to the
    20:00 just before; if that is before now, use the NEXT 08:00 instead. Drop if
    final send_at >= start. Appointments with start <= now yield nothing.
 2. A reminder landing in quiet hours moves to 20:00 the previous evening, so the
    2h reminder may go out much earlier than 2h before (e.g. 08:00-10:59 starts).
 3. If both reminders end with identical send_at, only the 2-hour one is kept.
 4. Channel: phone = non-blank str; email = non-blank str containing "@". Phone and
    not opted out -> sms; else email if valid; else skip (WARNING, id + reason).
 5. optout_sms_v2 accepts bool, int 0/1, "true"/"false" (any case). Missing, None or
    unrecognised = OPTED OUT (fail-safe, no SMS) with a WARNING by id.
 6. Status is stripped/casefolded; "cancelled"/"canceled" excluded (DEBUG). Missing or
    non-string status = malformed, skipped with WARNING. Other values are processed.
 7. Sort key: (send_at UTC instant, str(id), sequence 0=48h / 1=2h); not in output.
 8. Text: "Hi {name}, reminder: your Brennan Opticians appointment is on {Tue 20 Oct
    2026} at {HH:MM}. {signature}" (no-name form "Hi, reminder: ..."). English
    abbreviations hard-coded. Time is Europe/Dublin for ALL customers incl. PL
    (Krakow/Warsaw question open). Same wording for both reminders.
 9. SMS limit 160 chars incl. signature; name shortened in stages: full, first token,
    initial + ".", none. If still too long send as is with WARNING. RISK: fada letters
    and n-acute force UCS-2 (about 70 chars per segment), so 160 may under-protect.
    Email is never shortened.
10. country.strip().upper() == "PL" selects "Grzegorz Szczepański"; anything else
    (including missing) uses "Siobhán Ní Dhuibhir".
11. Per-record exceptions log only the exception class name.
12. Each record is processed in try/except; required: id, status, starts_at. Naive or
    non-datetime starts_at is skipped. Missing id skipped (index logged). Naive or
    non-datetime `now` raises ValueError.
13. Duplicate ids: first kept, later ones skipped with WARNING. Inputs not mutated.
14. send_at is an aware datetime in Europe/Dublin.
15. plan_reminders delegates to plan_reminders_detailed.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("brennan.reminders")

TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_CANCELLED = {"cancelled", "canceled"}


def _at(d, hour):
    return datetime(d.year, d.month, d.day, hour, tzinfo=TZ)


def _adjust(raw, now):
    cand = now if raw < now else raw
    loc = cand.astimezone(TZ)
    if 8 <= loc.hour < 21:
        return loc
    one = timedelta(days=1)
    if loc.hour >= 21:
        back_date, next_date = loc.date(), loc.date() + one
    else:
        back_date, next_date = loc.date() - one, loc.date()
    back = _at(back_date, 20)
    return back if back >= now else _at(next_date, 8)


def _parse_optout(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().casefold()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


def _valid_str(v):
    return isinstance(v, str) and v.strip() != ""


def _render(name, date, hhmm, sig):
    greet = "Hi %s," % name if name else "Hi,"
    return "%s reminder: your Brennan Opticians appointment is on %s at %s. %s" % (
        greet, date, hhmm, sig)


def _build_text(raw_name, date, hhmm, sig, sms, aid):
    name = " ".join(raw_name.split()) if isinstance(raw_name, str) else ""
    if not name:
        return _render(None, date, hhmm, sig)
    if not sms:
        return _render(name, date, hhmm, sig)
    first = name.split()[0]
    for cand in (name, first, first[0] + ".", None):
        text = _render(cand, date, hhmm, sig)
        if len(text) <= SMS_LIMIT:
            return text
    logger.warning("sms over limit after shortening appointment=%s", aid)
    return text


def _process(rec, aid, now):
    """Return (list of (seq, send_at, dict, contact_type), skip_reason)."""
    status = rec.get("status")
    if not isinstance(status, str):
        logger.warning("skip appointment=%s reason=malformed_status", aid)
        return [], "malformed_status"
    if status.strip().casefold() in _CANCELLED:
        logger.debug("skip appointment=%s reason=cancelled", aid)
        return [], "cancelled"
    start = rec.get("starts_at")
    if not isinstance(start, datetime) or start.utcoffset() is None:
        logger.warning("skip appointment=%s reason=invalid_starts_at", aid)
        return [], "invalid_starts_at"
    if start <= now:
        logger.debug("skip appointment=%s reason=already_started", aid)
        return [], "already_started"

    optout = _parse_optout(rec.get("optout_sms_v2"))
    if optout is None:
        logger.warning("appointment=%s optout_sms_v2 missing/unrecognised, treated as opted out", aid)
        optout = True
    phone, email = rec.get("phone"), rec.get("email")
    if _valid_str(phone) and not optout:
        channel, contact = "sms", "phone"
    elif _valid_str(email) and "@" in email:
        channel, contact = "email", "email"
    else:
        logger.warning("skip appointment=%s reason=no_channel", aid)
        return [], "no_channel"

    loc = start.astimezone(TZ)
    date = "%s %02d %s %d" % (_DAYS[loc.weekday()], loc.day, _MONTHS[loc.month - 1], loc.year)
    hhmm = "%02d:%02d" % (loc.hour, loc.minute)
    country = rec.get("country")
    pl = str(country).strip().upper() == "PL" if country is not None else False
    sig = "Grzegorz Szczepański" if pl else "Siobhán Ní Dhuibhir"
    text = _build_text(rec.get("customer_name"), date, hhmm, sig, channel == "sms", aid)

    s_utc = start.astimezone(UTC)
    sends = [(0, _adjust(s_utc - timedelta(hours=48), now)),
             (1, _adjust(s_utc - timedelta(hours=2), now))]
    sends = [(q, t) for q, t in sends if t < start]
    if len(sends) == 2 and sends[0][1] == sends[1][1]:
        sends = sends[1:]
    return [(q, t, {"appointment_id": aid, "channel": channel, "send_at": t, "text": text},
             contact) for q, t in sends], None


def plan_reminders_detailed(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    items, skipped, seen = [], [], set()
    for idx, rec in enumerate(appointments):
        ident = idx
        try:
            aid = rec.get("id")
            if aid is None:
                logger.warning("skip index=%s reason=missing_id", idx)
                skipped.append((idx, "missing_id"))
                continue
            ident = aid
            if aid in seen:
                logger.warning("skip appointment=%s reason=duplicate_id", aid)
                skipped.append((aid, "duplicate_id"))
                continue
            seen.add(aid)
            res, reason = _process(rec, aid, now)
            if reason:
                skipped.append((aid, reason))
            items.extend(res)
        except Exception as exc:
            logger.warning("skip appointment=%s reason=error type=%s", ident, type(exc).__name__)
            skipped.append((ident, "error"))
    items.sort(key=lambda i: (i[1].astimezone(UTC), str(i[2]["appointment_id"]), i[0]))
    for _, t, d, contact in items:
        logger.info("reminder planned appointment=%s channel=%s contact_type=%s send_at=%s",
                    d["appointment_id"], d["channel"], contact, t.isoformat())
    logger.info("planned reminders=%d skipped=%d", len(items), len(skipped))
    return [i[2] for i in items], skipped


def plan_reminders(appointments, now):
    return plan_reminders_detailed(appointments, now)[0]


# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-99vajey6/tests/test_reminders.py
# Acceptance criteria -> tests
# | Requirement                          | Tests                                                        |
# | 48h and 2h reminders                 | test_normal_48h_and_2h_daytime                               |
# | 48h passed -> first at now           | test_first_reminder_at_now_when_48h_passed                   |
# | Never past / quiet hours             | test_now_in_quiet_hours_deferred_to_0800, test_back_2000_in_past_goes_to_next_0800, test_quiet_hour_boundaries |
# | Drop if deferred >= start            | test_drop_when_deferred_time_after_start                     |
# | Started appointment                  | test_started_appointment_yields_nothing                      |
# | 2h moved to previous evening         | test_2h_moved_to_2000_previous_evening                       |
# | Collapse identical send_at           | test_collapse_keeps_2h_only, test_collapse_when_inside_2h_window |
# | Europe/Dublin, DST, UTC server       | test_dst_spring_forward, test_dst_autumn_back, test_utc_input_displays_local_time |
# | SMS vs email, opt-out v2 only        | test_optout_true_gives_email, test_optout_missing_or_none_gives_email, test_optout_accepted_forms, test_old_opt_out_field_ignored |
# | No phone -> email                    | test_no_phone_gives_email, test_opted_out_without_email_skipped |
# | One channel per reminder             | test_each_reminder_one_channel                               |
# | Cancelled excluded                   | test_cancelled_excluded, test_missing_status_skipped         |
# | Signature / PL                       | test_signatures                                              |
# | SMS 160 limit, date/time kept        | test_sms_length_limit_long_name, test_staged_shortening, test_blank_name_fallback |
# | Email not shortened                  | test_email_text_not_shortened                                |
# | Sorted by send_at                    | test_sorted_with_tiebreak_and_mixed                          |
# | No mutation, duplicates, malformed   | test_no_input_mutation, test_duplicate_ids, test_malformed_record_does_not_crash, test_naive_starts_at_skipped |
# | Naive now                            | test_naive_now_raises                                        |
# | Never log email/phone/name           | test_no_pii_in_logs                                          |
import copy
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reminders import plan_reminders, plan_reminders_detailed  # noqa: E402

D = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
START = datetime(2026, 10, 20, 12, 0, tzinfo=D)


def dub(*a):
    return datetime(*a, tzinfo=D)


def appt(**kw):
    base = {"id": "a1", "customer_name": "Anna Murphy", "email": "anna@example.com",
            "phone": "0851234567", "country": "IE", "status": "booked",
            "starts_at": START, "optout_sms_v2": False}
    base.update(kw)
    return base


def test_normal_48h_and_2h_daytime():
    res = plan_reminders([appt()], dub(2026, 10, 10, 10))
    assert [r["send_at"] for r in res] == [dub(2026, 10, 18, 12), dub(2026, 10, 20, 10)]
    assert all("Tue 20 Oct 2026 at 12:00" in r["text"] for r in res)
    assert set(res[0]) == {"appointment_id", "channel", "send_at", "text"}


def test_first_reminder_at_now_when_48h_passed():
    now = dub(2026, 10, 19, 10)
    res = plan_reminders([appt()], now)
    assert [r["send_at"] for r in res] == [now, dub(2026, 10, 20, 10)]


def test_now_in_quiet_hours_deferred_to_0800():
    res = plan_reminders([appt()], dub(2026, 10, 19, 22))
    assert [r["send_at"] for r in res] == [dub(2026, 10, 20, 8), dub(2026, 10, 20, 10)]


def test_back_2000_in_past_goes_to_next_0800():
    res = plan_reminders([appt()], dub(2026, 10, 20, 3))
    assert res[0]["send_at"] == dub(2026, 10, 20, 8)


def test_drop_when_deferred_time_after_start():
    a = appt(starts_at=dub(2026, 10, 20, 7, 30))
    assert plan_reminders([a], dub(2026, 10, 19, 22)) == []


def test_started_appointment_yields_nothing():
    assert plan_reminders([appt()], dub(2026, 10, 20, 12)) == []
    assert plan_reminders([appt()], dub(2026, 10, 21, 12)) == []


@pytest.mark.parametrize("h,m,expected", [
    (20, 59, dub(2026, 10, 14, 20, 59)),
    (21, 0, dub(2026, 10, 14, 20, 0)),
    (7, 59, dub(2026, 10, 13, 20, 0)),
    (8, 0, dub(2026, 10, 14, 8, 0)),
])
def test_quiet_hour_boundaries(h, m, expected):
    raw = dub(2026, 10, 14, h, m)
    res = plan_reminders([appt(starts_at=raw + timedelta(hours=2))], dub(2026, 10, 1, 10))
    assert res[-1]["send_at"] == expected


def test_2h_moved_to_2000_previous_evening():
    res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 9))], dub(2026, 10, 10, 10))
    assert res[-1]["send_at"] == dub(2026, 10, 19, 20)


def test_collapse_keeps_2h_only():
    a = appt(starts_at=dub(2026, 10, 20, 9, 30))
    res = plan_reminders([a], dub(2026, 10, 20, 7))
    assert len(res) == 1 and res[0]["send_at"] == dub(2026, 10, 20, 8)


def test_collapse_when_inside_2h_window():
    now = dub(2026, 10, 20, 11)
    res = plan_reminders([appt()], now)
    assert len(res) == 1 and res[0]["send_at"] == now


def test_dst_spring_forward():
    start = dub(2026, 3, 29, 12)  # IST, 11:00 UTC
    res = plan_reminders([appt(starts_at=start)], dub(2026, 3, 20, 10))
    assert res[0]["send_at"] == datetime(2026, 3, 27, 11, 0, tzinfo=UTC)
    assert res[0]["send_at"].hour == 11  # not 12: 48h elapsed, not wall-clock
    assert res[1]["send_at"] == dub(2026, 3, 29, 10)


def test_dst_autumn_back():
    start = dub(2026, 10, 25, 12)  # GMT, 12:00 UTC
    res = plan_reminders([appt(starts_at=start)], dub(2026, 10, 15, 10))
    assert res[0]["send_at"] == dub(2026, 10, 23, 13)
    assert res[1]["send_at"] == datetime(2026, 10, 25, 10, 0, tzinfo=UTC)


def test_utc_input_displays_local_time():
    start = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    res = plan_reminders([appt(starts_at=start)], datetime(2026, 7, 1, tzinfo=UTC))
    assert all("Wed 15 Jul 2026 at 13:00" in r["text"] for r in res)
    assert res[0]["send_at"].tzinfo is not None


def test_optout_true_gives_email():
    res = plan_reminders([appt(optout_sms_v2=True)], dub(2026, 10, 10, 10))
    assert {r["channel"] for r in res} == {"email"}


def test_optout_missing_or_none_gives_email():
    a = appt()
    del a["optout_sms_v2"]
    b = appt(id="b", optout_sms_v2=None)
    res = plan_reminders([a, b], dub(2026, 10, 10, 10))
    assert {r["channel"] for r in res} == {"email"}


@pytest.mark.parametrize("val,channel", [
    (1, "email"), (0, "sms"), ("TRUE", "email"), (" false ", "sms"), ("maybe", "email")])
def test_optout_accepted_forms(val, channel):
    res = plan_reminders([appt(optout_sms_v2=val)], dub(2026, 10, 10, 10))
    assert {r["channel"] for r in res} == {channel}


def test_old_opt_out_field_ignored():
    r1 = plan_reminders([appt(opt_out=True, optout_sms_v2=False)], dub(2026, 10, 10, 10))
    r2 = plan_reminders([appt(opt_out=False, optout_sms_v2=True)], dub(2026, 10, 10, 10))
    assert {r["channel"] for r in r1} == {"sms"}
    assert {r["channel"] for r in r2} == {"email"}


@pytest.mark.parametrize("phone", [None, "", "   "])
def test_no_phone_gives_email(phone):
    res = plan_reminders([appt(phone=phone)], dub(2026, 10, 10, 10))
    assert res and {r["channel"] for r in res} == {"email"}


def test_opted_out_without_email_skipped():
    a = appt(optout_sms_v2=True, email="")
    res, skipped = plan_reminders_detailed([a], dub(2026, 10, 10, 10))
    assert res == [] and skipped == [("a1", "no_channel")]


@pytest.mark.parametrize("status", ["cancelled", "Cancelled ", "canceled"])
def test_cancelled_excluded(status):
    assert plan_reminders([appt(status=status)], dub(2026, 10, 10, 10)) == []


def test_missing_status_skipped():
    a = appt()
    del a["status"]
    res, skipped = plan_reminders_detailed([a, appt(id="b", status=None)], dub(2026, 10, 10, 10))
    assert res == [] and [s[1] for s in skipped] == ["malformed_status"] * 2


def test_signatures():
    now = dub(2026, 10, 10, 10)
    pl = plan_reminders([appt(country="PL")], now)
    pl2 = plan_reminders([appt(country=" pl ")], now)
    de = plan_reminders([appt(country="IE")], now)
    none = plan_reminders([appt(country=None)], now)
    assert all(r["text"].endswith("Grzegorz Szczepański") for r in pl + pl2)
    assert all(r["text"].endswith("Siobhán Ní Dhuibhir") for r in de + none)


def test_sms_length_limit_long_name():
    a = appt(customer_name="Bartholomew " * 40)
    for r in plan_reminders([a], dub(2026, 10, 10, 10)):
        assert r["channel"] == "sms" and len(r["text"]) <= 160
        assert "Tue 20 Oct 2026" in r["text"] and "12:00" in r["text"]
        assert r["text"].endswith("Siobhán Ní Dhuibhir")


def test_staged_shortening():
    now = dub(2026, 10, 10, 10)
    short = plan_reminders([appt(customer_name="Anna Murphy")], now)[0]["text"]
    assert short.startswith("Hi Anna Murphy,")
    t2 = plan_reminders([appt(customer_name="Anna " + "Z" * 70)], now)[0]["text"]
    assert t2.startswith("Hi Anna, reminder") and len(t2) <= 160
    t3 = plan_reminders([appt(customer_name="A" + "b" * 200 + " Murphy")], now)[0]["text"]
    assert t3.startswith("Hi A., reminder") and len(t3) <= 160


@pytest.mark.parametrize("name", [None, "", "   "])
def test_blank_name_fallback(name):
    t = plan_reminders([appt(customer_name=name)], dub(2026, 10, 10, 10))[0]["text"]
    assert t.startswith("Hi, reminder:") and "12:00" in t


def test_email_text_not_shortened():
    name = "Anna " + "Z" * 300
    res = plan_reminders([appt(customer_name=name, optout_sms_v2=True)], dub(2026, 10, 10, 10))
    assert all(name in r["text"] and len(r["text"]) > 160 for r in res)


def test_sorted_with_tiebreak_and_mixed():
    now = dub(2026, 10, 10, 10)
    appts = [appt(id="b"), appt(id="a", optout_sms_v2=True),
             appt(id="c", starts_at=dub(2026, 10, 22, 15))]
    res = plan_reminders(appts, now)
    sends = [r["send_at"] for r in res]
    assert sends == sorted(sends)
    tied = [r["appointment_id"] for r in res if r["send_at"] == dub(2026, 10, 18, 12)]
    assert tied == ["a", "b"]


def test_each_reminder_one_channel():
    appts = [appt(id="a"), appt(id="b", optout_sms_v2=True)]
    res = plan_reminders(appts, dub(2026, 10, 10, 10))
    assert all(r["channel"] in ("sms", "email") for r in res)
    keys = [(r["appointment_id"], r["send_at"]) for r in res]
    assert len(keys) == len(set(keys))


def test_no_input_mutation():
    appts = [appt(), appt(id="b", optout_sms_v2=True, opt_out=True)]
    before = copy.deepcopy(appts)
    plan_reminders(appts, dub(2026, 10, 10, 10))
    assert appts == before


def test_duplicate_ids():
    a = appt(id="x")
    b = appt(id="x", starts_at=dub(2026, 10, 25, 15))
    res, skipped = plan_reminders_detailed([a, b], dub(2026, 10, 10, 10))
    assert len(res) == 2 and all("Tue 20 Oct" in r["text"] for r in res)
    assert skipped == [("x", "duplicate_id")]


def test_malformed_record_does_not_crash_batch():
    appts = [None, 5, {}, appt(id="bad", starts_at="tomorrow"), appt(id="ok")]
    res, skipped = plan_reminders_detailed(appts, dub(2026, 10, 10, 10))
    assert {r["appointment_id"] for r in res} == {"ok"}
    assert len(skipped) == 4


def test_naive_starts_at_skipped():
    a = appt(starts_at=datetime(2026, 10, 20, 12, 0))
    res, skipped = plan_reminders_detailed([a], dub(2026, 10, 10, 10))
    assert res == [] and skipped == [("a1", "invalid_starts_at")]


def test_naive_now_raises():
    with pytest.raises(ValueError):
        plan_reminders([appt()], datetime(2026, 10, 10, 10))
    with pytest.raises(ValueError):
        plan_reminders([appt()], "now")


def test_no_pii_in_logs(caplog):
    email, phone, name = "secret.person@example.com", "0861239999", "Secretfirst"

    class Boom(dict):
        def get(self, k, d=None):
            if k == "status":
                raise RuntimeError(email + phone + name)
            return super().get(k, d)

    base = dict(email=email, phone=phone)
    appts = [
        appt(id="1", customer_name=name + " " + "Q" * 80, **base),
        appt(id="2", customer_name=name, optout_sms_v2=True, **base),
        appt(id="3", customer_name=name, optout_sms_v2=True, **dict(base, email="")),
        appt(id="4", customer_name=name, status="cancelled", **base),
        appt(id="5", customer_name=name, status=None, **base),
        appt(id="6", customer_name=name, optout_sms_v2=None, **base),
        Boom(appt(id="7", customer_name=name, **base)),
    ]
    caplog.set_level(logging.DEBUG)
    res = plan_reminders(appts, dub(2026, 10, 10, 10))
    assert res
    fmt = logging.Formatter()
    infos = [r for r in caplog.records if r.levelno == logging.INFO and "planned appointment" not in r.getMessage()]
    assert caplog.records and infos
    for rec in caplog.records:
        blob = rec.getMessage() + str(rec.args) + str(rec.msg) + fmt.format(rec)
        for secret in (email, phone, name, "secret.person"):
            assert secret not in blob
        assert rec.exc_info is None