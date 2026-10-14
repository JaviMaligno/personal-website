"""Brennan Opticians appointment reminders (Python 3.12, standard library only).

Dependency: tzdata (the server runs UTC and may lack a system tz database).
Run tests with: python -m unittest <this_module_name>

REPORT
Built: plan_reminders(appointments, now), pure and stateless, plus unittest
tests (acceptance examples 1-15 and the template-fit check) in this module.

Assumptions:
- Reminder kinds are "48h" and "2h"; the 2h reminder wins on a send_at collision.
- Non-string status is treated as "not cancelled"; blank or non-string name
  uses the generic greeting.
- Polish appointments use Europe/Dublin for date, time and quiet hours.
- Log rule conflict: the house rule asks for the contact in each INFO line, but
  the client requirement says email, phone and name must never be logged. The
  stricter client rule wins, so each INFO line carries appointment id, channel
  and kind only. Support can look up the contact by appointment id.

Open items for the client:
1. Forward-to-08:00 fallback replaces "move back" when moving back would
   put the send in the past.
2. Should Polish appointments use Europe/Warsaw rather than Dublin (assumed Dublin)?
3. Signature characters (a with acute, i with acute, n with acute) may make carriers send SMS as
   UCS-2 (70-char segments) even though we enforce 160.
4. Email output has no subject.
5. The module is stateless, so repeated runs re-emit an overdue first reminder.
"""
import copy
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
log = logging.getLogger("brennan.reminders")

SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
TEMPLATE = ("{greeting}, this is a reminder of your appointment at "
            "Brennan Opticians on {date} at {time}. {signature}")
SMS_LIMIT = 160
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED = ("id", "customer_name", "email", "phone", "country", "status",
            "starts_at", "optout_sms_v2")


class _Malformed(Exception):
    """Carries only a reason code, never record content."""


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _local(dt):
    return dt.astimezone(DUBLIN)


def _quiet(dt):
    h = _local(dt).hour
    return h >= 21 or h < 8


def _at(day, hour):
    return datetime.combine(day, time(hour), tzinfo=DUBLIN).astimezone(UTC)


def _prev_2000(dt):
    l = _local(dt)
    return _at(l.date() if l.hour >= 21 else l.date() - timedelta(days=1), 20)


def _next_0800(dt):
    """Step 4 of the quiet-hours resolution: next 08:00 Dublin local."""
    l = _local(dt)
    return _at(l.date() if l.hour < 8 else l.date() + timedelta(days=1), 8)


def _resolve(target, now, start):
    if not _quiet(target):
        chosen = target
    else:
        prev = _prev_2000(target)
        if prev >= now:
            chosen = prev
        elif not _quiet(now):
            chosen = now
        else:
            chosen = _next_0800(now)
    return chosen if chosen < start else None


def _clean_name(name):
    import unicodedata
    if not isinstance(name, str):
        return ""
    return unicodedata.normalize("NFC", " ".join(name.split()))


def _text(name, start_local, country, sms):
    sig = SIGNATURE_PL if isinstance(country, str) and country.strip().upper() == "PL" \
        else SIGNATURE_DEFAULT
    date = f"{start_local.day} {MONTHS[start_local.month - 1]} {start_local.year}"
    hhmm = f"{start_local.hour:02d}:{start_local.minute:02d}"
    name = _clean_name(name)
    ladder = [name]
    if name:
        ladder += [name.split(" ")[0], name[0] + "."]
    ladder.append("")
    text = ""
    for n in dict.fromkeys(ladder):
        greeting = f"Hello {n}" if n else "Hello"
        text = TEMPLATE.format(greeting=greeting, date=date, time=hhmm, signature=sig)
        if not sms or len(text) <= SMS_LIMIT:
            break
        if not n:
            break
    return text


def _channel(a):
    phone, email = a["phone"], a["email"]
    if isinstance(phone, str) and phone.strip() and a["optout_sms_v2"] is False:
        return "sms"
    if isinstance(email, str) and email.strip():
        return "email"
    return None


def _plan_one(a, now):
    if not isinstance(a, dict) or any(k not in a for k in REQUIRED):
        raise _Malformed("missing_key")
    if not _aware(a["starts_at"]):
        raise _Malformed("naive_starts_at")
    status = a["status"]
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        return []
    start = a["starts_at"].astimezone(UTC)
    if start <= now:
        return []
    channel = _channel(a)
    if channel is None:
        return []
    planned = []
    for kind, nominal in (("48h", start - timedelta(hours=48)),
                          ("2h", start - timedelta(hours=2))):
        if nominal < now:
            if kind == "2h":
                continue
            nominal = now
        when = _resolve(nominal, now, start)
        if when is not None:
            planned.append((kind, when))
    if len(planned) == 2 and planned[0][1] == planned[1][1]:
        planned = planned[1:]
    text = _text(a["customer_name"], _local(start), a["country"], channel == "sms")
    out = []
    for kind, when in planned:
        out.append({"appointment_id": a["id"], "channel": channel,
                    "send_at": _local(when), "text": text})
        log.info("reminder planned appointment_id=%s channel=%s kind=%s",
                 a["id"], channel, kind)
    return out


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    result = []
    for a in appointments:
        try:
            result.extend(_plan_one(a, now_utc))
        except _Malformed as e:
            aid = a.get("id", "?") if isinstance(a, dict) else "?"
            log.warning("appointment skipped appointment_id=%s reason=%s", aid, e)
        except Exception:
            aid = a.get("id", "?") if isinstance(a, dict) else "?"
            log.warning("appointment skipped appointment_id=%s reason=error", aid)
    result.sort(key=lambda r: r["send_at"])
    return result


# ----------------------------- tests -----------------------------

NOW = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
EMAIL = "secret.person@distinct-example.invalid"


def D(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def appt(**kw):
    base = dict(id="A1", customer_name="Mary Murphy", email=EMAIL,
                phone="+353851234567", country="IE", status="booked",
                starts_at=D(2026, 10, 14, 15), optout_sms_v2=False)
    base.update(kw)
    return base


class PlanTests(unittest.TestCase):
    def test_1_two_sms(self):
        r = plan_reminders([appt()], NOW)
        self.assertEqual([x["channel"] for x in r], ["sms", "sms"])
        self.assertEqual(r[0]["send_at"], NOW)
        self.assertEqual(r[1]["send_at"], D(2026, 10, 14, 12))
        for x in r:
            self.assertIn("14 Oct 2026", x["text"])
            self.assertIn("15:00", x["text"])
            self.assertTrue(x["text"].endswith(SIGNATURE_DEFAULT))

    def test_2_email_fallbacks(self):
        for kw in ({"optout_sms_v2": True}, {"phone": "  "}, {"optout_sms_v2": None}):
            r = plan_reminders([appt(**kw)], NOW)
            self.assertEqual({x["channel"] for x in r}, {"email"})
        a = appt()
        del a["optout_sms_v2"]
        self.assertEqual(plan_reminders([a], NOW), [])  # malformed: key missing

    def test_2b_nothing_possible(self):
        self.assertEqual(plan_reminders([appt(optout_sms_v2=True, email="")], NOW), [])

    def test_3_legacy_field_ignored(self):
        r = plan_reminders([appt(opt_out=True, optout_sms_v2=False)], NOW)
        self.assertEqual(r[0]["channel"], "sms")
        r = plan_reminders([appt(opt_out=False, optout_sms_v2=True)], NOW)
        self.assertEqual(r[0]["channel"], "email")

    def test_4_cancelled_or_started(self):
        self.assertEqual(plan_reminders([appt(status=" Cancelled ")], NOW), [])
        self.assertEqual(plan_reminders([appt(starts_at=NOW)], NOW), [])
        self.assertEqual(plan_reminders([appt(starts_at=NOW - timedelta(hours=1))], NOW), [])

    def test_5_now_in_quiet_hours(self):
        now = datetime(2026, 10, 13, 21, 30, tzinfo=UTC)
        r = plan_reminders([appt(starts_at=D(2026, 10, 14, 14))], now)
        self.assertEqual([x["send_at"] for x in r], [D(2026, 10, 14, 8), D(2026, 10, 14, 12)])

    def test_6_quiet_target_now_ok(self):
        now = datetime(2026, 10, 13, 19, 30, tzinfo=UTC)
        r = plan_reminders([appt(starts_at=D(2026, 10, 15, 22))], now)
        self.assertEqual(r[0]["send_at"], now)

    def test_7_move_back(self):
        r = plan_reminders([appt(starts_at=D(2026, 10, 20, 8, 30))], NOW)
        self.assertEqual([x["send_at"] for x in r], [D(2026, 10, 17, 20), D(2026, 10, 19, 20)])

    def test_8_elapsed_arithmetic(self):
        r = plan_reminders([appt(starts_at=datetime(2026, 10, 26, 9, 0, tzinfo=UTC))], NOW)
        self.assertEqual(r[0]["send_at"], D(2026, 10, 24, 10))

    def test_9_only_first(self):
        now = D(2026, 10, 13, 12, 30)
        r = plan_reminders([appt(starts_at=D(2026, 10, 13, 13))], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], now)

    def test_10_drops_and_collisions(self):
        now = D(2026, 10, 13, 22, 30)
        self.assertEqual(plan_reminders([appt(starts_at=D(2026, 10, 14, 8))], now), [])
        r = plan_reminders([appt(starts_at=D(2026, 10, 14, 10))], now)
        self.assertEqual([x["send_at"] for x in r], [D(2026, 10, 14, 8)])

    def test_11_long_name(self):
        n = "Maximilian " + "X" * 200
        r = plan_reminders([appt(customer_name=n)], NOW)
        for x in r:
            self.assertLessEqual(len(x["text"]), 160)
            self.assertIn("14 Oct 2026", x["text"])
            self.assertIn("15:00", x["text"])
            self.assertTrue(x["text"].endswith(SIGNATURE_DEFAULT))
        self.assertTrue(r[0]["text"].startswith("Hello Maximilian,"))
        r = plan_reminders([appt(customer_name="Y" * 300 + " Z")], NOW)
        self.assertTrue(r[0]["text"].startswith("Hello Y.,"))
        r = plan_reminders([appt(customer_name="")], NOW)
        self.assertTrue(r[0]["text"].startswith("Hello,"))
        r = plan_reminders([appt(customer_name=n, optout_sms_v2=True)], NOW)
        self.assertIn(n, r[0]["text"])

    def test_12_signatures(self):
        for c in ("PL", " pl "):
            self.assertTrue(plan_reminders([appt(country=c)], NOW)[0]["text"]
                            .endswith(SIGNATURE_PL))
        self.assertTrue(plan_reminders([appt(country="IE")], NOW)[0]["text"]
                        .endswith(SIGNATURE_DEFAULT))

    def test_13_order_and_keys(self):
        r = plan_reminders([appt(id="late", starts_at=D(2026, 10, 20, 15)),
                            appt(id="soon")], NOW)
        sends = [x["send_at"] for x in r]
        self.assertEqual(sends, sorted(sends))
        for x in r:
            self.assertGreaterEqual(x["send_at"], NOW)
            self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(x["send_at"].tzinfo, DUBLIN)
        self.assertEqual(plan_reminders([], NOW), [])

    def test_14_no_email_in_logs(self):
        records = []

        class H(logging.Handler):
            def emit(self, record):
                records.append(record)

        root = logging.getLogger()
        old = root.level
        h = H(0)
        root.addHandler(h)
        root.setLevel(1)
        log.setLevel(1)
        try:
            bad = appt(id="BAD", starts_at=datetime(2026, 10, 20, 9))
            gone = appt(id="C", status="cancelled")
            ok = appt(id="OK", optout_sms_v2=True)
            out = plan_reminders([bad, gone, ok], NOW)
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        self.assertTrue(records)
        for rec in records:
            blob = rec.getMessage() + repr(rec.__dict__)
            self.assertNotIn(EMAIL, blob)
            self.assertNotIn("Mary", blob)
            self.assertNotIn("+353", blob)
        self.assertNotIn(EMAIL, repr(out))

    def test_15_purity(self):
        data = [appt(), appt(id="B", optout_sms_v2=True)]
        before = copy.deepcopy(data)
        plan_reminders(data, NOW)
        self.assertEqual(data, before)
        with self.assertRaises(ValueError):
            plan_reminders(data, datetime(2026, 10, 13, 10, 0))

    def test_malformed_skipped_not_fatal(self):
        bad = appt(id="B1")
        del bad["email"]
        r = plan_reminders([bad, "junk", appt(id="G")], NOW)
        self.assertEqual({x["appointment_id"] for x in r}, {"G"})

    def test_template_fits(self):
        longest = max((SIGNATURE_DEFAULT, SIGNATURE_PL), key=len)
        fixed = TEMPLATE.format(greeting="Hello", date="30 Sep 2026",
                                time="23:59", signature=longest)
        self.assertLessEqual(len(fixed), 160)


if __name__ == "__main__":
    unittest.main()