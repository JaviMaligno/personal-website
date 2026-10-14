"""Brennan Opticians appointment reminder planner (single file: module plus unittest tests).

requirements.txt (create alongside this file):
    tzdata

Run the tests (from the directory containing this file, saved as brennan_reminders.py):
    python -m unittest brennan_reminders -v
    (pytest brennan_reminders.py also works)

I could not run anything or create files (no tools), so the tests are unrun here.
Please run them and confirm.

Summary, deviations and open points:
- Deviation: the house rule asks for the contact in the INFO line, but the DPC audit
  forbids logging emails and phones are discouraged. Each INFO line therefore has the
  appointment id, channel, send_at and a contact descriptor ("email on file" or
  "phone on file"), never the address or number.
- Tests live in this file because the module is delivered as one file; split them out
  if you prefer test_*.py.
- Open points for the client:
  1. Forward-to-08:00 deviation: when "now" is inside quiet hours, the send moves
     forward to the next 08:00 so nothing is sent in the past.
  2. A missing, None or non-bool optout_sms_v2 is treated as opted out (email).
  3. The output has no "kind" field, so the caller must dedupe reminders itself.
  4. A Polish SMS containing the n-acute character is UCS-2 (70 chars per segment),
     so it may split into several billable segments.
  5. Are Krakow appointment times entered in Dublin time?
  6. Unknown statuses (completed, no_show, ...) still get reminders. Only "cancelled"
     is skipped.
"""
import copy
import logging
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone, time as dtime
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_LEN = 160
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepa\u0144ski"
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

logger = logging.getLogger(__name__)


def _is_aware(value):
    return isinstance(value, datetime) and value.utcoffset() is not None


def _in_window(utc_dt):
    h = utc_dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _shift_back(utc_dt):
    loc = utc_dt.astimezone(DUBLIN)
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    return datetime.combine(day, dtime(20, 0), DUBLIN).astimezone(UTC)


def _forward(utc_dt):
    loc = utc_dt.astimezone(DUBLIN)
    day = loc.date() + timedelta(days=1) if loc.hour >= 21 else loc.date()
    return datetime.combine(day, dtime(8, 0), DUBLIN).astimezone(UTC)


def _resolve(raw, now, starts):
    t = raw
    if _in_window(t):
        t = _shift_back(t)
    if t < now:
        t = now
    if _in_window(t):
        t = _forward(t)
    return t if t < starts else None


def _clean_name(name):
    if not isinstance(name, str):
        return ""
    out = "".join(" " if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") else c
                  for c in name)
    return " ".join(out.split())


def _signature(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIG_PL
    return SIG_DEFAULT


def _compose(name, date_s, time_s, sig):
    greeting = f"Hi {name}," if name else "Hello,"
    return (f"{greeting} your appointment at Brennan Opticians is on "
            f"{date_s} at {time_s}. {sig}")


def _build_text(name, date_s, time_s, sig, is_sms):
    if not is_sms:
        return _compose(name, date_s, time_s, sig)
    first = name.split(" ")[0] if name else ""
    candidates = [name, first]
    candidates += [first[:k] + "\u2026" for k in range(len(first) - 1, 0, -1)]
    if first:
        candidates.append(first[0] + ".")
    candidates.append("")
    for cand in candidates:
        text = _compose(cand, date_s, time_s, sig)
        if len(text) <= SMS_MAX_LEN:
            return text
    return _compose("", date_s, time_s, sig)


def _plan_one(appt, now):
    """Return list of (send_utc, appointment_id, channel, text, contact_desc)."""
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        return []
    starts = appt["starts_at"].astimezone(UTC)
    if starts <= now:
        return []

    phone = appt.get("phone")
    has_phone = isinstance(phone, str) and bool(phone.strip())
    if has_phone and appt.get("optout_sms_v2") is False:
        channel, contact = "sms", "phone on file"
    else:
        email = appt.get("email")
        if not (isinstance(email, str) and email.strip()):
            return []
        channel, contact = "email", "email on file"

    r1 = starts - timedelta(hours=48)
    r2 = starts - timedelta(hours=2)
    if now >= r2:
        raws = [now]
    elif now >= r1:
        raws = [now, r2]
    else:
        raws = [r1, r2]

    local = starts.astimezone(DUBLIN)
    date_s = f"{DAYS[local.weekday()]} {local.day} {MONTHS[local.month - 1]} {local.year}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    text = _build_text(_clean_name(appt.get("customer_name")), date_s, time_s,
                       _signature(appt.get("country")), channel == "sms")

    result, seen = [], set()
    for raw in raws:
        t = _resolve(raw, now, starts)
        if t is None or t in seen:
            continue
        seen.add(t)
        result.append((t, appt["id"], channel, text, contact))
    return result


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        if not isinstance(appt, dict):
            logger.warning("Skipping appointment id=%s: invalid field '%s'", "<unknown>", "appointment")
            continue
        aid = appt.get("id")
        if aid is None or aid == "":
            logger.warning("Skipping appointment id=%s: invalid field '%s'", "<unknown>", "id")
            continue
        if not _is_aware(appt.get("starts_at")):
            logger.warning("Skipping appointment id=%s: invalid field '%s'", aid, "starts_at")
            continue
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda p: p[0])
    out = []
    for t, aid, channel, text, contact in planned:
        send_at = t.astimezone(DUBLIN)
        logger.info("Planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                    aid, channel, contact, send_at.isoformat())
        out.append({"appointment_id": aid, "channel": channel,
                    "send_at": send_at, "text": text})
    logger.info("Planned %d reminders from %d appointments", len(out), len(appointments))
    return out


# ----------------------------------------------------------------- tests

def D(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=DUBLIN)


def A(**kw):
    base = {"id": "a1", "customer_name": "Aoife Murphy", "email": "known.person@example.com",
            "phone": "+353871234567", "country": "IE", "status": "confirmed",
            "starts_at": D(2026, 10, 18, 14), "optout_sms_v2": False}
    base.update(kw)
    return base


class PlannerTests(unittest.TestCase):
    def test_cancelled_variants(self):
        for s in ("cancelled", " CANCELLED ", "Cancelled\n"):
            self.assertEqual(plan_reminders([A(status=s)], D(2026, 10, 13, 10)), [])

    def test_started(self):
        now = D(2026, 10, 18, 14)
        self.assertEqual(plan_reminders([A()], now), [])
        self.assertEqual(plan_reminders([A()], now + timedelta(minutes=1)), [])

    def test_five_days_out(self):
        out = plan_reminders([A()], D(2026, 10, 13, 10))
        self.assertEqual([o["send_at"] for o in out], [D(2026, 10, 16, 14), D(2026, 10, 18, 12)])
        self.assertEqual(set(out[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertIn("Sun 18 Oct 2026", out[0]["text"])
        self.assertIn("14:00", out[0]["text"])

    def test_48h_passed(self):
        now = D(2026, 10, 13, 12)
        out = plan_reminders([A(starts_at=D(2026, 10, 14, 14))], now)
        self.assertEqual([o["send_at"] for o in out], [now, D(2026, 10, 14, 12)])

    def test_quiet_boundaries(self):
        cases = [((3, 20, 59), (3, 20, 59)), ((3, 21, 0), (3, 20, 0)),
                 ((3, 23, 30), (3, 20, 0)), ((4, 0, 0), (3, 20, 0)),
                 ((4, 7, 59), (3, 20, 0)), ((4, 8, 0), (4, 8, 0))]
        for (d, h, m), (ed, eh, em) in cases:
            raw = D(2026, 11, d, h, m)
            starts = raw.astimezone(UTC) + timedelta(hours=48)
            out = plan_reminders([A(starts_at=starts)], raw - timedelta(hours=50))
            self.assertEqual(out[0]["send_at"], D(2026, 11, ed, eh, em), (d, h, m))

    def test_2h_point_in_morning_window(self):
        out = plan_reminders([A(starts_at=D(2026, 11, 4, 9))], D(2026, 11, 1, 12))
        self.assertEqual([o["send_at"] for o in out], [D(2026, 11, 2, 9), D(2026, 11, 3, 20)])

    def test_now_before_raw_in_window(self):
        out = plan_reminders([A(starts_at=D(2026, 11, 4, 0))], D(2026, 11, 3, 20, 30))
        self.assertEqual([o["send_at"] for o in out], [D(2026, 11, 3, 20, 30)])

    def test_now_in_window_moves_forward(self):
        out = plan_reminders([A(starts_at=D(2026, 11, 4, 10))], D(2026, 11, 3, 23))
        self.assertEqual([o["send_at"] for o in out], [D(2026, 11, 4, 8)])

    def test_early_appointment_one_at_0800(self):
        out = plan_reminders([A(starts_at=D(2026, 11, 4, 8, 30))], D(2026, 11, 3, 22))
        self.assertEqual([o["send_at"] for o in out], [D(2026, 11, 4, 8)])

    def test_appointment_at_0800_now_in_window_none(self):
        self.assertEqual(plan_reminders([A(starts_at=D(2026, 11, 4, 8))], D(2026, 11, 3, 22)), [])

    def test_dst_autumn(self):
        out = plan_reminders([A(starts_at=D(2026, 10, 26, 10))], D(2026, 10, 20, 9))
        self.assertEqual(out[0]["send_at"], datetime(2026, 10, 24, 10, 0, tzinfo=UTC))
        self.assertEqual(out[0]["send_at"].hour, 11)

    def test_dst_spring(self):
        out = plan_reminders([A(starts_at=D(2027, 3, 29, 12))], D(2027, 3, 20, 9))
        self.assertEqual(out[0]["send_at"], datetime(2027, 3, 27, 11, 0, tzinfo=UTC))
        self.assertEqual(out[1]["send_at"], datetime(2027, 3, 29, 10, 0, tzinfo=UTC))

    def test_input_zone_independent(self):
        now = D(2026, 10, 20, 9)
        base = plan_reminders([A(starts_at=D(2026, 10, 26, 10))], now)
        for tz in (UTC, timezone(timedelta(hours=5))):
            out = plan_reminders([A(starts_at=D(2026, 10, 26, 10).astimezone(tz))],
                                 now.astimezone(tz))
            self.assertEqual(out, base)
            self.assertEqual(out[0]["send_at"].tzinfo, DUBLIN)

    def test_channel_matrix(self):
        now = D(2026, 10, 13, 10)
        for phone in (None, "", "  ", "+353871234567"):
            for opt in (False, True, None, "MISSING", "false", 0, 1):
                for email in ("a@b.ie", "", None, "MISSING"):
                    ap = A(phone=phone, email=email)
                    if opt == "MISSING" and False:
                        pass
                    ap["optout_sms_v2"] = opt
                    if email == "MISSING":
                        del ap["email"]
                    sms = bool(phone and phone.strip()) and opt is False
                    out = plan_reminders([ap], now)
                    if sms:
                        self.assertEqual({o["channel"] for o in out}, {"sms"})
                    elif email in ("a@b.ie",):
                        self.assertEqual({o["channel"] for o in out}, {"email"})
                    else:
                        self.assertEqual(out, [])
                    self.assertIn(len(out), (0, 2))
        ap = A()
        del ap["optout_sms_v2"]
        self.assertEqual(plan_reminders([ap], now)[0]["channel"], "email")

    def test_stale_opt_out_ignored(self):
        now = D(2026, 10, 13, 10)
        self.assertEqual(plan_reminders([A(opt_out=True)], now)[0]["channel"], "sms")
        self.assertEqual(plan_reminders([A(opt_out=False, optout_sms_v2=True)], now)[0]["channel"], "email")

    def test_sms_lengths(self):
        now = D(2026, 10, 13, 10)
        names = ["Ab" * 60, "Firstname " + "x" * 110, "", "A" * 120]
        for country in ("IE", "PL"):
            for n in names:
                t = plan_reminders([A(customer_name=n, country=country)], now)[0]["text"]
                self.assertLessEqual(len(t), SMS_MAX_LEN)
                self.assertTrue(t.endswith(SIG_PL if country == "PL" else SIG_DEFAULT))
                self.assertIn("Sun 18 Oct 2026", t)
                self.assertIn("14:00", t)

    def test_short_name_kept_and_ladder(self):
        now = D(2026, 10, 13, 10)
        t = plan_reminders([A(customer_name="Aoife Murphy")], now)[0]["text"]
        self.assertIn("Hi Aoife Murphy,", t)
        t = plan_reminders([A(customer_name="Aoife " + "m" * 110)], now)[0]["text"]
        self.assertIn("Hi Aoife,", t)

    def test_empty_name_template_fits_worst_case(self):
        worst = max((f"{d} {dd} {m} 2026" for d in DAYS for m in MONTHS for dd in (28, 30)), key=len)
        self.assertLessEqual(len(_compose("", worst, "23:59", SIG_PL)), SMS_MAX_LEN)

    def test_name_sanitised(self):
        t = plan_reminders([A(customer_name="Ao\nife\x00\tMurphy")], D(2026, 10, 13, 10))[0]["text"]
        self.assertIn("Hi Ao ife Murphy,", t)
        t = plan_reminders([A(customer_name=" \n ")], D(2026, 10, 13, 10))[0]["text"]
        self.assertTrue(t.startswith("Hello,"))

    def test_email_not_truncated(self):
        name = "N" * 120
        out = plan_reminders([A(customer_name=name, phone=None)], D(2026, 10, 13, 10))
        self.assertEqual(out[0]["channel"], "email")
        self.assertIn(name, out[0]["text"])
        self.assertGreater(len(out[0]["text"]), SMS_MAX_LEN)

    def test_signatures(self):
        now = D(2026, 10, 13, 10)
        for c, sig in ((" pl", SIG_PL), ("IE", SIG_DEFAULT), ("GB", SIG_DEFAULT),
                       (None, SIG_DEFAULT), ("MISSING", SIG_DEFAULT)):
            ap = A(country=c)
            if c == "MISSING":
                del ap["country"]
            self.assertTrue(plan_reminders([ap], now)[0]["text"].endswith(sig), c)

    def test_sorting_mixed_batch(self):
        now = D(2026, 10, 13, 10)
        aps = [A(id="late", starts_at=D(2026, 10, 30, 14)),
               A(id="soon", starts_at=D(2026, 10, 14, 14)),
               A(id="mid", starts_at=D(2026, 10, 20, 14))]
        out = plan_reminders(aps, now)
        times = [o["send_at"] for o in out]
        self.assertEqual(times, sorted(times))
        self.assertEqual(out[0]["appointment_id"], "soon")
        ids = [o["appointment_id"] for o in out]
        self.assertLess(ids.index("mid"), len(ids) - ids[::-1].index("mid"))

    def test_same_instant_dedupe(self):
        out = plan_reminders([A(starts_at=D(2026, 10, 13, 12))], D(2026, 10, 13, 11))
        self.assertEqual(len(out), 1)

    def test_not_mutated(self):
        aps = [A(), A(id="b", status="cancelled")]
        before = copy.deepcopy(aps)
        plan_reminders(aps, D(2026, 10, 13, 10))
        self.assertEqual(aps, before)

    def test_invalid_now(self):
        for bad in (datetime(2026, 10, 13, 10), None):
            with self.assertRaises(ValueError) as cm:
                plan_reminders([A()], bad)
            self.assertNotIn("known.person", str(cm.exception))

    def test_malformed_skipped_batch_continues(self):
        aps = [A(id="bad1", starts_at=datetime(2026, 10, 18, 14)),
               {"customer_name": "Zed", "email": "known.person@example.com"},
               A(id="bad3", starts_at=None), A(id="ok")]
        with self.assertLogs(level="DEBUG") as cm:
            out = plan_reminders(aps, D(2026, 10, 13, 10))
        self.assertEqual({o["appointment_id"] for o in out}, {"ok"})
        warns = [r.getMessage() for r in cm.records if r.levelno == logging.WARNING]
        self.assertEqual(len(warns), 3)
        self.assertTrue(any("bad1" in w and "starts_at" in w for w in warns))
        self.assertTrue(any("bad3" in w and "starts_at" in w for w in warns))

    def test_no_email_in_logs_or_exceptions(self):
        email = "secret.person@example.com"
        aps = [A(email=email, phone=None), A(id="x", email=email, starts_at=None),
               A(id="y", email=email, customer_name="Zed")]
        with self.assertLogs(level="DEBUG") as cm:
            out = plan_reminders(aps, D(2026, 10, 13, 10))
            with self.assertRaises(ValueError) as exc:
                plan_reminders(aps, datetime(2026, 1, 1))
        self.assertNotIn(email, str(exc.exception))
        for r in cm.records:
            self.assertNotIn(email, r.getMessage())
            self.assertNotIn(email, str(r.args))
        infos = [r for r in cm.records if r.levelno == logging.INFO and "Planned reminder" in r.getMessage()]
        self.assertEqual(len(infos), len(out))


if __name__ == "__main__":
    unittest.main()