"""Brennan Opticians appointment reminders (stdlib only, Python 3.12).

Dependency note: the server runs UTC, so zoneinfo needs the IANA database. Install the
"tzdata" package if the OS has no zoneinfo data.

Logging note: the house rule asks for one INFO line per planned reminder saying who it
goes to and how. Because of the Data Protection Commission privacy requirement, the line
carries the appointment id and the channel only, never the email address, phone number or
name. Support can look the contact up by appointment id.

Tests are included below (unittest). Run: python -m unittest <this_file>
"""
import copy
import logging
import os
import random
import time as _time
import unittest
import unicodedata
from datetime import datetime, timedelta, timezone, time as dtime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
TEMPLATE = ("Hi {name}, this is a reminder of your Brennan Opticians "
            "appointment on {date} at {time}. {signature}")
SIG_DEFAULT = "Siobh\u00e1n N\u00ed Dhuibhir"
SIG_PL = "Grzegorz Szczepa\u0144ski"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _aware(d):
    return isinstance(d, datetime) and d.tzinfo is not None and d.utcoffset() is not None


def _quiet(d):
    return d.hour >= 21 or d.hour < 8


def _at(day, hour):
    return datetime.combine(day, dtime(hour), tzinfo=DUBLIN)


def _u(d):
    return d.astimezone(UTC)


def _resolve(target, now, starts):
    """Return a Dublin-local send time, or None if there is no valid window."""
    t = _u(max(_u(target), _u(now))).astimezone(DUBLIN)
    if not _quiet(t):
        return t
    day = t.date() if t.hour >= 21 else t.date() - timedelta(days=1)
    c = _at(day, 20)
    if _u(c) >= _u(now):
        return c
    nl = _u(now).astimezone(DUBLIN)
    if not _quiet(nl):
        return nl
    day = nl.date() if nl.hour < 8 else nl.date() + timedelta(days=1)
    m = _at(day, 8)
    return m if _u(m) < _u(starts) else None


def _channel(a):
    phone, email = a.get("phone"), a.get("email")
    if isinstance(phone, str) and phone.strip() and a.get("optout_sms_v2") is False:
        return "sms"
    if isinstance(email, str) and email.strip() and "@" in email:
        return "email"
    return None


def _signature(a):
    c = a.get("country")
    return _nfc(SIG_PL if isinstance(c, str) and c.strip().upper() == "PL" else SIG_DEFAULT)


def _render(name, date, tm, sig):
    text = TEMPLATE.format(name=name, date=date, time=tm, signature=sig)
    if not name:
        text = "Hi," + text[len("Hi ,"):]
    return _nfc(text)


def _text(a, local_start, channel):
    raw = a.get("customer_name")
    words = _nfc(raw).split() if isinstance(raw, str) else []
    date = f"{local_start.day} {MONTHS[local_start.month - 1]} {local_start.year}"
    tm = f"{local_start.hour:02d}:{local_start.minute:02d}"
    sig = _signature(a)
    if channel == "email":
        return _render(" ".join(words), date, tm, sig)
    ladder = [" ".join(words)]
    if len(words) > 1:
        ladder.append(f"{words[0]} {words[-1][0]}.")
    if words:
        ladder.append(words[0])
    ladder.append("")
    text = ""
    for name in ladder:
        text = _render(name, date, tm, sig)
        if len(text) <= SMS_LIMIT:
            break
    return text


def _plan_one(a, ident, now):
    if not isinstance(a, dict):
        raise ValueError("record")
    starts = a.get("starts_at")
    if ident is None or not _aware(starts):
        raise ValueError("record")
    status = a.get("status")
    if isinstance(status, str) and status.strip().lower() in ("cancelled", "canceled"):
        log.info("skipped appointment_id=%s reason=cancelled", ident)
        return []
    starts = _u(starts)
    if starts <= now:
        log.info("skipped appointment_id=%s reason=past", ident)
        return []
    channel = _channel(a)
    if channel is None:
        log.info("skipped appointment_id=%s reason=no_channel", ident)
        return []
    text = _text(a, starts.astimezone(DUBLIN), channel)
    sends = []
    for kind, delta in (("first", timedelta(hours=48)), ("second", timedelta(hours=2))):
        s = _resolve(starts - delta, now, starts)
        if s is None:
            log.info("dropped appointment_id=%s reminder=%s reason=no_window", ident, kind)
        sends.append(s)
    first, second = sends
    if first is not None and second is not None and _u(first) >= _u(second):
        first = None
    out = []
    for kind, s in (("first", first), ("second", second)):
        if s is not None:
            log.info("reminder planned appointment_id=%s reminder=%s channel=%s send_at=%s",
                     ident, kind, channel, s.isoformat())
            out.append({"appointment_id": a["id"], "channel": channel,
                        "send_at": s, "text": text})
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_u = _u(now)
    out = []
    for i, a in enumerate(appointments):
        ident = None
        if isinstance(a, dict):
            v = a.get("id")
            if isinstance(v, (str, int)) and not isinstance(v, bool) and str(v).strip():
                ident = v
        try:
            out.extend(_plan_one(a, ident, now_u))
        except Exception:
            # Deliberately no exception text or exc_info: it could carry contact data.
            log.warning("skipped record id_or_index=%s reason=malformed",
                        ident if ident is not None else f"index:{i}")
    out.sort(key=lambda r: _u(r["send_at"]))
    return out


# ----------------------------------------------------------------- tests
def D(d, h=0, mi=0, m=11, y=2026):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def A(starts, **kw):
    base = {"id": "a1", "customer_name": "Aoife Murphy", "email": "aoife@example.com",
            "phone": "+353871234567", "country": "IE", "status": "booked",
            "starts_at": starts, "optout_sms_v2": False}
    base.update(kw)
    return base


def sends(res):
    return [r["send_at"] for r in res]


class ReminderTests(unittest.TestCase):
    def test_ex1(self):
        r = plan_reminders([A(D(20, 14))], D(2, 10))
        self.assertEqual(sends(r), [D(18, 14), D(20, 12)])

    def test_ex2(self):
        r = plan_reminders([A(D(20, 14))], D(19, 10))
        self.assertEqual(sends(r), [D(19, 10), D(20, 12)])

    def test_ex3(self):
        r = plan_reminders([A(D(20, 6, 30))], D(10, 12))
        self.assertEqual(sends(r), [D(17, 20), D(19, 20)])
        r = plan_reminders([A(D(20, 23, 30))], D(10, 12))
        self.assertEqual(sends(r), [D(18, 20), D(20, 20)])

    def test_ex4_boundaries(self):
        for start, exp in ((D(20, 23), D(20, 20)), (D(20, 10), D(20, 8)),
                           (D(20, 22, 59), D(20, 20, 59))):
            r = plan_reminders([A(start)], D(1, 12))
            self.assertEqual(r[-1]["send_at"], exp)

    def test_ex5(self):
        r = plan_reminders([A(D(20, 23, 30))], D(20, 20, 30))
        self.assertEqual(sends(r), [D(20, 20, 30)])

    def test_ex6(self):
        r = plan_reminders([A(D(21, 12))], D(20, 22))
        self.assertEqual(sends(r), [D(21, 8), D(21, 10)])

    def test_ex7(self):
        r = plan_reminders([A(D(21, 9))], D(20, 22))
        self.assertEqual(sends(r), [D(21, 8)])

    def test_ex8_no_window(self):
        with self.assertLogs(__name__, level="INFO") as cm:
            r = plan_reminders([A(D(21, 7))], D(20, 22))
        self.assertEqual(r, [])
        self.assertTrue(any("no_window" in m for m in cm.output))

    def test_ex9(self):
        self.assertEqual(sends(plan_reminders([A(D(20, 14))], D(20, 13))), [D(20, 13)])
        self.assertEqual(plan_reminders([A(D(20, 14))], D(20, 14)), [])
        self.assertEqual(plan_reminders([A(D(20, 14))], D(20, 15)), [])

    def test_ex10_mixed(self):
        starts = {"a": D(21, 12), "b": D(21, 9), "c": D(21, 7), "d": D(25, 15),
                  "e": D(22, 23, 30), "f": D(21, 22, 30)}
        now = D(20, 22)
        r = plan_reminders([A(s, id=k) for k, s in starts.items()], now)
        self.assertTrue(r)
        for x in r:
            s = x["send_at"]
            self.assertGreaterEqual(s, now)
            self.assertFalse(s.hour >= 21 or s.hour < 8)
            self.assertLess(s, starts[x["appointment_id"]])

    def test_ex11_dst_and_utc(self):
        start = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
        r = plan_reminders([A(start)], datetime(2026, 10, 1, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"], datetime(2026, 10, 24, 9, 0, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"].hour, 10)
        self.assertEqual(r[0]["send_at"].utcoffset(), timedelta(hours=1))
        start = datetime(2026, 7, 1, 23, 30, tzinfo=UTC)
        r = plan_reminders([A(start)], datetime(2026, 6, 1, tzinfo=UTC))
        self.assertIn("2 Jul 2026", r[0]["text"])
        self.assertIn("00:30", r[0]["text"])

    def test_ex12_channels(self):
        now, s = D(1, 12), D(20, 14)

        def ch(**kw):
            return [x["channel"] for x in plan_reminders([A(s, **kw)], now)]
        self.assertEqual(set(ch()), {"sms"})
        self.assertEqual(set(ch(optout_sms_v2=True)), {"email"})
        self.assertEqual(set(ch(phone=None)), {"email"})
        self.assertEqual(set(ch(phone="  ")), {"email"})
        self.assertEqual(set(ch(optout_sms_v2=None)), {"email"})
        self.assertEqual(set(ch(optout_sms_v2="false")), {"email"})
        self.assertEqual(set(ch(opt_out=True)), {"sms"})
        self.assertEqual(set(ch(opt_out=False, optout_sms_v2=True)), {"email"})
        a = A(s)
        del a["optout_sms_v2"]
        self.assertEqual({x["channel"] for x in plan_reminders([a], now)}, {"email"})
        with self.assertLogs(__name__, level="INFO") as cm:
            self.assertEqual(ch(optout_sms_v2=True, email=""), [])
        self.assertTrue(any("no_channel" in m and "a1" in m for m in cm.output))
        self.assertEqual(ch(phone=None, email=None), [])
        self.assertEqual(ch(optout_sms_v2=True, email="nope"), [])

    def test_ex13_cancelled(self):
        for st in ("cancelled", "CANCELLED", "Canceled", "canceled"):
            self.assertEqual(plan_reminders([A(D(20, 14), status=st)], D(1, 12)), [])

    def test_ex14_signature(self):
        for kw in ({}, {"optout_sms_v2": True}):
            for country, sig in (("IE", SIG_DEFAULT), (" pl ", SIG_PL), (None, SIG_DEFAULT)):
                r = plan_reminders([A(D(20, 14), country=country, **kw)], D(1, 12))
                for x in r:
                    self.assertTrue(x["text"].endswith(sig))
        r = plan_reminders([A(D(20, 14), customer_name="Aoife " + "X" * 150)], D(1, 12))
        self.assertTrue(r[0]["text"].endswith(SIG_DEFAULT))

    def test_ex15_sms_length(self):
        now = D(1, 12)
        r = plan_reminders([A(D(20, 14), customer_name="Aoife " + "X" * 150)], now)
        t = r[0]["text"]
        self.assertTrue(t.startswith("Hi Aoife X.,"))
        self.assertLessEqual(len(t), SMS_LIMIT)
        r = plan_reminders([A(D(20, 14), customer_name="A" * 200, country="PL")], now)
        t = r[0]["text"]
        self.assertTrue(t.startswith("Hi, this"))
        for part in ("20 Nov 2026", "14:00", SIG_PL):
            self.assertIn(part, t)
        self.assertLessEqual(len(t), SMS_LIMIT)
        r = plan_reminders([A(D(20, 14), customer_name="Aoife  Mary   Murphy")], now)
        self.assertTrue(r[0]["text"].startswith("Hi Aoife Mary Murphy,"))
        r = plan_reminders([A(D(20, 14), customer_name="  ")], now)
        self.assertTrue(r[0]["text"].startswith("Hi, this"))
        long = "B" * 200
        r = plan_reminders([A(D(20, 14), customer_name=long, optout_sms_v2=True)], now)
        self.assertIn(long, r[0]["text"])

    def test_ex16_sorted(self):
        days = [D(d, 13) for d in range(10, 28)]
        random.Random(1).shuffle(days)
        r = plan_reminders([A(s, id=i) for i, s in enumerate(days)], D(1, 12))
        self.assertEqual(sends(r), sorted(sends(r)))
        self.assertEqual(len(r), 2 * len(days))

    def test_ex17_privacy(self):
        S = "sentinel-9f3a@leak.example"
        S2 = "sentinel-9f3a-noat"
        now = D(1, 12)
        recs = [
            A(D(20, 14), id="c1", status="cancelled", email=S),
            A(D(20, 14), id="p1", email=S, starts_at=D(20, 14).replace(tzinfo=None)),
            A(D(20, 14), id=None, email=S),
            A(D(20, 14), id=["bad"], email=S),
            {"email": S, "starts_at": "x"},
            "not a dict " + S,
            A(D(20, 14), id="n1", phone=None, email=S2),
            A(D(20, 14), id="n2", optout_sms_v2=True, email=S2),
            A(D(2, 14), id="past", email=S, starts_at=D(1, 9)),
            A(D(20, 14), id="ok", email=S, optout_sms_v2=True),
        ]
        with self.assertLogs(level="DEBUG") as cm:
            r = plan_reminders(recs, now)
        for rec in cm.records:
            blob = rec.getMessage() + repr(rec.args) + (rec.exc_text or "") + str(rec.exc_info)
            self.assertNotIn("sentinel-9f3a", blob)
        for x in r:
            self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})
            self.assertNotIn("sentinel-9f3a", repr(x))
        self.assertEqual({x["appointment_id"] for x in r}, {"ok"})

    def test_batch_not_aborted_and_naive_now(self):
        r = plan_reminders([{"id": "x"}, A(D(20, 14))], D(1, 12))
        self.assertEqual(len(r), 2)
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 11, 1))

    def test_ex18_purity(self):
        recs = [A(D(20, 14)), A(D(21, 9), id="b", optout_sms_v2=True)]
        snap = copy.deepcopy(recs)
        base = plan_reminders(recs, D(2, 10))
        self.assertEqual(recs, snap)
        old = os.environ.get("TZ")
        try:
            os.environ["TZ"] = "Asia/Tokyo"
            _time.tzset()
            self.assertEqual(plan_reminders(recs, D(2, 10)), base)
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            _time.tzset()


if __name__ == "__main__":
    unittest.main()