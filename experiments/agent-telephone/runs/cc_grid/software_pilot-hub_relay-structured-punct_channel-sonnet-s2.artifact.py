"""Brennan Opticians appointment reminder planner (standard library only).

NOTE: the tests at the bottom were written without the ability to execute
them in this session. Run `python -m unittest <this_file>` (or pytest) to
confirm.

ASSUMPTIONS AND REPORT NOTES
* R6 FLAG SEMANTICS (NEEDS CLIENT CONFIRMATION): the client said "text them if
  optout_sms_v2 is true", which is ambiguous for an opt-out field. Fail-safe
  reading implemented: optout_sms_v2 == True means OPTED OUT (no SMS);
  False means SMS allowed; missing, None or non-bool is treated as opted out.
  The decision lives in OPTOUT_TRUE_MEANS_OPTED_OUT and _sms_permitted();
  set the constant to False to flip it.
* R8a: when the back-shift to 20:00 lands before `now`, the reminder moves
  forward to the next 08:00 Dublin after `now`; dropped if >= starts_at.
  Both reminders are floored to `now` (the 2h one only matters in R5a).
* Date format "DD Mon YYYY" with English month abbreviations (locale
  independent). With no name the greeting is "Hi, reminder: ...". The
  first-initial form is "J." (initial plus full stop).
* Dublin local time is used for everyone, including country PL.
* 160 is counted in code points (NFC). The signatures contain non-GSM
  characters, so carriers send these as Unicode, 70 chars per segment
  (67 when concatenated); a 160 char message can be 3 segments.
* R18: no memory of what was sent. The caller must dedupe repeated runs.
* LOGGING: the house rule asks for one INFO line per planned reminder with
  recipient and channel/contact. R10 (DPC audit) forbids phone, name and email
  in logs, so the line carries appointment id, reminder kind, channel and the
  contact FIELD ("phone"), never the contact value. Support can trace
  delivery by appointment id. Needs confirmation if the raw number is wanted.
* Required record fields: id, customer_name (str), status (str), starts_at
  (aware datetime). Missing phone/optout simply means no reminder.
"""
import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
SMS_MAX = 160
OPTOUT_TRUE_MEANS_OPTED_OUT = True  # R6 assumption; flip here only.
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_REMINDERS = ((timedelta(hours=48), "48h", 0), (timedelta(hours=2), "2h", 1))


def _sms_permitted(flag):
    """Single place deciding SMS permission from optout_sms_v2."""
    if not isinstance(flag, bool):
        return False
    return (not flag) if OPTOUT_TRUE_MEANS_OPTED_OUT else flag


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _valid_id(v):
    if isinstance(v, bool):
        return False
    return (isinstance(v, str) and bool(v.strip())) or isinstance(v, int)


def _invalid_reason(a):
    if not isinstance(a, dict):
        return "record is not a mapping"
    if not _valid_id(a.get("id")):
        return "missing or invalid id"
    if not isinstance(a.get("customer_name"), str):
        return "missing or invalid customer_name"
    if not isinstance(a.get("status"), str):
        return "missing or invalid status"
    if not _aware(a.get("starts_at")):
        return "missing or invalid starts_at"
    return None


def _at(d, hour):
    return datetime.combine(d, time(hour), tzinfo=DUBLIN).astimezone(UTC)


def _shift(t, now, starts):
    """R8/R8a steps 2-4. All datetimes are UTC; returns UTC or None."""
    loc = t.astimezone(DUBLIN)
    if loc.hour >= 21 or loc.hour < 8:
        d = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
        t = _at(d, 20)
        if t < now:
            ln = now.astimezone(DUBLIN)
            d = ln.date() if ln.hour < 8 else ln.date() + timedelta(days=1)
            t = _at(d, 8)
    return None if t >= starts else t


def _signature(a):
    c = a.get("country")
    pl = isinstance(c, str) and c.strip().upper() == "PL"
    return unicodedata.normalize("NFC", SIGNATURE_PL if pl else SIGNATURE_DEFAULT)


def _build_text(a, starts):
    loc = starts.astimezone(DUBLIN)
    date = f"{loc.day:02d} {_MONTHS[loc.month - 1]} {loc.year}"
    hhmm = f"{loc.hour:02d}:{loc.minute:02d}"
    sig = _signature(a)
    name = " ".join(unicodedata.normalize("NFC", a.get("customer_name")).split())
    first = name.split(" ")[0] if name else ""
    for cand in (name, first, first[:1] + "." if first else "", ""):
        greet = f"Hi {cand}," if cand else "Hi,"
        text = unicodedata.normalize(
            "NFC",
            f"{greet} reminder: your Brennan Opticians appointment is on {date} at {hhmm}. {sig}")
        if len(text) <= SMS_MAX:
            return text
    return None


def _plan_one(a, now):
    reason = _invalid_reason(a)
    if reason:
        aid = a.get("id") if isinstance(a, dict) and _valid_id(a.get("id")) else "unknown"
        log.warning("skipped appointment id=%s reason=%s", aid, reason)
        return []
    aid = a.get("id")
    status = a.get("status").strip().casefold()
    starts = a.get("starts_at").astimezone(UTC)
    if status == "cancelled":
        log.debug("no reminders id=%s reason=cancelled", aid)
        return []
    if starts <= now:
        log.debug("no reminders id=%s reason=already started", aid)
        return []
    phone = a.get("phone")
    if not isinstance(phone, str) or not phone.strip():
        log.debug("no reminders id=%s reason=no sms contact", aid)
        return []
    if not _sms_permitted(a.get("optout_sms_v2")):
        log.debug("no reminders id=%s reason=sms not permitted", aid)
        return []
    cands = []
    for delta, label, order in _REMINDERS:
        t = _shift(max(starts - delta, now), now, starts)
        if t is not None:
            cands.append((t, order, label))
    if len(cands) == 2 and cands[0][0] == cands[1][0]:
        cands = [cands[1]]  # R19: keep the 2h one
    if not cands:
        return []
    text = _build_text(a, starts)
    rows = []
    for t, order, label in cands:
        if text is None:
            log.warning("skipped reminder id=%s reason=text too long", aid)
            continue
        log.info("reminder planned id=%s kind=%s channel=sms contact=phone send_at=%s",
                 aid, label, t.astimezone(DUBLIN).isoformat())
        rows.append((t, str(aid), order,
                     {"appointment_id": aid, "channel": "sms",
                      "send_at": t.astimezone(DUBLIN), "text": text}))
    return rows


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_u = now.astimezone(UTC)
    rows = []
    for a in appointments:
        rows.extend(_plan_one(a, now_u))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return [r[3] for r in rows]


# ----------------------------------------------------------------- tests
import copy
import random
import sys
import unittest
from unittest import mock


def U(*a):
    return datetime(*a, tzinfo=UTC)


NOW = U(2026, 10, 13, 10)
EMAIL = "mary.murphy@example.com"
PHONE = "+353871234567"


def mk(**kw):
    d = dict(id="A1", customer_name="Mary Murphy", email=EMAIL, phone=PHONE,
             country="IE", status="confirmed", starts_at=U(2026, 10, 20, 10),
             optout_sms_v2=False)
    d.update(kw)
    return d


def sends(res):
    return [r["send_at"] for r in res]


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, r):
        self.records.append(r)


class _NoLegacy(dict):
    def get(self, k, d=None):
        assert k != "opt_out", "legacy field read"
        return super().get(k, d)

    def __getitem__(self, k):
        assert k != "opt_out", "legacy field read"
        return super().__getitem__(k)


class PlannerTests(unittest.TestCase):
    def test_r1_empty_and_keys(self):
        self.assertEqual(plan_reminders([], NOW), [])
        res = plan_reminders([mk()], NOW)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(r["channel"], "sms")
            self.assertEqual(r["appointment_id"], "A1")

    def test_r2_bad_now(self):
        for bad in (datetime(2026, 10, 13, 10), "now", None):
            with self.assertRaises(ValueError):
                plan_reminders([], bad)
            with self.assertRaises(ValueError):
                plan_reminders([mk()], bad)
        res = plan_reminders([mk()], NOW.astimezone(timezone(timedelta(hours=5))))
        self.assertEqual(len(res), 2)

    def test_r3_legacy_field_ignored(self):
        a = _NoLegacy(mk(opt_out=True, optout_sms_v2=False))
        self.assertEqual(len(plan_reminders([a], NOW)), 2)
        b = _NoLegacy(mk(opt_out=False, optout_sms_v2=True))
        self.assertEqual(plan_reminders([b], NOW), [])

    def test_r4_text(self):
        res = plan_reminders([mk()], NOW)
        self.assertEqual(
            res[0]["text"],
            "Hi Mary Murphy, reminder: your Brennan Opticians appointment is on "
            "20 Oct 2026 at 11:00. Siobhán Ní Dhuibhir")
        res = plan_reminders([mk(starts_at=U(2026, 11, 3, 9, 5))], NOW)
        self.assertIn("on 03 Nov 2026 at 09:05.", res[0]["text"])

    def test_r5_dst_safe_offsets(self):
        res = plan_reminders([mk(starts_at=U(2026, 3, 30, 11))], U(2026, 3, 20, 10))
        self.assertEqual(sends(res), [U(2026, 3, 28, 11), U(2026, 3, 30, 9)])
        self.assertEqual(res[0]["send_at"].hour, 11)
        self.assertEqual(res[1]["send_at"].hour, 10)
        res = plan_reminders([mk(starts_at=U(2026, 10, 26, 12))], NOW)
        self.assertEqual(sends(res), [U(2026, 10, 24, 12), U(2026, 10, 26, 10)])

    def test_r5_floor_to_now(self):
        res = plan_reminders([mk(starts_at=NOW + timedelta(hours=30))], NOW)
        self.assertEqual(sends(res), [NOW, U(2026, 10, 14, 14)])
        for r in res:
            self.assertGreaterEqual(r["send_at"], NOW)

    def test_r5a(self):
        self.assertEqual(plan_reminders([mk(starts_at=NOW)], NOW), [])
        self.assertEqual(plan_reminders([mk(starts_at=NOW - timedelta(hours=1))], NOW), [])
        res = plan_reminders([mk(starts_at=NOW + timedelta(minutes=90))], NOW)
        self.assertEqual(sends(res), [NOW])

    def test_r6_channel_rules(self):
        for kw in ({"phone": "  "}, {"phone": ""}, {"phone": None},
                   {"optout_sms_v2": True}, {"optout_sms_v2": None}):
            self.assertEqual(plan_reminders([mk(**kw)], NOW), [], kw)
        a = mk()
        del a["optout_sms_v2"]
        self.assertEqual(plan_reminders([a], NOW), [])
        self.assertTrue(_sms_permitted(False))
        self.assertFalse(_sms_permitted(True))
        self.assertFalse(_sms_permitted(None))
        with mock.patch.object(sys.modules[__name__], "OPTOUT_TRUE_MEANS_OPTED_OUT", False):
            self.assertTrue(_sms_permitted(True))
            self.assertFalse(_sms_permitted(False))
            self.assertFalse(_sms_permitted(None))

    def test_r7_shortening(self):
        long_first = plan_reminders([mk(customer_name="Jo " + "B" * 70)], NOW)
        self.assertTrue(long_first[0]["text"].startswith("Hi Jo, reminder"))
        r = plan_reminders([mk(customer_name="N" * 63)], NOW)[0]["text"]
        self.assertEqual(len(r), 160)
        self.assertTrue(r.startswith("Hi " + "N" * 63 + ","))
        r = plan_reminders([mk(customer_name="N" * 64)], NOW)[0]["text"]
        self.assertTrue(r.startswith("Hi N., reminder"))
        r = plan_reminders([mk(customer_name="X" * 70 + " Y")], NOW)[0]["text"]
        self.assertTrue(r.startswith("Hi X., reminder"))
        for r in plan_reminders([mk(customer_name="Sine\u0301ad Ní")], NOW):
            self.assertEqual(r["text"], unicodedata.normalize("NFC", r["text"]))
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))
        with mock.patch.object(sys.modules[__name__], "SIGNATURE_DEFAULT", "S" * 100):
            cap = _Cap()
            root = logging.getLogger()
            root.addHandler(cap)
            old = root.level
            root.setLevel(logging.DEBUG)
            try:
                self.assertEqual(plan_reminders([mk(id="LONG1")], NOW), [])
            finally:
                root.removeHandler(cap)
                root.setLevel(old)
            msgs = [r.getMessage() for r in cap.records]
            self.assertTrue(any("LONG1" in m for m in msgs))
            self.assertFalse(any("Mary" in m or PHONE in m for m in msgs))

    def test_r8_quiet_hours(self):
        # 48h point 22:30 IST -> 20:00 same day
        res = plan_reminders([mk(starts_at=U(2026, 10, 17, 21, 30))], NOW)
        self.assertEqual(sends(res)[0], U(2026, 10, 15, 19))
        # 48h point 03:00 IST and 2h point 01:00 IST -> previous day 20:00
        res = plan_reminders([mk(starts_at=U(2026, 10, 18, 2))], NOW)
        self.assertEqual(sends(res), [U(2026, 10, 15, 19), U(2026, 10, 17, 19)])
        # 08:00 is outside, 06:00 inside
        res = plan_reminders([mk(starts_at=U(2026, 10, 20, 7))], NOW)
        self.assertEqual(sends(res), [U(2026, 10, 18, 7), U(2026, 10, 19, 19)])
        # 21:00 is inside
        res = plan_reminders([mk(starts_at=U(2026, 10, 20, 20))], NOW)
        self.assertEqual(sends(res)[0], U(2026, 10, 18, 19))

    def test_r8_dst_weekends(self):
        res = plan_reminders([mk(starts_at=U(2026, 3, 30, 2))], U(2026, 3, 20, 12))
        self.assertEqual(sends(res), [U(2026, 3, 27, 20), U(2026, 3, 29, 19)])
        res = plan_reminders([mk(starts_at=U(2026, 10, 25, 23))], NOW)
        self.assertEqual(sends(res), [U(2026, 10, 23, 19), U(2026, 10, 25, 20)])

    def test_r8a_forward_and_drop(self):
        now = U(2026, 10, 13, 20, 30)  # 21:30 IST
        res = plan_reminders([mk(starts_at=U(2026, 10, 14, 20, 30))], now)
        self.assertEqual(sends(res), [U(2026, 10, 14, 7), U(2026, 10, 14, 18, 30)])
        self.assertEqual(plan_reminders([mk(starts_at=U(2026, 10, 13, 21, 30))], now), [])

    def test_r9_cancelled(self):
        for s in ("cancelled", "  Cancelled ", "CANCELLED"):
            self.assertEqual(plan_reminders([mk(status=s)], NOW), [])
        self.assertEqual(len(plan_reminders([mk(status="Booked")], NOW)), 2)

    def test_r10_no_pii_in_logs(self):
        cap = _Cap()
        root = logging.getLogger()
        root.addHandler(cap)
        old = root.level
        root.setLevel(logging.DEBUG)
        err = ""
        try:
            batch = [mk(id="E1"), mk(id="E2", starts_at="bad"), "junk",
                     mk(id="E3", phone="  "), mk(id="E4", optout_sms_v2=True),
                     mk(id="E5", status="cancelled"), mk(id="E6", status=None)]
            plan_reminders(batch, NOW)
            try:
                plan_reminders(batch, datetime(2026, 1, 1))
            except ValueError as e:
                err = str(e) + repr(e)
        finally:
            root.removeHandler(cap)
            root.setLevel(old)
        blob = err + "".join(r.getMessage() + str(r.__dict__) for r in cap.records)
        for secret in (EMAIL, PHONE, "Mary", "Murphy"):
            self.assertNotIn(secret, blob)
        planned = [r for r in cap.records
                   if r.levelno == logging.INFO and "planned" in r.getMessage()]
        self.assertEqual(len(planned), 2)
        self.assertIn("E1", planned[0].getMessage())
        self.assertIn("sms", planned[0].getMessage())
        self.assertTrue(any("E2" in r.getMessage() for r in cap.records))

    def test_r11_signature(self):
        for r in plan_reminders([mk()], NOW):
            self.assertTrue(r["text"].endswith(". Siobhán Ní Dhuibhir"))
        for c in ("PL", "pl", " Pl "):
            for r in plan_reminders([mk(country=c)], NOW):
                self.assertTrue(r["text"].endswith(". Grzegorz Szczepański"))
                self.assertIn("at 11:00.", r["text"])  # Dublin time for PL too

    def test_r13_dublin_tz(self):
        for r in plan_reminders([mk()], NOW):
            self.assertEqual(r["send_at"].tzinfo.key, "Europe/Dublin")
            self.assertEqual(r["send_at"].utcoffset(), timedelta(hours=1))
        res = plan_reminders([mk(starts_at=U(2026, 12, 10, 12))], NOW)
        self.assertEqual(res[0]["send_at"].utcoffset(), timedelta(0))

    def test_r14_ordering(self):
        a = [mk(id="B", starts_at=U(2026, 10, 20, 10)), mk(id="A", starts_at=U(2026, 10, 20, 10)),
             mk(id="C", starts_at=U(2026, 10, 19, 12))]
        res = plan_reminders(a, NOW)
        keys = [(r["send_at"], str(r["appointment_id"])) for r in res]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([r["appointment_id"] for r in res if r["send_at"] == U(2026, 10, 18, 10)],
                         ["A", "B"])
        for _ in range(5):
            b = a[:]
            random.shuffle(b)
            self.assertEqual(plan_reminders(b, NOW), res)

    def test_r16_bad_records_skipped(self):
        bad = [{}, "x", mk(id=None), mk(id=""), mk(id=True),
               mk(starts_at=datetime(2026, 10, 20, 10)), mk(starts_at=None),
               mk(status=3), mk(customer_name=None)]
        res = plan_reminders(bad + [mk(id="OK")], NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"OK"})

    def test_r17_pure(self):
        a = [mk(), mk(id="A2", status="cancelled")]
        before = copy.deepcopy(a)
        plan_reminders(a, NOW)
        self.assertEqual(a, before)

    def test_r19_identical_send_at(self):
        now = U(2026, 10, 13, 20, 30)
        res = plan_reminders([mk(starts_at=U(2026, 10, 14, 7, 30))], now)
        self.assertEqual(sends(res), [U(2026, 10, 14, 7)])

    def test_r21_current_period_and_dst_dates(self):
        res = plan_reminders([mk(starts_at=U(2026, 10, 14, 12))], NOW)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertGreaterEqual(r["send_at"], NOW)
            self.assertLess(r["send_at"], U(2026, 10, 14, 12))


if __name__ == "__main__":
    unittest.main()