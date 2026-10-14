# -*- coding: utf-8 -*-
"""Brennan Opticians appointment reminders (stdlib only, Python 3.12).

Intended path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-ucc4f122/reminders.py
Tests are embedded (unittest): python -m unittest reminders
NOTE: I had no execution tool, so these tests were written but NOT run.
Needs the system tz database or the `tzdata` package for zoneinfo
("Europe/Dublin"); without either, import fails with ZoneInfoNotFoundError.

Entry point: plan_reminders(appointments, now) -> list of dicts
{appointment_id, channel, send_at (tz-aware UTC), text}. Inputs are never mutated.

FINAL SEND-TIME RULE (per reminder, all quiet-hours checks in Europe/Dublin)
  target: 48h reminder = max(start-48h, now); 2h reminder = start-2h
          (absolute durations, computed in UTC).
  1. If target is in quiet hours [21:00, 08:00), move it back to the 20:00
     immediately before it (21:00 exactly is quiet; 08:00 exactly is not).
  2. If the result is earlier than now:
       - now outside quiet hours -> send at now;
       - now inside quiet hours  -> defer to the next 08:00 Dublin.
  3. If the result is >= appointment start, drop it (reason code quiet_hours).
  4. If both reminders survive and the 2h one is less than MIN_GAP after the
     48h one (equal, or 48h one later), drop the 48h one (2h has priority).
     Exactly MIN_GAP apart keeps both.
  Starts at or before now: no reminders. Cancelled ("cancelled"/"canceled",
  case/whitespace-insensitive): none. send_at is never < now.

CHANNEL: SMS if phone non-blank and not opted out, else email if non-blank,
else nothing. Never both. Only optout_sms_v2 is read; legacy opt_out ignored.
RISK: a missing/None optout_sms_v2 is treated as NOT opted out (see
OPTOUT_MISSING_IS_OPTED_OUT; set True for the safer treatment).

SMS LENGTH: max 160 characters (len of str) including signature. Name ladder:
full name, first name + last initial, ellipsis-truncated name, initials, no
name ("Hi,"). Date, time and signature are always kept. Initials is in
practice unreachable because the ellipsis step always fits.
GSM-7 vs UCS-2 (note only): the signatures contain non-GSM characters
(ó, á, í, ń), so the SMS is sent as Unicode: 70 chars for one segment, 67 per
segment when concatenated. A 160-char text is therefore about 3 segments.
The 160 limit is unchanged.

LOGGING: module logger, no handlers. No PII at all (no names, emails, phones;
exception messages are PII-free). INFO: one line per planned reminder with
appointment id, kind and channel (the contact value is deliberately omitted
because it is PII and the no-PII requirement takes precedence over logging
the contact; the appointment id lets support trace the delivery), plus a
counter summary. DEBUG: appointment id and reason code only.
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX = 160
MIN_GAP = timedelta(hours=1)
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
SEND_HOUR = time(20, 0)
OPTOUT_MISSING_IS_OPTED_OUT = False  # risk: flip to True for the safer treatment
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _nfc(s):
    return unicodedata.normalize("NFC", s)


SIG_DEFAULT = _nfc("Siobhán Ní Dhuibhir")
SIG_PL = _nfc("Grzegorz Szczepański")


def _s(v):
    return "" if v is None else str(v).strip()


def _aware(d):
    return isinstance(d, datetime) and d.tzinfo is not None and d.utcoffset() is not None


def _opted_out(a):
    v = a.get("optout_sms_v2")
    if v is None:
        return OPTOUT_MISSING_IS_OPTED_OUT
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y")
    return bool(v)


def _quiet(dt):
    t = dt.astimezone(DUBLIN).time()
    return t >= QUIET_START or t < QUIET_END


def _shift_back(dt):
    loc = dt.astimezone(DUBLIN)
    d = loc.date()
    if loc.time() < QUIET_END:
        d -= timedelta(days=1)
    return datetime.combine(d, SEND_HOUR, tzinfo=DUBLIN).astimezone(UTC)


def _next_open(dt):
    loc = dt.astimezone(DUBLIN)
    d = loc.date()
    if loc.time() >= QUIET_START:
        d += timedelta(days=1)
    return datetime.combine(d, QUIET_END, tzinfo=DUBLIN).astimezone(UTC)


def _place(target, now, start):
    """Return (send_at or None, reason)."""
    cand = _shift_back(target) if _quiet(target) else target
    deferred = False
    if cand < now:
        if _quiet(now):
            cand, deferred = _next_open(now), True
        else:
            cand = now
    if cand >= start:
        return None, "quiet_hours"
    return cand, "ok"


def _compose(kind, name, loc, sig):
    greet = f"Hi {name}," if name else "Hi,"
    date = f"{loc.day:02d} {_MONTHS[loc.month - 1]} {loc.year}"
    hm = f"{loc:%H:%M}"
    if kind == 1:
        body = f"reminder: your Brennan Opticians appointment is on {date} at {hm}."
    else:
        body = f"this is a final reminder of your Brennan Opticians appointment on {date} at {hm}."
    return _nfc(f"{greet} {body} {sig}")


def _sms_text(kind, name, loc, sig):
    t = _compose(kind, name, loc, sig)
    if len(t) <= SMS_MAX or not name:
        return t if len(t) <= SMS_MAX else _compose(kind, "", loc, sig)
    parts = name.split()
    if len(parts) > 1:
        t = _compose(kind, f"{parts[0]} {parts[-1][0]}.", loc, sig)
        if len(t) <= SMS_MAX:
            return t
    budget = SMS_MAX - len(_compose(kind, "", loc, sig)) - 1
    if budget >= 2:
        t = _compose(kind, name[:budget - 1].rstrip() + "\u2026", loc, sig)
        if len(t) <= SMS_MAX:
            return t
    t = _compose(kind, "".join(p[0] + "." for p in parts), loc, sig)
    if len(t) <= SMS_MAX:
        return t
    return _compose(kind, "", loc, sig)


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    st = dict(planned=0, skipped_cancelled=0, skipped_past=0,
              skipped_no_contact=0, dropped_quiet_hours=0, dropped_other=0)
    out = []
    for a in appointments:
        aid = a.get("id")
        if _s(a.get("status")).lower() in ("cancelled", "canceled"):
            st["skipped_cancelled"] += 1
            log.debug("appointment_id=%s reason=cancelled", aid)
            continue
        start = a.get("starts_at")
        if not _aware(start):
            raise ValueError("starts_at must be a timezone-aware datetime")
        start = start.astimezone(UTC)
        if start <= now:
            st["skipped_past"] += 1
            log.debug("appointment_id=%s reason=past", aid)
            continue
        phone, email = _s(a.get("phone")), _s(a.get("email"))
        if phone and not _opted_out(a):
            channel = "sms"
        elif email:
            channel = "email"
        else:
            st["skipped_no_contact"] += 1
            log.debug("appointment_id=%s reason=no_contact", aid)
            continue
        r2, why2 = _place(start - timedelta(hours=2), now, start)
        r1, why1 = _place(max(start - timedelta(hours=48), now), now, start)
        if r1 and r2 and r2 - r1 < MIN_GAP:
            r1, why1 = None, "collapsed"
        for send, why in ((r1, why1), (r2, why2)):
            if send is None:
                key = "dropped_quiet_hours" if why == "quiet_hours" else "dropped_other"
                st[key] += 1
                log.debug("appointment_id=%s reason=%s", aid, why)
        name = _nfc(" ".join(_s(a.get("customer_name")).split()))
        sig = SIG_PL if _s(a.get("country")).upper() == "PL" else SIG_DEFAULT
        loc = start.astimezone(DUBLIN)
        for kind, send in ((1, r1), (2, r2)):
            if send is None:
                continue
            text = (_sms_text(kind, name, loc, sig) if channel == "sms"
                    else _compose(kind, name, loc, sig))
            out.append((send, str(aid), kind, dict(
                appointment_id=aid, channel=channel, send_at=send, text=text)))
            st["planned"] += 1
            log.info("planned reminder appointment_id=%s kind=%s channel=%s send_at=%s",
                     aid, kind, channel, send.isoformat())
    out.sort(key=lambda x: x[:3])
    log.info("reminder summary %s", " ".join(f"{k}={v}" for k, v in st.items()))
    return [x[3] for x in out]


# ----------------------------------------------------------------- tests
import copy
import unittest


def _dt(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=UTC)


def _ap(**kw):
    base = dict(id="a1", customer_name="Mary Murphy", email="m@example.com",
                phone="+353851234567", country="IE", status="booked",
                starts_at=_dt(2026, 6, 15, 10), optout_sms_v2=False)
    base.update(kw)
    return base


def _plan(*aps, now):
    return plan_reminders(list(aps), now)


S = "Siobhán Ní Dhuibhir"
P = "Grzegorz Szczepański"


class Tests(unittest.TestCase):
    def test_summer_texts_and_times(self):
        r = _plan(_ap(), now=_dt(2026, 6, 1, 12))
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 6, 13, 10), _dt(2026, 6, 15, 8)])
        self.assertEqual(r[0]["text"], "Hi Mary Murphy, reminder: your Brennan Opticians appointment is on 15 Jun 2026 at 11:00. " + S)
        self.assertEqual(r[1]["text"], "Hi Mary Murphy, this is a final reminder of your Brennan Opticians appointment on 15 Jun 2026 at 11:00. " + S)
        self.assertEqual({x["channel"] for x in r}, {"sms"})

    def test_winter_utc_equals_local(self):
        r = _plan(_ap(starts_at=_dt(2026, 1, 20, 10)), now=_dt(2026, 1, 1))
        self.assertIn("on 20 Jan 2026 at 10:00.", r[1]["text"])

    def test_spring_forward(self):
        r = _plan(_ap(starts_at=_dt(2026, 3, 30, 9)), now=_dt(2026, 3, 20, 12))
        self.assertEqual(r[0]["send_at"], _dt(2026, 3, 28, 9))
        self.assertEqual(r[0]["send_at"].astimezone(DUBLIN).hour, 9)
        self.assertEqual(r[1]["send_at"], _dt(2026, 3, 30, 7))  # 08:00 local, not quiet
        self.assertIn("30 Mar 2026 at 10:00.", r[1]["text"])

    def test_fall_back(self):
        r = _plan(_ap(starts_at=_dt(2026, 10, 26, 10)), now=_dt(2026, 10, 15, 12))
        self.assertEqual(r[0]["send_at"], _dt(2026, 10, 24, 10))
        self.assertEqual(r[0]["send_at"].astimezone(DUBLIN).hour, 11)
        self.assertEqual(r[1]["send_at"], _dt(2026, 10, 26, 8))
        self.assertIn("26 Oct 2026 at 10:00.", r[1]["text"])

    def test_pl_signature(self):
        r = _plan(_ap(country=" pl "), now=_dt(2026, 6, 1))
        self.assertTrue(all(x["text"].endswith(". " + P) for x in r))

    def test_truncation_160_161(self):
        base = len(_plan(_ap(customer_name=""), now=_dt(2026, 6, 1))[1]["text"])
        k = SMS_MAX - base - 1
        t = _plan(_ap(customer_name="A" * k), now=_dt(2026, 6, 1))[1]["text"]
        self.assertEqual(len(t), 160)
        self.assertIn("A" * k, t)
        t = _plan(_ap(customer_name="A" * (k + 1)), now=_dt(2026, 6, 1))[1]["text"]
        self.assertEqual(len(t), 160)
        self.assertIn("\u2026", t)
        self.assertTrue(t.endswith(S))

    def test_ladder_initial_and_huge(self):
        t = _plan(_ap(customer_name="Bartholomew " + "X" * 200), now=_dt(2026, 6, 1))[1]["text"]
        self.assertTrue(t.startswith("Hi Bartholomew X.,"))
        t = _plan(_ap(customer_name="Q" * 100000), now=_dt(2026, 6, 1))[1]["text"]
        self.assertLessEqual(len(t), 160)

    def test_email_not_limited(self):
        r = _plan(_ap(phone="", customer_name="N" * 400), now=_dt(2026, 6, 1))
        self.assertEqual(r[0]["channel"], "email")
        self.assertGreater(len(r[0]["text"]), 160)

    def test_worst_case_no_name(self):
        for nm in (None, "", "   "):
            for x in _plan(_ap(customer_name=nm, country="PL"), now=_dt(2026, 6, 1)):
                self.assertLessEqual(len(x["text"]), 160)
                self.assertTrue(x["text"].startswith("Hi, "))

    def test_quiet_boundaries(self):
        n = _dt(2026, 6, 1)
        # r2 target at 21:00 local (20:00 UTC) -> 20:00 local same day
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 22)), now=n)
        self.assertEqual(r[-1]["send_at"], _dt(2026, 6, 15, 19))
        self.assertEqual(r[0]["send_at"], _dt(2026, 6, 13, 19))
        # 20:59 stays
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 21, 59)), now=n)
        self.assertEqual(r[-1]["send_at"], _dt(2026, 6, 15, 19, 59))
        # 08:00 stays
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 9)), now=n)
        self.assertEqual(r[-1]["send_at"], _dt(2026, 6, 15, 7))
        # 07:59 -> previous day 20:00 local
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 8, 59)), now=n)
        self.assertEqual(r[-1]["send_at"], _dt(2026, 6, 14, 19))

    def test_past_48h_sent_now(self):
        n = _dt(2026, 6, 14, 10)
        r = _plan(_ap(), now=n)
        self.assertEqual([x["send_at"] for x in r], [n, _dt(2026, 6, 15, 8)])

    def test_cancelled_variants(self):
        for s in ("cancelled", "CANCELLED", " Canceled ", "canceled"):
            self.assertEqual(_plan(_ap(status=s), now=_dt(2026, 6, 1)), [])

    def test_optout_and_contacts(self):
        n = _dt(2026, 6, 1)
        self.assertEqual(_plan(_ap(optout_sms_v2=True), now=n)[0]["channel"], "email")
        self.assertEqual(_plan(_ap(optout_sms_v2=False, opt_out=True), now=n)[0]["channel"], "sms")
        self.assertEqual(_plan(_ap(optout_sms_v2=True, email=" "), now=n), [])
        a = _ap(); del a["optout_sms_v2"]
        self.assertEqual(_plan(a, now=n)[0]["channel"], "sms")
        self.assertEqual(_plan(_ap(optout_sms_v2=None), now=n)[0]["channel"], "sms")
        self.assertEqual(_plan(_ap(phone="  "), now=n)[0]["channel"], "email")
        self.assertEqual(_plan(_ap(phone=None, email=None), now=n), [])
        self.assertEqual(_plan(_ap(phone="", email="\t"), now=n), [])

    def test_started(self):
        s = _dt(2026, 6, 15, 10)
        self.assertEqual(_plan(_ap(), now=s), [])
        self.assertEqual(_plan(_ap(), now=s + timedelta(minutes=1)), [])

    def test_deferral_and_gap(self):
        n = _dt(2026, 6, 14, 22, 30)  # 23:30 local, quiet
        r = _plan(_ap(), now=n)  # r1 deferred to 07:00 UTC, r2 08:00 UTC: exactly MIN_GAP
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 6, 15, 7), _dt(2026, 6, 15, 8)])
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 9)), now=n)  # same send_at -> collapse
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 6, 15, 7)])
        self.assertIn("final reminder", r[0]["text"])

    def test_drop_when_deferral_after_start(self):
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 6)), now=_dt(2026, 6, 14, 22, 30))
        self.assertEqual(r, [])

    def test_start_within_2h_sends_now(self):
        n = _dt(2026, 6, 15, 8, 30)
        r = _plan(_ap(starts_at=_dt(2026, 6, 15, 9, 30)), now=n)
        self.assertEqual([x["send_at"] for x in r], [n])

    def test_sorting(self):
        r = _plan(_ap(id="b"), _ap(id="a"), now=_dt(2026, 6, 1))
        self.assertEqual([x["appointment_id"] for x in r], ["a", "b", "a", "b"])
        r = _plan(_ap(id=9), _ap(id=10), now=_dt(2026, 6, 1))
        self.assertEqual([x["appointment_id"] for x in r], [10, 9, 10, 9])

    def test_no_mutation(self):
        aps = [_ap(), _ap(id="z", status="Canceled")]
        before = copy.deepcopy(aps)
        _plan(*aps, now=_dt(2026, 6, 1))
        self.assertEqual(aps, before)

    def test_naive_now_no_pii(self):
        with self.assertRaises(ValueError) as c:
            _plan(_ap(), now=datetime(2026, 6, 1))
        m = str(c.exception)
        for bad in ("Mary", "example.com", "353"):
            self.assertNotIn(bad, m)

    def test_no_pii_in_logs(self):
        aps = [_ap(), _ap(id="c", status="cancelled"), _ap(id="n", phone="", email="")]
        with self.assertLogs(level="DEBUG") as cm:
            _plan(*aps, now=_dt(2026, 6, 1))
        out = "\n".join(cm.output)
        for bad in ("m@example.com", "Mary", "Murphy", "353851234567"):
            self.assertNotIn(bad, out)
        self.assertIn("appointment_id=a1", out)

    def test_sweep(self):
        starts = [_dt(2026, 3, 30, 9), _dt(2026, 10, 26, 10), _dt(2026, 6, 15, 22), _dt(2026, 6, 15, 6)]
        for s in starts:
            aps = [_ap(starts_at=s), _ap(id="l", starts_at=s, customer_name="N" * 300, country="PL"),
                   _ap(id="e", starts_at=s, phone="")]
            n = s - timedelta(hours=60)
            while n < s + timedelta(hours=1):
                for x in plan_reminders(aps, n):
                    self.assertGreaterEqual(x["send_at"], n)
                    self.assertLess(x["send_at"], s)
                    self.assertFalse(_quiet(x["send_at"]))
                    if x["channel"] == "sms":
                        self.assertLessEqual(len(x["text"]), 160)
                n += timedelta(minutes=17)


if __name__ == "__main__":
    unittest.main()