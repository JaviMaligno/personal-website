"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now).

Defaults chosen where the brief was silent (to relay to the client):
- Window edges: quiet window is [21:00, 08:00) Dublin local, so 21:00 is quiet
  and 08:00 is allowed. 20:59 is allowed and 07:59 is quiet.
- Quiet-window vs not-in-past conflict: a shifted time earlier than now moves
  forward to the next 08:00 Dublin, if that is before starts_at, else the
  reminder is dropped.
- Passed 2h point: the 2h reminder is omitted. If the 48h point has also
  passed and the start is still in the future, one immediate reminder is sent
  at now (subject to quiet rules). A 48h reminder landing at or after the 2h
  send time is dropped. starts_at <= now gives nothing.
- Date format: "Tue 27 Oct 2026 at 14:30" (English names, Dublin local time).
- SMS length: counted with len() on Python characters, limit 160. The
  signatures contain non-GSM-7 characters (for example a-acute, n-acute), so
  carriers will send these as UCS-2, where a single segment holds only 70
  characters. A 160 character message may therefore bill as several segments.
- Missing/None/non-True-or-False optout_sms_v2: treated as opted out (email).
  Only an explicit False allows SMS. The legacy opt_out field is never read.
- Phone usable: a string with at least 7 digits. Email usable: contains "@".
- Other statuses: only "cancelled" (trimmed, case-insensitive) suppresses
  reminders. Any other status is treated as active.
- Logging: one INFO line per planned reminder with appointment id, kind,
  channel and a contact reference ("phone on file" / "email on file"). The
  actual address, phone and name are never logged (DPC audit), so the house
  rule's "contact" is logged as that non-identifying reference.
- Naive datetimes (now or starts_at) raise ValueError. Other malformed records
  are skipped and only their id is logged.
"""
import logging
import os
import time as _time
import unittest
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
log = logging.getLogger("brennan.reminders")
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SMS_LIMIT = 160


class _Naive(ValueError):
    pass


def _aware(dt):
    return dt.tzinfo is not None and dt.utcoffset() is not None


def _quiet(send, now, starts):
    """Apply the quiet window; return adjusted datetime or None to drop."""
    loc = send.astimezone(DUB)
    h = loc.hour
    if 8 <= h < 21:
        return send
    day = loc.date() if h >= 21 else loc.date() - timedelta(days=1)
    back = datetime.combine(day, time(20, 0), DUB)
    if back >= now:
        return back
    nxt_day = loc.date() + timedelta(days=1) if h >= 21 else loc.date()
    fwd = datetime.combine(nxt_day, time(8, 0), DUB)
    return fwd if fwd < starts else None


def _text(name, starts, sig, limit):
    loc = starts.astimezone(DUB)
    when = (f"{DAYS[loc.weekday()]} {loc.day} {MONTHS[loc.month - 1]} "
            f"{loc.year} at {loc:%H:%M}")
    parts = (name or "").split()
    cands = [" ".join(parts)] if parts else []
    if len(parts) > 1:
        cands.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        cands += [parts[0], parts[0][0] + "."]
    cands.append("")
    msg = ""
    for n in cands:
        greet = f"Hi {n}, " if n else "Hello, "
        msg = (f"{greet}this is a reminder of your Brennan Opticians "
               f"appointment on {when}. {sig}")
        if limit is None or len(msg) <= limit:
            break
    return msg


def _plan_one(rec, now):
    aid = rec["id"]
    starts = rec["starts_at"]
    if not isinstance(starts, datetime):
        raise TypeError("starts_at")
    if not _aware(starts):
        raise _Naive("naive starts_at")
    status = str(rec.get("status") or "").strip().lower()
    if status == "cancelled" or starts <= now:
        return []

    phone = rec.get("phone")
    email = rec.get("email")
    phone_ok = isinstance(phone, str) and sum(c.isdigit() for c in phone) >= 7
    if phone_ok and rec.get("optout_sms_v2") is False:
        channel = "sms"
    else:
        channel = "email"
        if not (isinstance(email, str) and "@" in email):
            return []
    name = rec.get("customer_name")
    name = name if isinstance(name, str) else ""
    country = str(rec.get("country") or "").strip().upper()
    sig = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"

    t48, t2 = starts - timedelta(hours=48), starts - timedelta(hours=2)
    raw = [(0, max(t48, now))]
    if t2 >= now:
        raw.append((1, t2))
    else:
        raw = [(0, now)]
    adj = {}
    for kind, when in raw:
        a = _quiet(when, now, starts)
        if a is not None:
            adj[kind] = a
    if 0 in adj and 1 in adj and adj[0] >= adj[1]:
        del adj[0]

    text = _text(name, starts, sig, SMS_LIMIT if channel == "sms" else None)
    ref = "phone on file" if channel == "sms" else "email on file"
    out = []
    for kind, when in adj.items():
        send_at = when.astimezone(DUB)
        log.info("reminder planned appointment_id=%s kind=%s channel=%s "
                 "contact=%s send_at=%s", aid, "48h" if kind == 0 else "2h",
                 channel, ref, send_at.isoformat())
        out.append((send_at, str(aid), kind, {
            "appointment_id": aid, "channel": channel,
            "send_at": send_at, "text": text}))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    planned = []
    for rec in appointments:
        try:
            planned.extend(_plan_one(rec, now))
        except _Naive:
            raise
        except Exception:
            rid = rec.get("id") if isinstance(rec, dict) else None
            log.warning("skipping malformed appointment id=%s", rid)
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    return [p[3] for p in planned]


# ----------------------------------------------------------------- tests
def _d(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUB)


def _rec(**kw):
    r = {"id": "A1", "customer_name": "Aoife Murphy", "email": "aoife@example.com",
         "phone": "+353851234567", "country": "IE", "status": "booked",
         "starts_at": _d(2026, 10, 27, 14, 30), "optout_sms_v2": False}
    r.update(kw)
    return r


class PlanTests(unittest.TestCase):
    NOW = _d(2026, 10, 13, 10, 0)

    def test_two_hour_first(self):
        r = plan_reminders([_rec()], self.NOW)
        self.assertEqual([x["send_at"] for x in r],
                         [_d(2026, 10, 25, 14, 30), _d(2026, 10, 27, 12, 30)])
        self.assertTrue(all(x["send_at"].tzinfo for x in r))
        self.assertIn("Tue 27 Oct 2026 at 14:30", r[0]["text"])

    def test_cancelled(self):
        self.assertEqual(plan_reminders([_rec(status=" Cancelled ")], self.NOW), [])

    def test_30h_immediate_plus_2h(self):
        now = _d(2026, 10, 26, 8, 30)
        r = plan_reminders([_rec()], now)
        self.assertEqual([x["send_at"] for x in r], [now, _d(2026, 10, 27, 12, 30)])

    def test_1h_none_and_past_none(self):
        self.assertEqual(plan_reminders([_rec()], _d(2026, 10, 27, 13, 30)), [])
        self.assertEqual(plan_reminders([_rec()], _d(2026, 10, 28, 9, 0)), [])

    def test_naive_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([_rec(starts_at=datetime(2026, 10, 27, 14, 30))], self.NOW)
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13))

    def test_channel_matrix(self):
        cases = [
            (dict(), "sms"),
            (dict(optout_sms_v2=True), "email"),
            (dict(optout_sms_v2=None), "email"),
            (dict(phone=""), "email"),
            (dict(phone="  "), "email"),
            (dict(phone=None), "email"),
            (dict(phone="", email=""), None),
            (dict(optout_sms_v2=True, email=None), None),
        ]
        for kw, want in cases:
            with self.subTest(kw=kw):
                r = plan_reminders([_rec(**kw)], self.NOW)
                if want is None:
                    self.assertEqual(r, [])
                else:
                    self.assertEqual({x["channel"] for x in r}, {want})
                    self.assertEqual(len(r), 2)

    def test_opt_out_ignored_and_missing_flag(self):
        r = plan_reminders([_rec(opt_out=True)], self.NOW)
        self.assertEqual(r[0]["channel"], "sms")
        rec = _rec(opt_out=False)
        del rec["optout_sms_v2"]
        self.assertEqual(plan_reminders([rec], self.NOW)[0]["channel"], "email")

    def test_quiet_boundaries(self):
        far, early = _d(2020, 1, 1), _d(2030, 1, 1)
        for (y, m, dd), off in (((2026, 11, 10), 0), ((2026, 7, 10), 1),
                                ((2026, 10, 25), 0), ((2027, 3, 29), 1)):
            with self.subTest(date=(y, m, dd)):
                q = lambda h, mi: _quiet(_d(y, m, dd, h, mi), far, early)
                self.assertEqual(q(20, 59), _d(y, m, dd, 20, 59))
                self.assertEqual(q(21, 0), _d(y, m, dd, 20, 0))
                self.assertEqual(q(8, 0), _d(y, m, dd, 8, 0))
                prev = q(7, 59)
                self.assertEqual(prev.astimezone(DUB).replace(tzinfo=None).time(),
                                 time(20, 0))
                self.assertEqual(prev.astimezone(DUB).date(),
                                 _d(y, m, dd).date() - timedelta(days=1))
                self.assertEqual(q(21, 0).utcoffset(), timedelta(hours=off))

    def test_quiet_forward_and_drop(self):
        starts = _d(2026, 11, 12, 12, 0)
        now = _d(2026, 11, 10, 22, 0)
        self.assertEqual(_quiet(now, now, starts), _d(2026, 11, 11, 8, 0))
        self.assertIsNone(_quiet(now, now, _d(2026, 11, 11, 7, 0)))

    def test_long_name_sms(self):
        name = "Alexandria " + "X" * 89
        self.assertEqual(len(name), 100)
        for x in plan_reminders([_rec(customer_name=name)], self.NOW):
            self.assertLessEqual(len(x["text"]), 160)
            self.assertIn("Tue 27 Oct 2026 at 14:30", x["text"])
            self.assertTrue(x["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_pl_and_nameless(self):
        r = plan_reminders([_rec(country=" pl ", customer_name="")], self.NOW)
        self.assertTrue(r[0]["text"].startswith("Hello, "))
        self.assertTrue(r[0]["text"].endswith("Grzegorz Szczepański"))

    def test_no_pii_in_logs(self):
        with self.assertLogs("brennan.reminders", "INFO") as cm:
            plan_reminders([_rec(optout_sms_v2=True), _rec(id="B", starts_at=None)],
                           self.NOW)
        out = "\n".join(cm.output)
        for s in ("aoife", "example.com", "Aoife", "Murphy", "353851234567"):
            self.assertNotIn(s, out)
        self.assertIn("appointment_id=A1", out)
        self.assertIn("id=B", out)

    def test_sorting(self):
        a = _rec(id="B", starts_at=_d(2026, 10, 27, 14, 30))
        b = _rec(id="A", starts_at=_d(2026, 10, 27, 14, 30))
        c = _rec(id="C", starts_at=_d(2026, 10, 20, 11, 0))
        r = plan_reminders([a, b, c], self.NOW)
        keys = [(x["send_at"], x["appointment_id"]) for x in r]
        self.assertEqual(keys, sorted(keys))

    def test_no_mutation(self):
        rec = _rec()
        before = dict(rec)
        plan_reminders([rec], self.NOW)
        self.assertEqual(rec, before)

    def test_host_timezone_independence(self):
        old = os.environ.get("TZ")
        results = []
        try:
            for tz in ("UTC", "Pacific/Auckland", "America/New_York"):
                os.environ["TZ"] = tz
                _time.tzset()
                results.append(plan_reminders([_rec()], self.NOW))
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            _time.tzset()
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])


if __name__ == "__main__":
    unittest.main()