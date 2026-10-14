"""Brennan Opticians appointment reminder planner.

File: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-qrc4kc1g/brennan_reminders.py
Run tests (any TZ): python3 -m unittest -v brennan_reminders
  e.g. TZ=UTC python3 -m unittest brennan_reminders ; TZ=Asia/Tokyo python3 -m unittest brennan_reminders
Test results: not executed here (no execution tools were available); run the commands above.

Python 3.9+ ships zoneinfo; this targets 3.12. The IANA database must exist: on
systems without system tz data (Windows, slim containers) run `pip install tzdata`.
plan_reminders loads the default zone up front so a missing database fails loudly.

Logging note: the house rule asks for an INFO line per planned reminder naming the
channel and contact. R10 (DPC audit) forbids logging email, phone or name, so each
INFO line carries the appointment id, reminder number, channel, the contact FIELD
used ("phone" or "email", never its value) and send_at. This is a deliberate
conflict resolution in favour of R10; tell support.

[CONFIRM] defaults chosen (see constants / functions named):
 - R7/R22 SMS_LIMIT = 160 NFC chars, no transliteration (real SMS may be UCS-2).
 - R9 "canceled" also treated as cancelled (CANCELLED_STATUSES).
 - R13/R24 COUNTRY_ZONES empty: every country, including PL, uses Europe/Dublin.
 - R17 quiet-hours fallback: now outside window -> now; inside -> next 08:00 local
   if strictly before start, else omit (_fallback_time).
 - R18 start <= now -> nothing; t1 < now -> now; t2 < now -> omitted.
 - R20 no usable channel -> no reminders. optout_sms_v2 missing/None/non-bool means
   opted out (a missing optout_sms_v2 key is NOT treated as malformed, per R20).
 - R21 single English template, no subject (TEMPLATE).
 - R27 stateless: repeated runs give different "now" send_at; the caller must dedupe.
   No extra output keys.
"""
import copy
import logging
import os
import time as _time
import unicodedata
import unittest
from collections.abc import Mapping
from datetime import datetime, timedelta, time, timezone
from functools import cache
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

# ---- [CONFIRM] configuration, all in one place -----------------------------
DEFAULT_ZONE = "Europe/Dublin"
COUNTRY_ZONES: dict[str, str] = {}          # R24: PL follows Dublin by default
SMS_LIMIT = 160                             # R7/R22
CANCELLED_STATUSES = {"cancelled", "canceled"}   # R9
TEMPLATE = ("{greeting} reminder: your Brennan Opticians appointment is on "
            "{date} at {time}. {signature}")     # R21
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURES = {"PL": "Grzegorz Szczepański"}
QUIET_START_H, QUIET_END_H, QUIET_RESUME_H = 21, 8, 20
# -----------------------------------------------------------------------------

_REQUIRED = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")


def _nfc(s):
    return unicodedata.normalize("NFC", s)


@cache
def _zone(name):
    return ZoneInfo(name)


def _country_key(country):
    return country.strip().upper() if isinstance(country, str) else ""


def _zone_for(country):
    return _zone(COUNTRY_ZONES.get(_country_key(country), DEFAULT_ZONE))


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _safe_id(a):
    try:
        v = a.get("id") if isinstance(a, Mapping) else None
    except Exception:
        return "unknown"
    return str(v) if isinstance(v, (str, int)) and not isinstance(v, bool) else "unknown"


def _parse(a):
    """Return a validated dict or None when malformed."""
    if not isinstance(a, Mapping):
        return None
    if any(k not in a for k in _REQUIRED):
        return None
    p = {k: a[k] for k in _REQUIRED}
    if isinstance(p["id"], bool) or not isinstance(p["id"], (str, int)):
        return None
    for k in ("customer_name", "status"):
        if not isinstance(p[k], str):
            return None
    for k in ("email", "phone", "country"):
        if p[k] is not None and not isinstance(p[k], str):
            return None
    if not _aware(p["starts_at"]):
        return None
    p["optout"] = a["optout_sms_v2"] if "optout_sms_v2" in a else None  # R4/R20
    return p


def _present(s):
    return isinstance(s, str) and bool(s.strip())


def _channel(p):
    """R6/R20: returns (channel, contact_field) or None."""
    if _present(p["phone"]) and p["optout"] is False:
        return "sms", "phone"
    if _present(p["email"]):
        return "email", "email"
    return None


def _in_quiet(local):
    return local.hour >= QUIET_START_H or local.hour < QUIET_END_H


def _quiet_adjust(dt, zone):
    """R8: move back to the immediately preceding 20:00 local if in quiet hours."""
    local = dt.astimezone(zone)
    if not _in_quiet(local):
        return local
    d = local.date() if local.hour >= QUIET_START_H else local.date() - timedelta(days=1)
    return datetime.combine(d, time(QUIET_RESUME_H), tzinfo=zone)


def _fallback_time(now, starts, zone):
    """R17: where a reminder whose adjusted time is before now should go."""
    local = now.astimezone(zone)
    if not _in_quiet(local):
        return now
    d = local.date() + timedelta(days=1) if local.hour >= QUIET_START_H else local.date()
    t = datetime.combine(d, time(QUIET_END_H), tzinfo=zone)
    return t if t < starts else None


def _sms_limit_ok(text):
    return len(text) <= SMS_LIMIT


def _name_variants(name):
    parts = name.split()
    if not parts:
        return [""]
    out = [" ".join(parts)]
    if len(parts) > 1:
        out.append(f"{parts[0]} {parts[-1][0]}.")
    out.append(parts[0])
    out.append("")
    return out


def _build_text(p, channel, local_start):
    sig = SIGNATURES.get(_country_key(p["country"]), DEFAULT_SIGNATURE)
    date = f"{local_start.day:02d}/{local_start.month:02d}/{local_start.year:04d}"
    tm = f"{local_start.hour:02d}:{local_start.minute:02d}"

    def make(n):
        greeting = f"Hi {n}," if n else "Hi,"
        return _nfc(TEMPLATE.format(greeting=greeting, date=date, time=tm, signature=sig))

    variants = _name_variants(p["customer_name"])
    if channel == "email":
        return make(variants[0])
    for n in variants:
        text = make(n)
        if _sms_limit_ok(text):
            return text
    return make("")


def _plan_one(a, now):
    p = _parse(a)
    if p is None:
        log.warning("skipped appointment_id=%s reason=malformed", _safe_id(a))
        return []
    aid = p["id"]
    if p["status"].strip().lower() in CANCELLED_STATUSES:
        log.info("skipped appointment_id=%s reason=cancelled", aid)
        return []
    starts = p["starts_at"].astimezone(timezone.utc)   # elapsed-time arithmetic on UTC
    if starts <= now:
        log.info("skipped appointment_id=%s reason=already_started", aid)
        return []
    ch = _channel(p)
    if ch is None:
        log.info("skipped appointment_id=%s reason=no_channel", aid)
        return []
    channel, field = ch
    zone = _zone_for(p["country"])
    cands = []
    for idx, raw in ((1, starts - timedelta(hours=48)), (2, starts - timedelta(hours=2))):
        if raw < now:
            if idx == 2:
                continue
            raw = now
        adj = _quiet_adjust(raw, zone)
        if adj < now:
            adj = _fallback_time(now, starts, zone)
            if adj is None:
                continue
        cands.append((idx, adj))
    if len(cands) == 2 and cands[0][1] == cands[1][1]:
        cands = [cands[1]]                       # R19 keep the 2-hour one
    if not cands:
        log.info("skipped appointment_id=%s reason=no_valid_send_time", aid)
    text = _build_text(p, channel, starts.astimezone(zone))
    out = []
    for idx, when in cands:
        send_at = when.astimezone(zone)
        log.info("planned appointment_id=%s reminder=%d channel=%s contact_field=%s send_at=%s",
                 aid, idx, channel, field, send_at.isoformat())
        out.append({"appointment_id": aid, "channel": channel, "send_at": send_at, "text": text})
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    _zone(DEFAULT_ZONE)                          # fail loudly if tz database is missing
    now_utc = now.astimezone(timezone.utc)
    result = []
    for a in appointments:
        try:
            result.extend(_plan_one(a, now_utc))
        except Exception as exc:                 # never embed the appointment or message
            log.error("skipped appointment_id=%s reason=unexpected_error type=%s",
                      _safe_id(a), type(exc).__name__)
    result.sort(key=lambda r: r["send_at"])      # stable, by instant
    return result


# ============================== tests ========================================
DUB = ZoneInfo("Europe/Dublin")
EMAIL = "secret.person@example.com"


def D(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUB)


def appt(**kw):
    base = dict(id="A1", customer_name="Mary O'Brien", email=EMAIL, phone="+353871234567",
                country="IE", status="confirmed", starts_at=D(2026, 11, 10, 14),
                optout_sms_v2=False)
    base.update(kw)
    return base


def plan1(now, **kw):
    return plan_reminders([appt(**kw)], now)


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class _Boom(dict):
    def __contains__(self, k):
        raise RuntimeError("boom")


class WorkedExamples(unittest.TestCase):
    def test_e1(self):
        r = plan1(D(2026, 11, 1, 9))
        self.assertEqual([x["send_at"] for x in r], [D(2026, 11, 8, 14), D(2026, 11, 10, 12)])

    def test_e2(self):
        r = plan1(D(2026, 11, 1, 9), starts_at=D(2026, 11, 10, 9))
        self.assertEqual([x["send_at"] for x in r], [D(2026, 11, 8, 9), D(2026, 11, 9, 20)])

    def test_e3_dst_back(self):
        r = plan1(D(2026, 10, 1, 9), starts_at=D(2026, 10, 26, 10))
        self.assertEqual(len(r), 2)
        self.assertEqual((r[0]["send_at"].hour, r[0]["send_at"].day), (11, 24))
        self.assertEqual(r[0]["send_at"].utcoffset(), timedelta(hours=1))
        self.assertEqual(r[1]["send_at"], D(2026, 10, 26, 8))

    def test_e4(self):
        r = plan1(D(2026, 11, 3, 22, 30), starts_at=D(2026, 11, 4, 9))
        self.assertEqual([x["send_at"] for x in r], [D(2026, 11, 4, 8)])

    def test_e5(self):
        self.assertEqual(plan1(D(2026, 11, 3, 22, 30), starts_at=D(2026, 11, 4, 8)), [])

    def test_e6(self):
        now = D(2026, 11, 10, 20, 30)
        r = plan1(now, starts_at=D(2026, 11, 12, 21, 30))
        self.assertEqual([x["send_at"] for x in r], [now, D(2026, 11, 12, 19, 30)])


class Dst(unittest.TestCase):
    def test_oct_week_elapsed(self):
        r = plan1(D(2026, 10, 1, 9), starts_at=D(2026, 10, 25, 12))
        self.assertEqual(r[0]["send_at"].hour, 13)     # 23 Oct 12:00 UTC = 13:00 IST

    def test_march_week_elapsed(self):
        r = plan1(D(2027, 3, 1, 9), starts_at=D(2027, 3, 29, 10))
        self.assertEqual((r[0]["send_at"].day, r[0]["send_at"].hour), (27, 9))
        self.assertEqual((r[1]["send_at"].day, r[1]["send_at"].hour), (29, 8))


class Rules(unittest.TestCase):
    NOW = D(2026, 11, 1, 9)

    def test_keys_and_types(self):
        r = plan1(self.NOW)
        self.assertEqual(set(r[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertIsNotNone(r[0]["send_at"].utcoffset())
        self.assertEqual(plan_reminders([], self.NOW), [])

    def test_display_dublin(self):
        s = datetime(2026, 7, 1, 23, 30, tzinfo=timezone.utc)
        r = plan1(D(2026, 6, 1, 9), starts_at=s)
        self.assertIn("02/07/2026 at 00:30.", r[0]["text"])

    def test_naive_now(self):
        with self.assertRaises(ValueError):
            plan_reminders([appt()], datetime(2026, 1, 1))

    def test_malformed_skipped_batch_continues(self):
        bad = [appt(id="x", starts_at=datetime(2026, 11, 10, 14)), appt(id="y", status=5),
               {"id": "z"}, "junk", appt(id=True)]
        r = plan_reminders(bad + [appt(id="ok")], self.NOW)
        self.assertEqual({x["appointment_id"] for x in r}, {"ok"})

    def test_no_mutation(self):
        a = [appt()]
        before = copy.deepcopy(a)
        plan_reminders(a, self.NOW)
        self.assertEqual(a, before)

    def test_cancelled(self):
        for s in ("cancelled", " Cancelled ", "CANCELED"):
            self.assertEqual(plan1(self.NOW, status=s), [])
        self.assertTrue(plan1(self.NOW, status="Booked"))

    def test_started(self):
        self.assertEqual(plan1(D(2026, 11, 10, 14), starts_at=D(2026, 11, 10, 14)), [])

    def test_one_hour_away(self):
        now = D(2026, 11, 10, 10)
        r = plan1(now, starts_at=D(2026, 11, 10, 11))
        self.assertEqual([x["send_at"] for x in r], [now])

    def test_channels(self):
        self.assertEqual(plan1(self.NOW)[0]["channel"], "sms")
        for kw in (dict(optout_sms_v2=True), dict(optout_sms_v2=None), dict(optout_sms_v2="no"),
                   dict(phone="  "), dict(phone=None)):
            r = plan1(self.NOW, **kw)
            self.assertEqual({x["channel"] for x in r}, {"email"}, kw)
        self.assertEqual(plan1(self.NOW, phone=None, email=" "), [])
        self.assertEqual(plan1(self.NOW, optout_sms_v2=True, email=None), [])

    def test_legacy_optout_ignored(self):
        self.assertEqual(plan1(self.NOW, opt_out=True)[0]["channel"], "sms")
        a = appt(opt_out=False)
        del a["optout_sms_v2"]
        self.assertEqual(plan_reminders([a], self.NOW)[0]["channel"], "email")

    def test_sms_shortening(self):
        r = plan1(self.NOW, customer_name="A" * 60 + " " + "B" * 60)
        self.assertEqual(r[0]["text"].split(",")[0], "Hi " + "A" * 60 + " B.")
        r = plan1(self.NOW, customer_name="A" * 62 + " " + "B" * 62)
        self.assertTrue(r[0]["text"].startswith("Hi " + "A" * 62 + ", reminder"))
        r = plan1(self.NOW, customer_name="A" * 100 + " Z")
        self.assertTrue(r[0]["text"].startswith("Hi, reminder"))
        for x in r:
            self.assertLessEqual(len(x["text"]), SMS_LIMIT)
            self.assertTrue(x["text"].endswith(DEFAULT_SIGNATURE))
        e = plan1(self.NOW, customer_name="A" * 100 + " Z", phone=None)
        self.assertIn("A" * 100 + " Z,", e[0]["text"])

    def test_signature(self):
        self.assertTrue(plan1(self.NOW, country=" pl ")[0]["text"].endswith("Grzegorz Szczepański"))
        for c in (None, "IE", ""):
            self.assertTrue(plan1(self.NOW, country=c)[0]["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_no_pii_in_output(self):
        for x in plan1(self.NOW) + plan1(self.NOW, phone=None):
            self.assertNotIn("@", x["text"])
            self.assertNotIn("+353", x["text"])

    def test_quiet_hours(self):
        f = lambda h, m=0, d=5: _quiet_adjust(D(2026, 11, d, h, m), DUB)
        self.assertEqual(f(20, 59), D(2026, 11, 5, 20, 59))
        self.assertEqual(f(21), D(2026, 11, 5, 20))
        self.assertEqual(f(0), D(2026, 11, 4, 20))
        self.assertEqual(f(7, 59), D(2026, 11, 4, 20))
        self.assertEqual(f(8), D(2026, 11, 5, 8))

    def test_sorted(self):
        a = appt(id="late", starts_at=D(2026, 11, 20, 14))
        b = appt(id="early", starts_at=D(2026, 11, 10, 14))
        r = plan_reminders([a, b], self.NOW)
        self.assertEqual([x["send_at"] for x in r], sorted(x["send_at"] for x in r))
        self.assertEqual(r[0]["appointment_id"], "early")

    def test_tz_independent(self):
        if not hasattr(_time, "tzset"):
            self.skipTest("no tzset")
        old = os.environ.get("TZ")
        try:
            for tz in ("UTC", "Asia/Tokyo"):
                os.environ["TZ"] = tz
                _time.tzset()
                r = plan1(D(2026, 11, 1, 9))
                self.assertEqual([x["send_at"] for x in r],
                                 [D(2026, 11, 8, 14), D(2026, 11, 10, 12)])
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            _time.tzset()


class Logging(unittest.TestCase):
    def test_no_pii_logged(self):
        cap = _Cap()
        root = logging.getLogger()
        old = root.level
        root.addHandler(cap)
        root.setLevel(logging.DEBUG)
        try:
            now = D(2026, 11, 1, 9)
            batch = [appt(id="ok"), appt(id="can", status="cancelled"),
                     appt(id="mal", starts_at=datetime(2026, 11, 10, 14)),
                     appt(id="past", starts_at=D(2026, 10, 1, 9)),
                     appt(id="none", phone=None, email=None),
                     _Boom(appt(id="boom")), appt(id="mail", phone=None)]
            r = plan_reminders(batch, now)
        finally:
            root.removeHandler(cap)
            root.setLevel(old)
        self.assertTrue(cap.records)
        planned = [x for x in cap.records if x.levelno == logging.INFO and "planned" in x.getMessage()]
        self.assertEqual(len(planned), len(r))
        for rec in cap.records:
            blob = rec.getMessage() + str(rec.args) + str(rec.exc_info)
            for secret in (EMAIL, "secret.person", "+353871234567", "Mary", "O'Brien"):
                self.assertNotIn(secret, blob)


if __name__ == "__main__":
    unittest.main()