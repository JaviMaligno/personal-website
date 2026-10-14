"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now). It is pure and does no I/O apart
from one INFO log line per planned reminder.

Assumptions (defaults taken from the PM requirements):
- Only optout_sms_v2 is read, and SMS is used only when it is explicitly falsy
  (False). Missing or None counts as opted out. The legacy opt_out field is
  never read.
- Status is compared case-insensitively after stripping whitespace.
- Naive datetimes (the appointment's starts_at, or now) raise ValueError
  naming only the appointment id.
- The log line carries appointment id, channel, kind and send_at only. The
  brief asks for the contact too, but that would put the email or phone number
  in the logs, which the DPC audit and the tech lead forbid. The appointment id
  is enough to trace a delivery.
- send_at is returned as an aware datetime in Europe/Dublin. The instant is
  identical to the UTC one.
- Dates use English day and month names (no locale dependence), with an
  unpadded day, e.g. "Tue 20 October 2026".
- An over-long SMS name is truncated, not ellipsised. If no room is left, the
  name and greeting are dropped.
- The tests are in this module (run: python -I module.py). They were NOT
  executed by the author, who had no tools in this session. Run them before
  relying on this.
"""
import copy
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
log = logging.getLogger("brennan.reminders")

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]
SMS_MAX = 160


def _aware(d):
    return d.tzinfo is not None and d.utcoffset() is not None


def _blank(v):
    return not isinstance(v, str) or not v.strip()


def _quiet_shift(t, now, starts):
    """Apply quiet hours (21:00-08:00 Dublin) to UTC instant t, or None to drop."""
    local = t.astimezone(DUB)
    if 8 <= local.hour < 21:
        return t
    late = local.hour >= 21
    one = timedelta(days=1)
    back_day = local.date() if late else local.date() - one
    back = datetime.combine(back_day, time(20), DUB).astimezone(UTC)
    if back >= now:
        return back
    fwd_day = local.date() + one if late else local.date()
    fwd = datetime.combine(fwd_day, time(8), DUB).astimezone(UTC)
    return fwd if fwd < starts else None


def _text(name, local_start, sig, sms):
    when = (f"{_DAYS[local_start.weekday()]} {local_start.day} "
            f"{_MONTHS[local_start.month - 1]} {local_start.year} at "
            f"{local_start.hour:02d}:{local_start.minute:02d}")

    def build(n):
        greet = f"Hi {n}, your" if n else "Your"
        return f"{greet} appointment at Brennan Opticians is on {when}. {sig}"

    name = name.strip() if isinstance(name, str) else ""
    full = build(name)
    if not sms or len(full) <= SMS_MAX:
        return full
    room = SMS_MAX - len(build("")) + 1  # build("") has no "Hi , " overhead
    room = SMS_MAX - (len(build("x")) - 1)
    short = name[:max(room, 0)].rstrip()
    return build(short) if short else build("")


def _plan_one(a, now):
    aid = a.get("id")
    starts = a["starts_at"]
    if not _aware(starts):
        raise ValueError(f"naive datetime in appointment {aid}")
    if str(a.get("status") or "").strip().lower() == "cancelled":
        return []
    starts = starts.astimezone(UTC)
    if starts <= now:
        return []
    if not _blank(a.get("phone")) and a.get("optout_sms_v2") is False:
        channel = "sms"
    elif not _blank(a.get("email")):
        channel = "email"
    else:
        return []
    sig = ("Grzegorz Szczepański"
           if str(a.get("country") or "").strip().upper() == "PL"
           else "Chevonne Nee Divver")
    text = _text(a.get("customer_name"), starts.astimezone(DUB), sig,
                 channel == "sms")
    out = []
    for order, (kind, t) in enumerate((("48h", starts - timedelta(hours=48)),
                                       ("2h", starts - timedelta(hours=2)))):
        if t < now:
            if order == 1:
                continue
            t = now
        t = _quiet_shift(t, now, starts)
        if t is None or t < now:
            continue
        out.append((t, str(aid), order, kind, channel, text))
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(UTC)
    planned = []
    for a in appointments:
        planned.extend(_plan_one(a, now))
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    result = []
    for t, aid, _, kind, channel, text in planned:
        send_at = t.astimezone(DUB)
        log.info("reminder planned: appointment=%s kind=%s channel=%s send_at=%s",
                 aid, kind, channel, send_at.isoformat())
        result.append({"appointment_id": aid, "channel": channel,
                       "send_at": send_at, "text": text})
    return result


# ---------------------------------------------------------------- tests
EMAIL = "secret@example.com"
PHONE = "+353871234567"
NOW = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)  # 10:00 Dublin


def appt(**kw):
    d = {"id": "a1", "customer_name": "Aoife", "email": EMAIL, "phone": PHONE,
         "country": "IE", "status": "booked", "optout_sms_v2": False,
         "starts_at": datetime(2026, 10, 20, 14, 0, tzinfo=DUB)}
    d.update(kw)
    return d


def dub(*a):
    return datetime(*a, tzinfo=DUB)


class PlanTests(unittest.TestCase):
    def test_channels(self):
        r = plan_reminders([appt()], NOW)
        self.assertEqual([x["channel"] for x in r], ["sms", "sms"])
        for kw in ({"optout_sms_v2": True}, {"optout_sms_v2": None},
                   {"phone": "  "}, {"phone": None}):
            r = plan_reminders([appt(**kw)], NOW)
            self.assertEqual([x["channel"] for x in r], ["email", "email"])
        d = appt()
        del d["optout_sms_v2"]
        self.assertEqual(plan_reminders([d], NOW)[0]["channel"], "email")
        self.assertEqual(plan_reminders([appt(optout_sms_v2=True, email=" ")], NOW), [])
        self.assertEqual(plan_reminders([appt(phone=None, email=None)], NOW), [])

    def test_output_keys(self):
        r = plan_reminders([appt()], NOW)[0]
        self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
        self.assertIsNotNone(r["send_at"].utcoffset())
        self.assertNotIn(EMAIL, r["text"])
        self.assertNotIn(PHONE, r["text"])

    def test_cancelled(self):
        self.assertEqual(plan_reminders([appt(status="CANCELLED")], NOW), [])

    def test_regular_times(self):
        r = plan_reminders([appt()], NOW)
        self.assertEqual(r[0]["send_at"], dub(2026, 10, 18, 14, 0))
        self.assertEqual(r[1]["send_at"], dub(2026, 10, 20, 12, 0))

    def test_quiet_boundaries(self):
        cases = [(dub(2026, 10, 20, 23, 0), dub(2026, 10, 20, 20, 0)),
                 (dub(2026, 10, 20, 22, 59), dub(2026, 10, 20, 20, 59)),
                 (dub(2026, 10, 20, 10, 0), dub(2026, 10, 20, 8, 0)),
                 (dub(2026, 10, 20, 9, 59), dub(2026, 10, 19, 20, 0))]
        for start, expected in cases:
            r = plan_reminders([appt(starts_at=start)], NOW)
            self.assertEqual(r[-1]["send_at"], expected, start)

    def test_dst_25_oct(self):
        r = plan_reminders([appt(starts_at=dub(2026, 10, 26, 10, 0))], NOW)
        self.assertEqual(r[0]["send_at"], datetime(2026, 10, 24, 10, 0, tzinfo=UTC))
        self.assertEqual(r[0]["send_at"].hour, 11)
        self.assertEqual(r[1]["send_at"], datetime(2026, 10, 26, 8, 0, tzinfo=UTC))
        self.assertIn("Mon 26 October 2026 at 10:00", r[0]["text"])

    def test_immediate_a(self):
        r = plan_reminders([appt(starts_at=dub(2026, 10, 14, 14, 0))], NOW)
        self.assertEqual(r[0]["send_at"], NOW)
        now = dub(2026, 10, 13, 22, 30)
        r = plan_reminders([appt(starts_at=dub(2026, 10, 14, 14, 0))], now)
        self.assertEqual(r[0]["send_at"], dub(2026, 10, 14, 8, 0))
        self.assertEqual(len(r), 2)
        self.assertEqual(plan_reminders([appt(starts_at=dub(2026, 10, 14, 7, 30))], now), [])
        for x in r:
            self.assertGreaterEqual(x["send_at"], now)

    def test_past_cases(self):
        self.assertEqual(plan_reminders([appt(starts_at=NOW)], NOW), [])
        r = plan_reminders([appt(starts_at=NOW + timedelta(hours=1))], NOW)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], NOW)

    def test_sms_length_and_signature(self):
        for country, sig in (("IE", "Chevonne Nee Divver"),
                             (" pl ", "Grzegorz Szczepański")):
            r = plan_reminders([appt(customer_name="Ó" * 300, country=country)], NOW)
            for x in r:
                self.assertLessEqual(len(x["text"]), 160)
                self.assertTrue(x["text"].endswith(sig))
                self.assertIn("Tue 20 October 2026", x["text"])
                self.assertIn("14:00", x["text"])
        r = plan_reminders([appt(customer_name="Ó" * 300, optout_sms_v2=True)], NOW)
        self.assertGreater(len(r[0]["text"]), 160)
        self.assertIn("Ó" * 300, r[0]["text"])

    def test_dublin_time_in_text(self):
        now = datetime(2026, 6, 20, tzinfo=UTC)
        r = plan_reminders([appt(starts_at=datetime(2026, 7, 1, 12, 30, tzinfo=UTC))], now)
        self.assertIn("1 July 2026 at 13:30", r[0]["text"])

    def test_sorting(self):
        s = dub(2026, 10, 20, 14, 0)
        r = plan_reminders([appt(id="b", starts_at=s), appt(id="a", starts_at=s)], NOW)
        self.assertEqual([x["appointment_id"] for x in r], ["a", "b", "a", "b"])
        r = plan_reminders([appt(id="late", starts_at=dub(2026, 10, 30, 14, 0)),
                            appt(id="early", starts_at=s)], NOW)
        times = [x["send_at"] for x in r]
        self.assertEqual(times, sorted(times))

    def test_no_mutation(self):
        data = [appt(), appt(id="b", optout_sms_v2=True)]
        before = copy.deepcopy(data)
        plan_reminders(data, NOW)
        self.assertEqual(data, before)

    def test_naive_errors(self):
        with self.assertRaises(ValueError) as c:
            plan_reminders([appt(id="zz9", starts_at=datetime(2026, 10, 20, 14))], NOW)
        self.assertIn("zz9", str(c.exception))
        self.assertNotIn(EMAIL, str(c.exception))
        with self.assertRaises(ValueError):
            plan_reminders([appt()], datetime(2026, 10, 13))

    def test_logging_has_no_pii(self):
        with self.assertLogs(log, "INFO") as cm:
            r = plan_reminders([appt(), appt(id="b", optout_sms_v2=True)], NOW)
        self.assertEqual(len(cm.output), len(r))
        joined = "\n".join(cm.output)
        self.assertNotIn(EMAIL, joined)
        self.assertNotIn(PHONE, joined)
        self.assertIn("appointment=a1", joined)


if __name__ == "__main__":
    unittest.main()