"""Brennan Opticians appointment reminder planner.

Save as brennan_reminders.py. Tests are in the same file and run with:
    pytest brennan_reminders.py
They were NOT executed: this agent had no tools, so no test results exist yet.

Single public entry point: plan_reminders(appointments, now). Pure and deterministic.

R18: There is no idempotency or memory. Calling it again with the same input
returns the same plan, and the caller must de-duplicate.
R19: No email subject is produced. Downstream supplies it.

Implementation notes and deviations to review:
- The house rule asks for an INFO line per reminder with channel and contact.
  R11 forbids logging email, phone and name. The log line therefore carries
  appointment_id, slot, channel and send_at, but never the contact value.
  Support can look the contact up by appointment_id.
- optout_sms_v2 is optional as a key (R3: missing means opted out). All other
  fields are required keys (R2). Only a literal False opts in to SMS.

Open-point defaults implemented (unconfirmed with the client):
- The 2h reminder is the second reminder, and the offsets are constants.
- Quiet hours may mean no reminder at all.
- The date is DD/MM/YYYY, the language is English only, and PL customers get Dublin time.
- A missing opt-out means email only.
- Statuses other than "cancelled" are active.
- Accented signatures make an SMS UCS-2 (70 chars/segment), so 160 chars may be about 3 segments.
"""
import copy
import logging
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START = time(21, 0)      # inclusive
QUIET_END = time(8, 0)         # exclusive
QUIET_FALLBACK = time(20, 0)
SMS_MAX_CHARS = 160
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"
PL_COUNTRY = "PL"
CANCELLED_STATUS = "cancelled"
DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"
GREETING_TEMPLATE = "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {time}. {signature}"
PLAIN_TEMPLATE = "Reminder of your Brennan Opticians appointment on {date} at {time}. {signature}"
REQUIRED_FIELDS = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")

logger = logging.getLogger(__name__)


def _has(value):
    return isinstance(value, str) and bool(value.strip())


def _is_quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _move_back(t):
    local = t.astimezone(DUBLIN)
    day = local.date() if local.time() >= QUIET_START else local.date() - timedelta(days=1)
    return datetime.combine(day, QUIET_FALLBACK, tzinfo=DUBLIN)


def _move_forward(t):
    local = t.astimezone(DUBLIN)
    day = local.date() if local.time() < QUIET_END else local.date() + timedelta(days=1)
    return datetime.combine(day, QUIET_END, tzinfo=DUBLIN)


def _adjust(starts_utc, offset, now):
    """R17 steps 1-4 for one reminder. Returns a Dublin datetime or None."""
    t = starts_utc - offset          # UTC arithmetic = elapsed time
    clamped = False
    if t < now:
        t, clamped = now, True
    if _is_quiet(t.astimezone(DUBLIN)):
        if clamped:
            t = _move_forward(t)
        else:
            t = _move_back(t)
            if t < now:
                t = _move_forward(t)
    if t >= starts_utc:
        return None
    return t.astimezone(DUBLIN)


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _name_options(name):
    tokens = _nfc(name or "").split() if isinstance(name, str) else []
    if not tokens:
        return [""]
    opts = [" ".join(tokens)]
    if len(tokens) > 1:
        opts.append(f"{tokens[0]} {tokens[-1][0]}.")
    opts.append(tokens[0])
    opts.append("".join(t[0].upper() for t in tokens))
    opts.append("")
    return opts


def _compose(name_part, local_start, signature):
    d, t = local_start.strftime(DATE_FORMAT), local_start.strftime(TIME_FORMAT)
    if name_part:
        text = GREETING_TEMPLATE.format(name=name_part, date=d, time=t, signature=signature)
    else:
        text = PLAIN_TEMPLATE.format(date=d, time=t, signature=signature)
    return _nfc(text)


def _build_text(name, local_start, signature, channel):
    options = _name_options(name)
    if channel == "email":
        return _compose(options[0], local_start, signature)
    for opt in options:
        text = _compose(opt, local_start, signature)
        if len(text) <= SMS_MAX_CHARS:
            return text
    return _compose("", local_start, signature)


def _skip(appt_id, reason):
    logger.info("appointment_id=%s skipped reason=%s", appt_id, reason)


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for index, appt in enumerate(appointments):
        if not isinstance(appt, dict):
            _skip("unknown", "malformed_not_a_dict")
            continue
        appt_id = appt.get("id", "unknown")
        if any(f not in appt for f in REQUIRED_FIELDS):
            _skip(appt_id, "malformed_missing_field")
            continue
        starts = appt["starts_at"]
        if not isinstance(starts, datetime) or starts.tzinfo is None or starts.utcoffset() is None:
            _skip(appt_id, "malformed_starts_at")
            continue
        status = appt["status"]
        if not isinstance(status, str):
            _skip(appt_id, "malformed_status")
            continue
        if status.strip().lower() == CANCELLED_STATUS:
            _skip(appt_id, "cancelled")
            continue
        if starts <= now:
            _skip(appt_id, "not_in_future")
            continue
        if _has(appt["phone"]) and appt.get("optout_sms_v2") is False:
            channel = "sms"
        elif _has(appt["email"]):
            channel = "email"
        else:
            _skip(appt_id, "no_contact")
            continue
        starts_utc = starts.astimezone(timezone.utc)
        second = _adjust(starts_utc, SECOND_OFFSET, now)
        first = _adjust(starts_utc, FIRST_OFFSET, now)
        if first is not None and second is not None and first >= second:
            first = None
        country = appt["country"]
        pl = isinstance(country, str) and country.strip().upper() == PL_COUNTRY
        signature = PL_SIGNATURE if pl else DEFAULT_SIGNATURE
        local_start = starts.astimezone(DUBLIN)
        text = _build_text(appt["customer_name"], local_start, signature, channel)
        for order, slot, when in ((0, "2h", second), (1, "48h", first)):
            if when is None:
                continue
            planned.append((when, index, order, {
                "appointment_id": appt_id, "channel": channel,
                "send_at": when, "text": text}))
            logger.info("reminder planned appointment_id=%s slot=%s channel=%s send_at=%s",
                        appt_id, slot, channel, when.isoformat())
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    return [p[3] for p in planned]


# ----------------------------------------------------------------- tests ---
SECRET_EMAIL = "zz.unique.secret@example.com"


def _dt(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def _appt(starts, **kw):
    a = {"id": "A1", "customer_name": "Ann Byrne", "email": SECRET_EMAIL,
         "phone": "0851234567", "country": "IE", "status": "booked",
         "starts_at": starts, "optout_sms_v2": False}
    a.update(kw)
    return a


NOW = _dt(2026, 6, 1, 10)


def _plan(starts, now=NOW, **kw):
    return plan_reminders([_appt(starts, **kw)], now)


def test_basic_two_reminders_and_shape():
    res = _plan(_dt(2026, 6, 10, 14))
    assert [r["send_at"] for r in res] == [_dt(2026, 6, 8, 14), _dt(2026, 6, 10, 12)]
    for r in res:
        assert set(r) == {"appointment_id", "channel", "send_at", "text"}
        assert r["channel"] == "sms"
        assert r["send_at"].tzinfo.key == "Europe/Dublin"
        assert "10/06/2026 at 14:00" in r["text"]
        assert "48 hours" not in r["text"] and "2 hours" not in r["text"]
        assert r["text"].endswith("Siobhán Ní Dhuibhir")
        assert r["text"].startswith("Hi Ann Byrne, reminder of your Brennan Opticians")
    assert res == _plan(_dt(2026, 6, 10, 14))


def test_optout_reads_only_v2():
    r = _plan(_dt(2026, 6, 10, 14), opt_out=False, optout_sms_v2=True)
    assert {x["channel"] for x in r} == {"email"}
    r = _plan(_dt(2026, 6, 10, 14), opt_out=True, optout_sms_v2=False)
    assert {x["channel"] for x in r} == {"sms"}
    a = _appt(_dt(2026, 6, 10, 14), opt_out=False)
    del a["optout_sms_v2"]
    assert {x["channel"] for x in plan_reminders([a], NOW)} == {"email"}
    assert {x["channel"] for x in _plan(_dt(2026, 6, 10, 14), optout_sms_v2=None)} == {"email"}


def test_channel_fallbacks():
    s = _dt(2026, 6, 10, 14)
    assert {x["channel"] for x in _plan(s, phone="  ")} == {"email"}
    assert _plan(s, optout_sms_v2=True, email="") == []
    assert _plan(s, phone=None, email=None) == []


def test_empty_and_now_validation():
    assert plan_reminders([], NOW) == []
    for bad in (datetime(2026, 6, 1, 10), "2026-06-01", None):
        try:
            plan_reminders([], bad)
            assert False
        except ValueError:
            pass


def test_malformed_skipped():
    good = _appt(_dt(2026, 6, 10, 14), id="G")
    naive = _appt(datetime(2026, 6, 10, 14), id="N")
    missing = _appt(_dt(2026, 6, 10, 14), id="M")
    del missing["phone"]
    res = plan_reminders([naive, missing, good], NOW)
    assert {r["appointment_id"] for r in res} == {"G"}


def test_cancelled_and_other_status():
    s = _dt(2026, 6, 10, 14)
    assert _plan(s, status=" Cancelled ") == []
    assert len(_plan(s, status="rescheduled")) == 2


def test_boundaries_now():
    now = _dt(2026, 6, 1, 12)
    res = _plan(now + timedelta(hours=48), now=now)
    assert res[0]["send_at"] == now and len(res) == 2
    assert _plan(now, now=now) == []
    assert _plan(now - timedelta(hours=1), now=now) == []


def test_quiet_boundaries():
    res = _plan(_dt(2026, 6, 10, 23))          # 2h at exactly 21:00 is quiet
    assert res[-1]["send_at"] == _dt(2026, 6, 10, 20)
    res = _plan(_dt(2026, 6, 10, 10))          # 2h at exactly 08:00 allowed
    assert res[-1]["send_at"] == _dt(2026, 6, 10, 8)
    assert res[0]["send_at"] == _dt(2026, 6, 8, 10)
    res = _plan(_dt(2026, 6, 10, 0, 30))       # 22:30 -> 20:00 same day
    assert res[-1]["send_at"] == _dt(2026, 6, 9, 20)
    res = _plan(_dt(2026, 6, 10, 5))           # 03:00 -> 20:00 previous day
    assert res[-1]["send_at"] == _dt(2026, 6, 9, 20)


def test_r17_examples():
    now = _dt(2026, 6, 1, 23)
    res = _plan(now + timedelta(hours=30), now=now)
    assert res[0]["send_at"] == _dt(2026, 6, 2, 8)
    now = _dt(2026, 6, 1, 14)
    res = _plan(now + timedelta(hours=1), now=now)
    assert len(res) == 1 and res[0]["send_at"] == now
    now = _dt(2026, 6, 1, 23)
    assert _plan(now + timedelta(hours=1), now=now) == []


def test_dst():
    now = _dt(2026, 3, 1, 9)
    res = _plan(_dt(2026, 3, 30, 12), now=now)       # spring forward on 29 March
    assert res[0]["send_at"] == _dt(2026, 3, 28, 11)
    assert res[-1]["send_at"] == _dt(2026, 3, 30, 10)
    now = _dt(2026, 10, 1, 9)
    res = _plan(_dt(2026, 10, 26, 12), now=now)      # fall back on 25 October
    assert res[0]["send_at"] == _dt(2026, 10, 24, 13)
    assert res[-1]["send_at"] == _dt(2026, 10, 26, 10)


def test_sort_and_ties():
    s = _dt(2026, 6, 10, 14)
    res = plan_reminders([_appt(s, id="a1"), _appt(s, id="a2")], NOW)
    assert [r["appointment_id"] for r in res] == ["a1", "a2", "a1", "a2"]
    res = plan_reminders([_appt(_dt(2026, 6, 12, 14), id="late"), _appt(s, id="early")], NOW)
    assert res == sorted(res, key=lambda r: r["send_at"])


def test_signatures():
    s = _dt(2026, 6, 10, 14)
    assert _plan(s, country=" pl ")[0]["text"].endswith("Grzegorz Szczepański")
    for c in (None, "FR", ""):
        assert _plan(s, country=c)[0]["text"].endswith("Siobhán Ní Dhuibhir")


def test_sms_shortening_steps():
    s = _dt(2026, 6, 10, 14)
    probe = _plan(s, customer_name="N")[0]["text"]
    fit = SMS_MAX_CHARS - (len(probe) - 1)

    def check(name, expected_start):
        t = _plan(s, customer_name=name)[0]["text"]
        assert len(t) <= SMS_MAX_CHARS
        assert "10/06/2026" in t and "14:00" in t and t.endswith("Siobhán Ní Dhuibhir")
        assert t.startswith(expected_start)
        return t

    check("Ann Byrne", "Hi Ann Byrne, ")
    check("F" * 10 + " " + "L" * fit, "Hi " + "F" * 10 + " L., ")
    check("F" * (fit - 1) + " L", "Hi " + "F" * (fit - 1) + ", ")
    check("A" * (fit + 1) + " B" * 3, "Hi AB" + "B" * 2 + ", ")
    t = check(" ".join(["A" * (fit + 1)] + ["B"] * (fit + 1)), "Reminder of your")
    assert "Hi" not in t
    long_name = " ".join(["Long"] * 60)
    assert long_name in _plan(s, customer_name=long_name, optout_sms_v2=True)[0]["text"]


def test_input_unchanged():
    appts = [_appt(_dt(2026, 6, 10, 14)), _appt(_dt(2026, 6, 10, 0, 30), id="B")]
    snap = copy.deepcopy(appts)
    plan_reminders(appts, NOW)
    assert appts == snap


def test_logging_hides_pii(caplog):
    caplog.set_level(logging.DEBUG)
    appts = [_appt(_dt(2026, 6, 10, 14), customer_name="Zed Uniqueperson"),
             _appt(_dt(2026, 6, 10, 14), id="NOC", phone=None, email=None),
             _appt(datetime(2026, 6, 10, 14), id="BAD")]
    plan_reminders(appts, NOW)
    text = caplog.text
    assert SECRET_EMAIL not in text and "0851234567" not in text and "Uniqueperson" not in text
    assert text.count("reminder planned appointment_id=A1") == 2
    assert "NOC" in text and "BAD" in text