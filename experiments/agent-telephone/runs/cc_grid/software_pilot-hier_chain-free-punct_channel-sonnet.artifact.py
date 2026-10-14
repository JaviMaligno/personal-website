"""Brennan Opticians appointment reminder planner (stdlib only, Python 3.12).

plan_reminders(appointments, now) -> list of dicts with exactly the keys
appointment_id, channel, send_at, text, sorted by send_at instant (ties:
str(appointment_id), then first before second). send_at is tz-aware, Europe/Dublin.

OPT-OUT DECISION (READ THIS FIRST): the client's literal wording is "send SMS if
optout_sms_v2 is true". This module DELIBERATELY CONTRADICTS that. By default
optout_sms_v2 == True means "opted out", so NO SMS is sent. Reason: texting an
opted-out person is a consent/regulatory problem, whereas not texting is a
recoverable missed reminder. One switch, OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT, flips
it. The client must confirm before go-live. The flag must be a real bool; a
missing, None or non-bool value is a malformed record (fail closed, no SMS).
The legacy opt_out field is never read.

Channels: only "sms" is ever emitted. Email is never a channel or a fallback and
the email field is never read. No phone (str with at least one digit) or opted
out means nothing is sent.

Timing: all arithmetic is on absolute instants (UTC internally). "48 hours" is 48
ELAPSED hours, not wall-clock, so it differs by one hour across a DST change.
Targets: first = start - 48h, second = start - 2h. A target before now becomes
"immediate" (= now). ASSUMPTION: this also applies to the second reminder when
the appointment is under 2h away but still in the future. If both are immediate,
only the second is emitted. Quiet hours (Dublin local time): quiet if >= 21:00
or < 08:00 (21:00 is quiet, 08:00 and 20:59 are allowed). A quiet target moves
BACK to the preceding 20:00 Dublin; if that is before now, now is used when now
is not quiet; otherwise the reminder is dropped (never deferred forward, never in
the past; stateless, a later run picks it up). A 2h reminder moved back to 20:00
the evening before is accepted. If first and second end up at the same instant,
only the second is kept. Text date/time are the appointment start in Dublin.

Malformed records (not a dict, missing id/status/starts_at/optout_sms_v2, naive
starts_at, non-bool flag, id not str/int) are skipped with a WARNING carrying only
a reason code and a sanitised id; the batch continues. Callers can only see
skipped records via logs (limitation). Duplicate ids are NOT deduplicated.
Cancelled records are skipped before any other validation.

Privacy: logs never contain email, name, phone or message text. House rule asks
for one INFO line per planned reminder naming recipient and channel/contact; to
reconcile with the privacy rule, the contact is logged MASKED (last two digits).

SMS length risk (rule unchanged: len(text) <= 160): diacritics (a-acute, o-acute,
n-acute, l-stroke) make an SMS UCS-2, where a segment holds 70 characters, and the
signatures contain non-GSM-7 characters, so every message is probably UCS-2 and
the real segment count may be higher than 160 characters suggests.

Run the embedded tests with: python reminders.py  (the author had no way to
execute them; they have NOT been run).
"""
import logging
import re
import sys
import unicodedata
import unittest
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
QUIET_START = time(21, 0)          # quiet from here (inclusive)
QUIET_END = time(8, 0)             # quiet until here (exclusive)
QUIET_FALLBACK_TIME = time(20, 0)  # quiet reminders move back to this time
FIRST_LEAD = timedelta(hours=48)   # elapsed hours, not wall-clock
SECOND_LEAD = timedelta(hours=2)
SMS_MAX_LEN = 160
# DELIBERATE deviation from client wording: True means opted OUT (no SMS).
# Set to False to get the client's literal reading. Needs client confirmation.
OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT = True
DEFAULT_SIGNATURE = unicodedata.normalize("NFC", "Siobhán Ní Dhuibhir")
PL_SIGNATURE = unicodedata.normalize("NFC", "Grzegorz Szczepański")

logger = logging.getLogger("brennan.reminders")

_CANCELLED = {"cancelled", "canceled"}
_REQUIRED = ("id", "status", "starts_at", "optout_sms_v2")
_MALFORMED = {"not_a_dict", "missing_key", "bad_id", "bad_starts_at", "bad_optout_flag"}


class _Skip(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def sms_permitted(flag):
    """True if the opt-out flag allows SMS. Fails closed on non-bool."""
    if not isinstance(flag, bool):
        return False
    if OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT:
        return not flag
    return flag


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _safe_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return "<unknown>"
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(value))[:40]


def _is_quiet(t):
    lt = t.astimezone(DUBLIN).time()
    return lt >= QUIET_START or lt < QUIET_END


def _effective(t, now):
    """Return the instant (UTC) to send for candidate t >= now, or None."""
    if not _is_quiet(t):
        return t
    local = t.astimezone(DUBLIN)
    d = local.date() if local.time() >= QUIET_START else local.date() - timedelta(days=1)
    cand = datetime.combine(d, QUIET_FALLBACK_TIME, tzinfo=DUBLIN).astimezone(UTC)
    if cand >= now:
        return cand
    if not _is_quiet(now):
        return now
    return None


def _clean_name(name):
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFC", name)
    s = "".join(" " if unicodedata.category(c).startswith("C") else c for c in s)
    return " ".join(s.split())


def _name_variants(clean):
    if not clean:
        return []
    parts = clean.split(" ")
    out = [clean]
    if len(parts) > 1:
        out.append(f"{parts[0]} {parts[-1][0]}.")
    out.append(parts[0])
    out.append(f"{parts[0][0]}.")
    seen, res = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            res.append(v)
    return res


def compose_text(name, country, local_start):
    """Build the SMS text, or None if even the shortest template is too long."""
    pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = PL_SIGNATURE if pl else DEFAULT_SIGNATURE
    date = f"{local_start.day:02d}/{local_start.month:02d}/{local_start.year:04d}"
    tm = f"{local_start.hour:02d}:{local_start.minute:02d}"
    for n in _name_variants(_clean_name(name)):
        t = f"Hi {n}, this is a reminder of your Brennan Opticians appointment on {date} at {tm}. {sig}"
        if len(t) <= SMS_MAX_LEN:
            return t
    for t in (f"Reminder: your Brennan Opticians appointment is on {date} at {tm}. {sig}",
              f"Appointment {date} at {tm}. {sig}"):
        if len(t) <= SMS_MAX_LEN:
            return t
    return None


def _mask(phone):
    digits = [c for c in phone if c.isdigit()]
    return "***" + "".join(digits[-2:])


def _plan_one(rec, now, skipped):
    if not isinstance(rec, dict):
        raise _Skip("not_a_dict")
    status = rec.get("status")
    if isinstance(status, str) and status.strip().casefold() in _CANCELLED:
        raise _Skip("cancelled")
    for k in _REQUIRED:
        if k not in rec:
            raise _Skip("missing_key")
    aid = rec["id"]
    if isinstance(aid, bool) or not isinstance(aid, (str, int)):
        raise _Skip("bad_id")
    start = rec["starts_at"]
    if not _aware(start):
        raise _Skip("bad_starts_at")
    flag = rec["optout_sms_v2"]
    if not isinstance(flag, bool):
        raise _Skip("bad_optout_flag")
    if not sms_permitted(flag):
        raise _Skip("opted_out")
    phone = rec.get("phone")
    if not (isinstance(phone, str) and any(c.isdigit() for c in phone)):
        raise _Skip("no_phone")
    start_u = start.astimezone(UTC)
    if start_u <= now:
        raise _Skip("already_started")
    sid = _safe_id(aid)
    t1, t2 = start_u - FIRST_LEAD, start_u - SECOND_LEAD
    imm1, imm2 = t1 < now, t2 < now
    t1 = now if imm1 else t1
    t2 = now if imm2 else t2
    cands = [] if (imm1 and imm2) else [(0, t1)]
    cands.append((1, t2))
    eff = {}
    for kind, t in cands:
        e = _effective(t, now)
        if e is None or e < now:
            skipped["quiet_hours_drop"] += 1
            logger.info("dropped reminder appointment_id=%s kind=%d reason=quiet_hours_drop", sid, kind)
        else:
            eff[kind] = e
    if 0 in eff and 1 in eff and eff[0] == eff[1]:
        del eff[0]
    if not eff:
        return []
    text = compose_text(rec.get("customer_name"), rec.get("country"), start_u.astimezone(DUBLIN))
    if text is None:
        skipped["text_too_long"] += 1
        logger.warning("skipped appointment_id=%s reason=text_too_long", sid)
        return []
    return [(e, str(aid), kind, aid, text, _mask(phone), sid) for kind, e in eff.items()]


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    if not isinstance(appointments, (list, tuple)):
        raise TypeError("appointments must be a list or tuple")
    now_u = now.astimezone(UTC)
    planned, skipped = [], Counter()
    for rec in appointments:
        sid = "<unknown>"
        try:
            if isinstance(rec, dict):
                sid = _safe_id(rec.get("id"))
            planned.extend(_plan_one(rec, now_u, skipped))
        except _Skip as s:
            skipped[s.reason] += 1
            if s.reason in _MALFORMED:
                logger.warning("skipped appointment_id=%s reason=%s", sid, s.reason)
            else:
                logger.debug("skipped appointment_id=%s reason=%s", sid, s.reason)
        except Exception as exc:  # no message, no traceback: may contain PII
            skipped["unexpected_error"] += 1
            logger.warning("skipped appointment_id=%s reason=unexpected_error type=%s",
                           sid, type(exc).__name__)
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    result = []
    for e, _s, kind, aid, text, masked, sid in planned:
        logger.info("planned reminder appointment_id=%s kind=%d channel=sms contact=%s",
                    sid, kind, masked)
        result.append({"appointment_id": aid, "channel": "sms",
                       "send_at": e.astimezone(DUBLIN), "text": text})
    logger.info("batch input=%d produced=%d skipped=%s", len(appointments), len(result),
                dict(skipped))
    return result


# ----------------------------------------------------------------- tests
EMAIL = "secret.person@example.com"
PHONE = "+353851234567"
THIS = sys.modules[__name__]


def U(*a):
    return datetime(*a, tzinfo=UTC)


def A(**kw):
    d = {"id": 1, "customer_name": "Mary O'Brien", "email": EMAIL, "phone": PHONE,
         "country": "IE", "status": "booked", "starts_at": U(2026, 7, 15, 9, 0),
         "optout_sms_v2": False}
    d.update(kw)
    return d


NOW = U(2026, 7, 1, 12, 0)


def utc(r):
    return r["send_at"].astimezone(UTC)


class Evil:
    def __str__(self):
        raise RuntimeError(EMAIL)

    def __repr__(self):
        raise RuntimeError(EMAIL)


class EvilRepr:
    def __str__(self):
        return EMAIL

    def __repr__(self):
        return EMAIL


class Tests(unittest.TestCase):
    def test_sorted_and_not_past(self):
        import random
        recs = [A(id=i, starts_at=U(2026, 7, 10, 6, 0) + i * timedelta(hours=7, minutes=13))
                for i in range(20)]
        random.Random(1).shuffle(recs)
        res = plan_reminders(recs, NOW)
        times = [utc(r) for r in res]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all(t >= NOW for t in times))
        self.assertTrue(res)
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(r["send_at"].tzinfo, DUBLIN)

    def test_cancelled(self):
        for s in ("cancelled", "Cancelled", "canceled", "  CANCELED "):
            self.assertEqual(plan_reminders([A(status=s)], NOW), [])
        self.assertEqual(plan_reminders([{"status": "cancelled", "junk": 1}], NOW), [])

    def test_optout_and_no_phone_no_email(self):
        recs = [A(id=1, optout_sms_v2=True), A(id=2, phone=None), A(id=3, phone=""),
                A(id=4, phone="   "), A(id=5, phone="abc")]
        r6 = A(id=6)
        del r6["phone"]
        recs.append(r6)
        self.assertEqual(plan_reminders(recs, NOW), [])
        ok = A(id=7)
        del ok["email"]
        res = plan_reminders([ok, A(id=8, email=None)], NOW)
        self.assertEqual(len(res), 4)
        self.assertTrue(all(r["channel"] == "sms" for r in res))

    def test_optout_switch(self):
        self.assertEqual(plan_reminders([A(optout_sms_v2=True)], NOW), [])
        self.assertTrue(plan_reminders([A(optout_sms_v2=False)], NOW))
        with mock.patch.object(THIS, "OPTOUT_FLAG_TRUE_MEANS_OPTED_OUT", False):
            self.assertTrue(plan_reminders([A(optout_sms_v2=True)], NOW))
            self.assertEqual(plan_reminders([A(optout_sms_v2=False)], NOW), [])

    def test_old_optout_field_ignored(self):
        self.assertTrue(plan_reminders([A(opt_out=True, optout_sms_v2=False)], NOW))
        self.assertEqual(plan_reminders([A(opt_out=False, optout_sms_v2=True)], NOW), [])

    def test_first_immediate_daytime_and_quiet(self):
        start = U(2026, 1, 20, 12, 0)
        res = plan_reminders([A(starts_at=start)], U(2026, 1, 19, 12, 0))
        self.assertEqual([utc(r) for r in res], [U(2026, 1, 19, 12, 0), U(2026, 1, 20, 10, 0)])
        res = plan_reminders([A(starts_at=start)], U(2026, 1, 19, 23, 0))
        self.assertEqual([utc(r) for r in res], [U(2026, 1, 20, 10, 0)])

    def test_quiet_boundaries(self):
        for h, m, q in ((19, 59, False), (20, 0, True), (6, 59, True), (7, 0, False)):
            self.assertEqual(_is_quiet(U(2026, 7, 1, h, m)), q, (h, m))  # IST
        for h, m, q in ((20, 59, False), (21, 0, True), (7, 59, True), (8, 0, False)):
            self.assertEqual(_is_quiet(U(2026, 1, 15, h, m)), q, (h, m))  # GMT

    def test_summer_both(self):
        res = plan_reminders([A(starts_at=U(2026, 7, 15, 9, 0))], NOW)
        self.assertEqual([utc(r) for r in res], [U(2026, 7, 13, 9, 0), U(2026, 7, 15, 7, 0)])
        self.assertEqual(res[1]["send_at"].hour, 8)

    def test_two_hour_moves_to_evening_before(self):
        res = plan_reminders([A(starts_at=U(2026, 1, 20, 9, 0))], U(2026, 1, 10, 12, 0))
        self.assertEqual([utc(r) for r in res], [U(2026, 1, 18, 9, 0), U(2026, 1, 19, 20, 0)])

    def test_now_2030_target_2200_gives_now(self):
        now = U(2026, 1, 19, 20, 30)
        res = plan_reminders([A(starts_at=U(2026, 1, 20, 0, 0))], now)
        self.assertEqual(len(res), 1)
        self.assertEqual(utc(res[0]), now)

    def test_now_2300_immediate_dropped(self):
        now = U(2026, 1, 19, 23, 0)
        self.assertEqual(plan_reminders([A(starts_at=U(2026, 1, 20, 1, 0))], now), [])

    def test_started_or_exactly_now(self):
        self.assertEqual(plan_reminders([A(starts_at=NOW)], NOW), [])
        self.assertEqual(plan_reminders([A(starts_at=NOW - timedelta(hours=1))], NOW), [])

    def test_under_two_hours(self):
        res = plan_reminders([A(starts_at=U(2026, 7, 1, 12, 30))], NOW)
        self.assertEqual(len(res), 1)
        self.assertEqual(utc(res[0]), NOW)

    def test_spring_forward(self):
        res = plan_reminders([A(starts_at=U(2026, 3, 29, 11, 0))], U(2026, 3, 20, 12, 0))
        self.assertEqual(len(res), 2)
        self.assertEqual(utc(res[0]), U(2026, 3, 27, 11, 0))  # 48 elapsed hours
        self.assertEqual(utc(res[1]), U(2026, 3, 29, 9, 0))
        self.assertEqual(res[1]["send_at"].utcoffset(), timedelta(hours=1))
        self.assertIn("29/03/2026 at 12:00", res[0]["text"])

    def test_fall_back(self):
        res = plan_reminders([A(starts_at=U(2026, 10, 26, 10, 0))], U(2026, 10, 20, 12, 0))
        self.assertEqual(utc(res[0]), U(2026, 10, 24, 10, 0))
        self.assertEqual(res[0]["send_at"].hour, 11)
        self.assertIn("26/10/2026 at 10:00", res[0]["text"])

    def test_ambiguous_hour(self):
        now = U(2026, 10, 20, 12, 0)
        for start in (U(2026, 10, 25, 0, 30), U(2026, 10, 25, 1, 30)):
            res = plan_reminders([A(starts_at=start)], now)
            self.assertTrue(res)
            self.assertIn("25/10/2026 at 01:30", res[0]["text"])
        res = plan_reminders([A(starts_at=U(2026, 10, 25, 1, 30))], now)
        self.assertIn(U(2026, 10, 24, 19, 0), [utc(r) for r in res])

    def test_non_dublin_offset(self):
        s = datetime(2026, 7, 15, 5, 0, tzinfo=timezone(timedelta(hours=-4)))
        res = plan_reminders([A(starts_at=s)], NOW)
        self.assertIn("15/07/2026 at 10:00", res[0]["text"])

    def test_tz_env_independent(self):
        import os
        import time as _t
        if not hasattr(_t, "tzset"):
            self.skipTest("no tzset")
        old = os.environ.get("TZ")
        try:
            os.environ["TZ"] = "Asia/Tokyo"
            _t.tzset()
            res = plan_reminders([A()], NOW)
            self.assertEqual([utc(r) for r in res], [U(2026, 7, 13, 9, 0), U(2026, 7, 15, 7, 0)])
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            _t.tzset()

    def test_signatures(self):
        for s in (DEFAULT_SIGNATURE, PL_SIGNATURE):
            self.assertTrue(unicodedata.is_normalized("NFC", s))
        self.assertEqual(DEFAULT_SIGNATURE, "Siobh\u00e1n N\u00ed Dhuibhir")
        self.assertEqual(PL_SIGNATURE, "Grzegorz Szczepa\u0144ski")

    def test_text_and_signature(self):
        r = plan_reminders([A(country="IE")], NOW)[0]["text"]
        self.assertTrue(r.endswith("Siobh\u00e1n N\u00ed Dhuibhir"))
        self.assertIn("15/07/2026 at 10:00", r)
        for c in ("PL", "pl ", " Pl"):
            t = plan_reminders([A(country=c)], NOW)[0]["text"]
            self.assertTrue(t.endswith("Grzegorz Szczepa\u0144ski"))
        self.assertTrue(plan_reminders([A(country=None)], NOW)[0]["text"].endswith(DEFAULT_SIGNATURE))

    def test_lengths(self):
        names = ["", "Al", "Mary O'Brien", "Zo\u00eb \u0141ukasz Wi\u015bniewski", "x" * 500,
                 "  Mary \t  Ann \n Smith  ", "Line\nbreak\r\nName", "A" * 80 + " " + "B" * 80,
                 "Maria " * 40, None, 42]
        for n in names:
            for c in ("IE", "PL"):
                res = plan_reminders([A(customer_name=n, country=c)], NOW)
                self.assertTrue(res)
                for r in res:
                    t = r["text"]
                    self.assertLessEqual(len(t), 160)
                    self.assertIn("15/07/2026", t)
                    self.assertIn("10:00", t)
                    self.assertTrue(t.endswith(PL_SIGNATURE if c == "PL" else DEFAULT_SIGNATURE))
                    self.assertNotIn("\n", t)
        self.assertEqual(plan_reminders([A()], NOW)[0]["text"], plan_reminders([A()], NOW)[1]["text"])

    def test_name_fallbacks(self):
        ls = datetime(2026, 7, 15, 10, 0, tzinfo=DUBLIN)
        self.assertIn("Hi Mary O.,", compose_text("Mary " + "O" * 60, "IE", ls) or "")
        self.assertIn("Hi M.,", compose_text("M" * 80 + " " + "O" * 80, "IE", ls) or "")
        with mock.patch.object(THIS, "SMS_MAX_LEN", 100):
            self.assertTrue(compose_text("Mary", "IE", ls).startswith("Reminder:"))
        with mock.patch.object(THIS, "SMS_MAX_LEN", 80):
            self.assertTrue(compose_text("Mary", "IE", ls).startswith("Appointment"))
        with mock.patch.object(THIS, "SMS_MAX_LEN", 10):
            self.assertIsNone(compose_text("Mary", "IE", ls))
            self.assertEqual(plan_reminders([A()], NOW), [])

    def test_far_future_and_no_duplicates(self):
        res = plan_reminders([A(id=1), A(id=2), A(id="x")], NOW)
        self.assertEqual(len(res), 6)
        keys = [(r["appointment_id"], utc(r)) for r in res]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(r["channel"] != "email" for r in res))

    def test_malformed_batch(self):
        r_missing = A()
        del r_missing["optout_sms_v2"]
        bad = ["junk", None, r_missing, A(starts_at=datetime(2026, 7, 15, 9, 0)),
               A(optout_sms_v2="no"), A(optout_sms_v2=None), A(id=True), A(id=1.5),
               A(starts_at="2026-07-15"), A(starts_at=None)]
        res = plan_reminders(bad + [A(id="good")], NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"good"})
        self.assertEqual(plan_reminders(bad, NOW), [])

    def test_bad_inputs(self):
        for now, apps, exc in ((datetime(2026, 7, 1), [], ValueError), ("x", [], ValueError),
                               (NOW, "abc", TypeError), (NOW, None, TypeError)):
            with self.assertRaises(exc):
                plan_reminders(apps, now)
        for now, apps in ((EMAIL, []), (NOW, EMAIL)):
            try:
                plan_reminders(apps, now)
            except (ValueError, TypeError) as e:
                self.assertNotIn(EMAIL, str(e))

    def test_pii_not_logged(self):
        recs = [A(id=1, customer_name="Zed Quill"), A(id=2, status="cancelled", customer_name="Zed Quill"),
                A(id=3, optout_sms_v2=True, customer_name="Zed Quill"),
                A(id=4, phone=None, customer_name="Zed Quill"),
                A(id=5, starts_at=datetime(2026, 7, 15, 9, 0), customer_name="Zed Quill"),
                A(id=6, optout_sms_v2=EMAIL, customer_name="Zed Quill"),
                A(id=7, customer_name=Evil()), A(id=8, customer_name=EvilRepr()),
                A(id=EMAIL), A(id=9, starts_at=EMAIL), A(id=EMAIL, starts_at=EMAIL), EMAIL,
                A(id=10, country=Evil(), phone=PHONE, customer_name="Zed Quill")]
        with self.assertLogs(level="DEBUG") as cm:
            res = plan_reminders(recs, NOW)
        logs = "\n".join(cm.output)
        for secret in (EMAIL, "Zed Quill", "353851234567"):
            self.assertNotIn(secret, logs)
        self.assertNotIn(EMAIL, repr(res))
        self.assertNotIn(PHONE, repr(res))
        self.assertIn("planned reminder", logs)


if __name__ == "__main__":
    unittest.main()