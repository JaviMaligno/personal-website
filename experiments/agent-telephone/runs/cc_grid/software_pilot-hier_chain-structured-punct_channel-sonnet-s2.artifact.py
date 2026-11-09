# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-dqghe88i/reminders.py =====
"""Brennan Opticians appointment reminders (R1-R22). Standard library only.

Assumptions (documented per the requirements):
* R9: optout_sms_v2 == True means the customer HAS OPTED OUT. SMS is allowed only
  when the flag is exactly False. A missing or None flag (consent unknown) means no
  SMS. The semantics live in one place, _sms_allowed(), so they can be flipped.
* R4: the legacy "opt_out" field is never read.
* R10: no email fallback. The module only ever produces channel "sms" and never
  reads or uses the email field for sending. "email" remains in the R2 channel
  vocabulary for schema compatibility only. No SMS possible means no reminder.
* R13: quiet hours are 21:00 <= local < 08:00 (Europe/Dublin). A time inside the
  window moves back to the preceding 20:00. If that is already in the past, the
  reminder is deferred FORWARD to the next 08:00 if that is before starts_at,
  otherwise it is dropped (logged at INFO). The forward deferral is an assumption.
* Collapse rule: if the 2h point is already <= now (appointment still in the
  future), only the 2h-style reminder is emitted, so the customer does not get two
  messages at once. If both reminders end up at the same send_at, only the 2h one
  is kept (R18).
* R14: only status "cancelled" (case-insensitive, stripped) suppresses reminders.
  All other statuses are treated as active (open question for the client).
* R3: the seven keys id, customer_name, email, phone, country, status, starts_at are
  required; optout_sms_v2 is optional (missing means opted out, see R9).
* Logging (R15 plus house rule): one INFO line per planned reminder with the
  appointment id, channel and contact. The contact is the SMS phone number. The
  email address, whole appointment dicts and the customer name are never logged.
"""
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIGNATURE = "Siobh\u00e1n N\u00ed Dhuibhir"            # R16
SIGNATURE_PL = "Grzegorz Szczepa\u0144ski"             # R17
MAX_SMS_LEN = 160                                      # R12
REQUIRED = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")
TEMPLATES = {  # R5: both keep date and HH:MM
    "48h": "{g} reminder of your Brennan Opticians appointment on {d} at {t}. {s}",
    "2h": "{g} your Brennan Opticians appointment is coming up on {d} at {t}. {s}",
}
SLOT_ORDER = {"48h": 0, "2h": 1}


def _safe_id(appt):
    i = appt.get("id") if isinstance(appt, dict) else None
    return i if isinstance(i, (str, int)) else "unknown"


def _check(appt):
    """Raise ValueError if the appointment is malformed (R3)."""
    if not isinstance(appt, dict) or any(k not in appt for k in REQUIRED):
        raise ValueError("missing key")
    if not isinstance(appt["id"], (str, int)) or isinstance(appt["id"], bool):
        raise ValueError("bad id")
    for k in ("customer_name", "email", "phone", "country"):
        if appt[k] is not None and not isinstance(appt[k], str):
            raise ValueError("bad " + k)
    if not isinstance(appt["status"], str):
        raise ValueError("bad status")
    s = appt["starts_at"]
    if not isinstance(s, datetime) or s.utcoffset() is None:
        raise ValueError("bad starts_at")


def _sms_allowed(appt):
    """R9: True only if the customer has NOT opted out (flag exactly False)."""
    return appt.get("optout_sms_v2") is False


def _signature(country):
    return SIGNATURE_PL if (country or "").strip().upper() == "PL" else SIGNATURE


def _in_quiet(dt):
    h = dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _at_local(day, hour):
    return datetime.combine(day, time(hour, 0), tzinfo=DUBLIN)  # wall-clock build


def _to_quiet_safe(dt):
    """Move a quiet-hours time back to the immediately preceding 20:00 (R13)."""
    loc = dt.astimezone(DUBLIN)
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    return _at_local(day, 20)


def _next_morning(dt):
    """Next 08:00 local after a quiet-hours time."""
    loc = dt.astimezone(DUBLIN)
    day = loc.date() if loc.hour < 8 else loc.date() + timedelta(days=1)
    return _at_local(day, 8)


def _name_options(name):
    """R12: full name, truncated, first name, initial, then no name."""
    name = (name or "").strip()
    if name:
        yield name
        for k in range(len(name) - 1, 1, -1):
            yield name[:k].rstrip() + "\u2026"
        yield name.split()[0]
        yield name[0] + "."
    yield ""


def _build_text(slot, name, starts_at, signature):
    loc = starts_at.astimezone(DUBLIN)
    date = f"{loc.day:02d} {MONTHS[loc.month - 1]} {loc.year}"
    hhmm = f"{loc.hour:02d}:{loc.minute:02d}"
    for n in _name_options(name):
        g = f"Hi {n}," if n else "Hi,"
        text = TEMPLATES[slot].format(g=g, d=date, t=hhmm, s=signature)
        if len(text) <= MAX_SMS_LEN:
            assert len(text) <= MAX_SMS_LEN
            return text
    raise ValueError("text cannot fit in 160 characters")


def _resolve(nominal, now, start, aid, slot):
    """R7, R8, R13 steps b-d. Returns the final send time or None."""
    cand = now if nominal < now else nominal
    if _in_quiet(cand):
        moved = _to_quiet_safe(cand)
        if moved >= now:
            cand = moved
        else:
            cand = _next_morning(cand)
            if cand >= start:
                logger.info("Dropping %s reminder for appointment %s: quiet hours and "
                            "next 08:00 is not before the appointment", slot, aid)
                return None
    if not (now <= cand < start) or _in_quiet(cand):  # defensive (R8)
        return None
    return cand.astimezone(DUBLIN)


def _plan_one(appt, now):
    aid, start = appt["id"], appt["starts_at"]
    if appt["status"].strip().lower() == "cancelled":
        logger.debug("Appointment %s: cancelled, no reminders", aid)
        return []
    if start <= now:
        logger.debug("Appointment %s: already started, no reminders", aid)
        return []
    phone = (appt["phone"] or "").strip()
    if not phone:
        logger.debug("Appointment %s: no SMS possible, no phone", aid)
        return []
    if not _sms_allowed(appt):
        logger.debug("Appointment %s: no SMS possible, opted out or consent unknown", aid)
        return []
    t48, t2 = start - timedelta(hours=48), start - timedelta(hours=2)
    slots = [("2h", t2)] if t2 <= now else [("48h", t48), ("2h", t2)]  # collapse rule
    times = {}
    for slot, nominal in slots:
        send = _resolve(nominal, now, start, aid, slot)
        if send is not None:
            times[slot] = send
    if len(times) == 2 and times["48h"] == times["2h"]:
        del times["48h"]  # R18: keep the 2h one
    sig = _signature(appt["country"])
    out = []
    for slot, send in times.items():
        text = _build_text(slot, appt["customer_name"], start, sig)
        logger.info("Planned reminder: appointment=%s slot=%s channel=sms contact=%s send_at=%s",
                    aid, slot, phone, send.isoformat())
        out.append(({"appointment_id": aid, "channel": "sms",
                     "send_at": send, "text": text}, SLOT_ORDER[slot]))
    return out


def plan_reminders(appointments, now):
    """Return the planned SMS reminders sorted by send_at (R1, R20)."""
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for appt in appointments:
        try:
            _check(appt)
        except ValueError:
            logger.warning("Skipping malformed appointment id=%s", _safe_id(appt))
            continue
        planned.extend(_plan_one(appt, now))
    planned.sort(key=lambda p: (p[0]["send_at"], str(p[0]["appointment_id"]), p[1]))
    result = [p[0] for p in planned]
    logger.debug("Planned %d reminders for %d appointments", len(result), len(appointments))
    return result


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-dqghe88i/test_reminders.py =====
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


def D(*a):
    return datetime(*a, tzinfo=DUB)


START = D(2026, 10, 14, 14, 30)
NOW = D(2026, 10, 10, 12, 0)


def mk(**o):
    a = dict(id="A1", customer_name="Mary Murphy", email="x@example.com",
             phone="+353851234567", country="IE", status="booked",
             starts_at=START, optout_sms_v2=False)
    a.update(o)
    return a


def test_r1_r2_happy_path_two_sorted():
    res = plan_reminders([mk()], NOW)
    assert [r["send_at"] for r in res] == [D(2026, 10, 12, 14, 30), D(2026, 10, 14, 12, 30)]
    assert all(set(r) == {"appointment_id", "channel", "send_at", "text"} for r in res)
    assert all(r["channel"] == "sms" and r["send_at"].tzinfo == DUB for r in res)
    assert all("14 Oct 2026 at 14:30" in r["text"] and r["text"].endswith(SIG) for r in res)
    assert res[0]["text"].startswith("Hi Mary Murphy,")


def test_r20_sorted_across_appointments():
    res = plan_reminders([mk(id="B", starts_at=START + timedelta(days=1)), mk(id="A")], NOW)
    keys = [r["send_at"] for r in res]
    assert keys == sorted(keys)


def test_r7_first_reminder_at_now_when_48h_passed():
    now = D(2026, 10, 13, 10, 0)
    res = plan_reminders([mk()], now)
    assert [r["send_at"] for r in res] == [now, D(2026, 10, 14, 12, 30)]


@pytest.mark.parametrize("now", [D(2026, 10, 9, 9, 0), D(2026, 10, 12, 15, 0),
                                 D(2026, 10, 13, 22, 0), D(2026, 10, 14, 3, 0),
                                 D(2026, 10, 14, 12, 30), D(2026, 10, 14, 13, 45)])
def test_r8_nothing_in_the_past_or_after_start(now):
    for r in plan_reminders([mk()], now):
        assert now <= r["send_at"] < START


def test_r8_started_appointment_gives_nothing():
    assert plan_reminders([mk()], START) == []
    assert plan_reminders([mk()], START + timedelta(hours=1)) == []


def test_r9_optout_true_gives_nothing():
    assert plan_reminders([mk(optout_sms_v2=True)], NOW) == []


def test_r9_optout_false_with_phone_gives_sms():
    assert {r["channel"] for r in plan_reminders([mk(optout_sms_v2=False)], NOW)} == {"sms"}


def test_r9_missing_or_none_flag_gives_nothing():
    a = mk()
    del a["optout_sms_v2"]
    assert plan_reminders([a, mk(id="B", optout_sms_v2=None)], NOW) == []


def test_r4_old_opt_out_field_ignored():
    assert len(plan_reminders([mk(opt_out=True, optout_sms_v2=False)], NOW)) == 2
    assert plan_reminders([mk(opt_out=False, optout_sms_v2=True)], NOW) == []


@pytest.mark.parametrize("phone", ["", "   ", None])
def test_r10_no_phone_gives_nothing_and_email_unused(phone):
    res = plan_reminders([mk(phone=phone, email="someone@example.com")], NOW)
    assert res == []


def test_r10_never_email_channel():
    assert all(r["channel"] != "email" for r in plan_reminders([mk(), mk(id="B", phone="")], NOW))


def test_r14_cancelled_gives_nothing():
    assert plan_reminders([mk(status=" Cancelled ")], NOW) == []
    assert len(plan_reminders([mk(status="confirmed")], NOW)) == 2


@pytest.mark.parametrize("target,expected", [
    (D(2026, 10, 12, 21, 0), D(2026, 10, 12, 20, 0)),
    (D(2026, 10, 12, 23, 30), D(2026, 10, 12, 20, 0)),
    (D(2026, 10, 12, 3, 0), D(2026, 10, 11, 20, 0)),
    (D(2026, 10, 12, 7, 59), D(2026, 10, 11, 20, 0)),
    (D(2026, 10, 12, 8, 0), D(2026, 10, 12, 8, 0)),
])
def test_r13_quiet_hours_moves(target, expected):
    res = plan_reminders([mk(starts_at=target + timedelta(hours=48))], D(2026, 10, 8, 12, 0))
    assert res[0]["send_at"] == expected
    assert all(not (r["send_at"].hour >= 21 or r["send_at"].hour < 8) for r in res)


def test_r13_r8_defer_forward_to_0800():
    res = plan_reminders([mk(starts_at=D(2026, 10, 12, 12, 0))], D(2026, 10, 10, 22, 0))
    assert [r["send_at"] for r in res] == [D(2026, 10, 11, 8, 0), D(2026, 10, 12, 10, 0)]


def test_r13_r8_dropped_when_0800_not_before_start(caplog):
    with caplog.at_level(logging.INFO):
        res = plan_reminders([mk(starts_at=D(2026, 10, 11, 7, 0))], D(2026, 10, 10, 22, 0))
    assert res == []
    assert "A1" in caplog.text and "Dropping" in caplog.text


def test_collapse_rule_only_2h_style_at_now():
    now = D(2026, 10, 14, 13, 0)
    res = plan_reminders([mk()], now)
    assert len(res) == 1 and res[0]["send_at"] == now
    assert "coming up" in res[0]["text"]


def test_identical_send_at_keeps_only_one():
    res = plan_reminders([mk(starts_at=D(2026, 10, 11, 8, 30))], D(2026, 10, 10, 22, 0))
    assert len(res) == 1 and res[0]["send_at"] == D(2026, 10, 11, 8, 0)
    assert "coming up" in res[0]["text"]


def test_r6_r19_dst_spring_2026_03_29_utc_input():
    start = datetime(2026, 3, 29, 14, 30, tzinfo=UTC)  # 15:30 in Dublin (BST)
    res = plan_reminders([mk(starts_at=start)], datetime(2026, 3, 20, 12, 0, tzinfo=UTC))
    assert res[0]["send_at"] == datetime(2026, 3, 27, 14, 30, tzinfo=UTC)  # absolute 48h
    assert res[0]["send_at"].hour == 14 and res[1]["send_at"].hour == 13
    assert all("29 Mar 2026 at 15:30" in r["text"] for r in res)


def test_r19_dst_autumn_2026_10_25_date_differs_from_utc():
    start = datetime(2026, 10, 24, 23, 30, tzinfo=UTC)  # 25 Oct 00:30 in Dublin (BST)
    res = plan_reminders([mk(starts_at=start)], datetime(2026, 10, 20, 12, 0, tzinfo=UTC))
    assert all("25 Oct 2026 at 00:30" in r["text"] for r in res)
    assert [r["send_at"] for r in res] == [D(2026, 10, 22, 20, 0), D(2026, 10, 24, 20, 0)]


def test_r6_dst_autumn_absolute_48h():
    start = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)  # 12:00 GMT
    res = plan_reminders([mk(starts_at=start)], datetime(2026, 10, 20, 12, 0, tzinfo=UTC))
    assert res[0]["send_at"] == datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
    assert res[0]["send_at"].hour == 13  # BST locally


def test_r16_r17_signatures_and_accents():
    ie = plan_reminders([mk()], NOW)[0]["text"]
    pl = plan_reminders([mk(country=" pl ")], NOW)[0]["text"]
    assert ie.endswith("Siobh\u00e1n N\u00ed Dhuibhir") and "\u00e1" in ie and "\u00cd" not in ie
    assert "Siobh\u00e1n N\u00ed Dhuibhir" == SIG and "\u00ed" in SIG
    assert pl.endswith("Grzegorz Szczepa\u0144ski") and SIG not in pl


@pytest.mark.parametrize("country,sig", [("IE", SIG), ("PL", SIG_PL)])
def test_r12_r22_long_name_keeps_signature_date_time(country, sig):
    res = plan_reminders([mk(customer_name="Bartholomew " * 30, country=country)], NOW)
    for r in res:
        t = r["text"]
        assert len(t) <= 160 and t.endswith(sig) and "14 Oct 2026" in t and "14:30" in t


@pytest.mark.parametrize("name", [None, "", "   "])
def test_r12_missing_name(name):
    t = plan_reminders([mk(customer_name=name)], NOW)[0]["text"]
    assert t.startswith("Hi, ") and t.endswith(SIG)


def test_r12_short_name_untouched_long_name_shortened():
    t = plan_reminders([mk(customer_name="Zed " + "Q" * 150)], NOW)[0]["text"]
    assert len(t) <= 160 and t.startswith("Hi Zed ")


def test_r1_naive_now_raises():
    with pytest.raises(ValueError):
        plan_reminders([mk()], datetime(2026, 10, 10, 12, 0))


def test_r3_malformed_skipped_and_batch_continues(caplog):
    bad_missing = mk(id="M")
    del bad_missing["phone"]
    bad_naive = mk(id="N", starts_at=datetime(2026, 10, 14, 14, 30))
    bad_type = mk(id="T", status=5)
    with caplog.at_level(logging.WARNING):
        res = plan_reminders([bad_missing, bad_naive, "junk", bad_type, mk(id="OK")], NOW)
    assert {r["appointment_id"] for r in res} == {"OK"}
    warns = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warns) == 4 and any("id=M" in w for w in warns)


def test_r1_inputs_not_mutated():
    appts = [mk(), mk(id="B", optout_sms_v2=True)]
    before = copy.deepcopy(appts)
    plan_reminders(appts, NOW)
    assert appts == before


def test_r15_email_never_logged(caplog):
    email = "secret.person@distinct-mail.example"
    appts = [mk(email=email), mk(id="O", email=email, optout_sms_v2=True),
             mk(id="X", email=email, starts_at=datetime(2026, 10, 14, 14, 30)),
             mk(id="C", email=email, status="cancelled"), mk(id="P", email=email, phone=None),
             mk(id="W", email=email, country=7)]
    with caplog.at_level(logging.DEBUG):
        plan_reminders(appts, NOW)
    assert caplog.records
    assert email not in caplog.text
    assert all(email not in str(r.getMessage()) and email not in str(r.args) for r in caplog.records)


def test_house_rule_info_line_per_reminder(caplog):
    with caplog.at_level(logging.INFO):
        plan_reminders([mk()], NOW)
    lines = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert len(lines) == 2
    assert all("A1" in l and "sms" in l and "+353851234567" in l for l in lines)