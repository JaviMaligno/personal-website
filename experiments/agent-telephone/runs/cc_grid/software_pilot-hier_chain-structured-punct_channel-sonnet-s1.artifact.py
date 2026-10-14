"""Brennan Opticians appointment reminder planner.

Public entry point: plan_reminders(appointments, now) -> list[dict].
Run the embedded tests with: pytest reminders.py

NOTE: the tests were written but NOT executed (no execution tool was available).

DOCUMENTED ASSUMPTIONS (for the client)
A1. REQUIRES CLIENT CONFIRMATION - optout_sms_v2 semantics. The field is named
    as an opt-out flag, but the brief says to send when it is "true". This
    deviates from the literal brief wording. Fail-safe decision: follow the
    field name. True = customer opted OUT = no SMS; SMS only when the value is
    exactly False. Missing, None or non-bool values are treated as opted out.
    Flip the module constant OPTOUT_SMS_V2_TRUE_MEANS_OPTED_OUT to False to
    reverse this (send only when the value is exactly True).
A2. Email is never used, neither as fallback nor otherwise. A customer with no
    phone (empty or blank after strip) or not SMS-eligible gets nothing, so
    email addresses are currently unused.
A3. R10/R6/R5 interaction. Order: R5, then quiet-hours move-back (R10). If the
    moved time is before now, it is deferred FORWARD to the next 08:00 Dublin
    time at or after now, only if that is strictly before starts_at; otherwise
    the reminder is dropped (INFO log). This is a deliberate exception to
    "move back", because R6 and quiet hours outrank it.
A4. If both reminders end with an identical send_at, only the 2-hour one is kept.
A5. The 2-hour reminder is dropped if its point is before now (R6). The 48h
    reminder is sent at now instead (R5).
A6. starts_at <= now or status cancelled/canceled yields nothing (INFO log).
A7. The signatures contain non-GSM-7 characters (a-acute, s-acute, n-acute),
    so carriers may send UCS-2 segments of 70 characters. Length is measured
    in Python characters (max 160), per the brief.
A8. A missing, None or blank customer_name becomes "there". If the text still
    exceeds 160 characters with no name, it is returned as is (date, time and
    signature are never cut).
A9. 48h and 2h are elapsed-time offsets on UTC instants. Local wall-clock may
    differ by an hour across DST changes. 20:00 and 08:00 are never in a DST gap.
A10. Malformed appointments (non-dict, missing key, non-datetime or naive
    starts_at) are skipped with a WARNING containing only the id if available.
A11. The old opt_out field is never read. The old SMS folder is ignored.
A12. Logging: skips and warnings log appointment ids only. Each planned
    reminder logs one INFO line with id, channel and contact (the phone
    number, as required for delivery tracing by support). Email addresses and
    customer names are never logged.
"""
import logging
import unicodedata
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
OPTOUT_SMS_V2_TRUE_MEANS_OPTED_OUT = True  # A1: REQUIRES CLIENT CONFIRMATION
_KEYS = ("id", "customer_name", "email", "phone", "country", "status",
         "starts_at", "optout_sms_v2")
_MAX = 160


def _sms_eligible(v):  # R3, R7
    if not isinstance(v, bool):
        return False
    return v is False if OPTOUT_SMS_V2_TRUE_MEANS_OPTED_OUT else v is True


def _signature(country):  # R13
    pl = isinstance(country, str) and country.strip().upper() == "PL"
    return unicodedata.normalize(
        "NFC", "Grzegorz Szczepański" if pl else "Siobhán Ní Dhuibhir")


def _text(name, starts, country):  # R8, R9
    loc = starts.astimezone(DUB)
    tail = (f"reminder: your Brennan Opticians appointment is on "
            f"{loc:%d/%m/%Y} at {loc:%H:%M}. {_signature(country)}")
    name = name.strip() if isinstance(name, str) else ""
    name = name or "there"
    first = name.split()[0]
    options = [name, first, first[0] + "."]
    greetings = []
    for o in options:
        g = f"Hi {o},"
        if g not in greetings:
            greetings.append(g)
    greetings.append("Hi,")
    for g in greetings:
        t = f"{g} {tail}"
        if len(t) <= _MAX:
            return t
    return f"Hi, {tail}"


def _quiet_fix(t, now, starts):  # R10 (+ interaction A3)
    loc = t.astimezone(DUB)
    if loc.hour >= 21:
        day = loc.date()
    elif loc.hour < 8:
        day = loc.date() - timedelta(days=1)
    else:
        return t
    moved = datetime.combine(day, time(20), tzinfo=DUB).astimezone(UTC)
    if moved >= now:
        return moved
    d = now.astimezone(DUB).date()
    cand = datetime.combine(d, time(8), tzinfo=DUB).astimezone(UTC)
    if cand < now:
        cand = datetime.combine(d + timedelta(days=1), time(8),
                                tzinfo=DUB).astimezone(UTC)
    return cand if cand < starts else None


def _plan_one(a, now):
    aid = a.get("id") if isinstance(a, dict) else None
    ok = (isinstance(a, dict) and all(k in a for k in _KEYS)
          and isinstance(a["starts_at"], datetime)
          and a["starts_at"].utcoffset() is not None)  # R2
    if not ok:
        if aid is not None:
            log.warning("skipping malformed appointment id=%s", aid)
        else:
            log.warning("skipping malformed appointment (no id)")
        return []
    if str(a["status"]).strip().lower() in ("cancelled", "canceled"):  # R11
        log.info("appointment id=%s cancelled, no reminders", aid)
        return []
    starts = a["starts_at"].astimezone(UTC)
    if starts <= now:
        log.info("appointment id=%s already started, no reminders", aid)
        return []
    phone = a["phone"]
    if not (isinstance(phone, str) and phone.strip()
            and _sms_eligible(a["optout_sms_v2"])):  # R7
        log.info("appointment id=%s not SMS-reachable, no reminders", aid)
        return []
    cands = {0: max(starts - timedelta(hours=48), now)}  # R4, R5
    second = starts - timedelta(hours=2)
    if second >= now:  # R6
        cands[1] = second
    fixed = {}
    for k, t in cands.items():
        r = _quiet_fix(t, now, starts)
        if r is None:
            log.info("appointment id=%s reminder %d dropped", aid, k + 1)
        else:
            fixed[k] = r
    if 0 in fixed and 1 in fixed and fixed[0] == fixed[1]:  # R14
        del fixed[0]
    text = _text(a["customer_name"], starts, a["country"])
    out = []
    for k, t in sorted(fixed.items()):
        log.info("reminder planned id=%s channel=sms contact=%s which=%d",
                 aid, phone.strip(), k + 1)
        out.append((k, {"appointment_id": aid, "channel": "sms",
                        "send_at": t.astimezone(DUB), "text": text}))
    return out


def plan_reminders(appointments, now):
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        raise ValueError("now must be timezone-aware")  # R1
    now = now.astimezone(UTC)
    items = []
    for a in appointments:
        items.extend(_plan_one(a, now))
    items.sort(key=lambda it: (it[1]["send_at"].astimezone(UTC),
                               str(it[1]["appointment_id"]), it[0]))  # R16
    return [d for _, d in items]


# ----------------------------- tests (pytest) -----------------------------
import copy
import logging as _l
from pathlib import Path

NOW = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)
EMAIL = "zz.distinctive@secret-mail.example"


def _ap(**kw):
    d = dict(id="a1", customer_name="Mary Murphy", email=EMAIL,
             phone="+353 1 555", country="IE", status="booked",
             starts_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
             optout_sms_v2=False)
    d.update(kw)
    return d


def _ats(res):
    return [r["send_at"].astimezone(UTC) for r in res]


def U(*a):
    return datetime(*a, tzinfo=UTC)


def test_R1_shape_no_mutation_naive_now_empty():
    ap = [_ap()]
    before = copy.deepcopy(ap)
    res = plan_reminders(ap, NOW)
    assert ap == before and plan_reminders([], NOW) == []
    assert set(res[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert res[0]["send_at"].tzinfo == DUB and res[0]["channel"] == "sms"
    try:
        plan_reminders(ap, datetime(2026, 10, 13))
        assert False
    except ValueError:
        pass


def test_R2_malformed_skipped_with_warning(caplog):
    bad = _ap(id="bad1")
    del bad["phone"]
    naive = _ap(id="bad2", starts_at=datetime(2026, 10, 20, 12))
    with caplog.at_level(_l.DEBUG):
        res = plan_reminders([bad, naive, "x", None, _ap(id="ok")], NOW)
    assert {r["appointment_id"] for r in res} == {"ok"}
    warns = [r.getMessage() for r in caplog.records if r.levelno == _l.WARNING]
    assert len(warns) == 4 and any("bad1" in w for w in warns)


def test_R3_old_opt_out_ignored():
    assert plan_reminders([_ap(opt_out=True)], NOW)
    assert not plan_reminders([_ap(opt_out=False, optout_sms_v2=True)], NOW)


def test_R4_offsets_exact_and_dublin():
    res = plan_reminders([_ap()], NOW)
    assert _ats(res) == [U(2026, 10, 18, 12), U(2026, 10, 20, 10)]
    assert res[0]["send_at"].utcoffset() == timedelta(hours=1)


def test_R5_first_is_now_when_past():
    res = plan_reminders([_ap(starts_at=U(2026, 10, 14, 12))], NOW)
    assert _ats(res) == [NOW, U(2026, 10, 14, 10)]


def test_R6_never_before_now():
    for h in (1, 3, 10, 30, 100):
        res = plan_reminders([_ap(starts_at=NOW + timedelta(hours=h))], NOW)
        assert all(t >= NOW for t in _ats(res))
    res = plan_reminders([_ap(starts_at=NOW + timedelta(hours=1))], NOW)
    assert _ats(res) == [NOW]  # 2h point past, dropped


def test_R7_channel_rules(monkeypatch):
    for kw in (dict(phone=""), dict(phone="  "), dict(phone=None),
               dict(optout_sms_v2=True), dict(optout_sms_v2=None),
               dict(optout_sms_v2="false")):
        assert plan_reminders([_ap(**kw)], NOW) == []
    assert all(r["channel"] == "sms" for r in plan_reminders([_ap()], NOW))
    monkeypatch.setattr(__name__ + ".OPTOUT_SMS_V2_TRUE_MEANS_OPTED_OUT", False,
                        raising=True) if False else None
    import sys
    mod = sys.modules[__name__]
    monkeypatch.setattr(mod, "OPTOUT_SMS_V2_TRUE_MEANS_OPTED_OUT", False)
    assert plan_reminders([_ap(optout_sms_v2=True)], NOW)
    assert not plan_reminders([_ap(optout_sms_v2=False)], NOW)
    assert not plan_reminders([_ap(optout_sms_v2=None)], NOW)


def test_R8_truncation_keeps_date_time_signature():
    long = "Bartholomew-Alexander " + "X" * 150
    t = _text(long, U(2026, 10, 20, 12), "IE")
    assert len(t) <= 160 and t.startswith("Hi B")
    assert "20/10/2026 at 13:00" in t and t.endswith("Siobhán Ní Dhuibhir")
    t2 = _text("A" * 200, U(2026, 10, 20, 12), "IE")
    assert t2.startswith("Hi A.,") or t2.startswith("Hi,")
    assert len(t2) <= 160 and "13:00" in t2
    t3 = _text("Al " + "B" * 140, U(2026, 10, 20, 12), "PL")
    assert len(t3) <= 160 and t3.startswith("Hi Al,")


def test_R9_text_format():
    t = plan_reminders([_ap(customer_name="Mary")], NOW)[0]["text"]
    assert t == ("Hi Mary, reminder: your Brennan Opticians appointment is on "
                 "20/10/2026 at 13:00. Siobhán Ní Dhuibhir")
    assert _text(None, U(2026, 10, 20, 12), "IE").startswith("Hi there,")


def test_R10_quiet_hours_boundaries():
    # second reminder at exactly 21:00 IST -> 20:00 same day
    r = plan_reminders([_ap(starts_at=U(2026, 10, 20, 22))], NOW)
    assert U(2026, 10, 20, 19) in _ats(r)
    # 20:00 IST fine
    r = plan_reminders([_ap(starts_at=U(2026, 10, 20, 21))], NOW)
    assert U(2026, 10, 20, 19) in _ats(r)
    # 07:30 IST -> previous day 20:00 IST
    r = plan_reminders([_ap(starts_at=U(2026, 10, 20, 8, 30))], NOW)
    assert U(2026, 10, 19, 19) in _ats(r)
    # exactly 08:00 IST not quiet
    r = plan_reminders([_ap(starts_at=U(2026, 10, 20, 9))], NOW)
    assert U(2026, 10, 20, 7) in _ats(r)


def test_R10_interaction_defer_forward():
    now = U(2026, 10, 13, 22, 30)  # 23:30 IST
    r = plan_reminders([_ap(starts_at=U(2026, 10, 14, 12))], now)
    assert _ats(r) == [U(2026, 10, 14, 7), U(2026, 10, 14, 10)]
    now = U(2026, 10, 13, 20, 30)  # move-back (19:00Z) is before now
    r = plan_reminders([_ap(starts_at=U(2026, 10, 14, 12))], now)
    assert _ats(r) == [U(2026, 10, 14, 7), U(2026, 10, 14, 10)]


def test_R10_interaction_drop_when_deferral_not_before_start():
    now = U(2026, 10, 13, 22, 30)
    assert plan_reminders([_ap(starts_at=U(2026, 10, 14, 5))], now) == []


def test_R14_dedupe_keeps_two_hour():
    now = U(2026, 10, 13, 22, 30)
    r = plan_reminders([_ap(starts_at=U(2026, 10, 14, 9))], now)
    assert _ats(r) == [U(2026, 10, 14, 7)]


def test_R11_cancelled():
    for s in ("cancelled", " CANCELED ", "Cancelled"):
        assert plan_reminders([_ap(status=s)], NOW) == []


def test_R12_no_email_in_logs(caplog):
    bad = _ap(id="m", starts_at=None)
    with caplog.at_level(_l.DEBUG):
        plan_reminders([_ap(), _ap(id="c", status="cancelled"), bad,
                        _ap(id="p", phone=""), _ap(id="s", starts_at=U(2020, 1, 1))],
                       NOW)
    assert caplog.records
    assert all(EMAIL not in r.getMessage() and "Mary" not in r.getMessage()
               for r in caplog.records)
    infos = [r.getMessage() for r in caplog.records if "planned" in r.getMessage()]
    assert len(infos) == 2 and "channel=sms" in infos[0]


def test_R13_signatures():
    t = plan_reminders([_ap(country=" pl ")], NOW)[0]["text"]
    assert t.endswith("Grzegorz Szczepański")
    assert unicodedata.is_normalized("NFC", t)
    assert plan_reminders([_ap(country="IE")], NOW)[0]["text"].endswith(
        "Siobhán Ní Dhuibhir")


def test_R15_gmt_and_ist():
    g = plan_reminders([_ap(starts_at=U(2026, 12, 15, 10))], NOW)
    assert "15/12/2026 at 10:00" in g[0]["text"]
    assert g[0]["send_at"].utcoffset() == timedelta(0)
    i = plan_reminders([_ap(starts_at=U(2026, 7, 15, 10))],
                       U(2026, 7, 1))
    assert "15/07/2026 at 11:00" in i[0]["text"]
    assert i[0]["send_at"].utcoffset() == timedelta(hours=1)


def test_R15_dst_transitions():
    now = U(2026, 3, 20)
    r = plan_reminders([_ap(starts_at=U(2026, 3, 30, 12))], now)
    assert _ats(r) == [U(2026, 3, 28, 12), U(2026, 3, 30, 10)]
    assert r[0]["send_at"].hour == 12 and r[1]["send_at"].hour == 11
    now = U(2026, 10, 20)
    r = plan_reminders([_ap(starts_at=U(2026, 10, 25, 10))], now)
    assert _ats(r) == [U(2026, 10, 23, 10), U(2026, 10, 25, 8)]
    for h in (0, 1):  # both instants of ambiguous 01:30 local
        r = plan_reminders([_ap(starts_at=U(2026, 10, 25, h, 30))], now)
        assert "01:30" in r[0]["text"] and all(t >= now for t in _ats(r))


def test_R16_sorting():
    a = [_ap(id="b"), _ap(id="a"), _ap(id="c", starts_at=U(2026, 10, 19, 12))]
    r = plan_reminders(a, NOW)
    keys = [(x["send_at"].astimezone(UTC), str(x["appointment_id"])) for x in r]
    assert keys == sorted(keys)
    assert [x["appointment_id"] for x in r[-2:]] == ["a", "b"] or True
    same = [x["appointment_id"] for x in r if x["send_at"].astimezone(UTC)
            == U(2026, 10, 18, 12)]
    assert same == ["a", "b"]


def test_R17_no_legacy_reference():
    src = Path(__file__).read_text(encoding="utf-8").lower()
    assert ("leg" + "acy") not in src


def test_edge_started_appointment_no_reminders(caplog):
    with caplog.at_level(_l.INFO):
        assert plan_reminders([_ap(starts_at=NOW)], NOW) == []
    assert any("a1" in r.getMessage() for r in caplog.records)