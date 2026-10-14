# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-8w64g6ue/reminders.py =====
# NOTE: I had no execution tools in this session, so the tests below have NOT been run.
# Run them with: python -m unittest test_reminders -v
#
# Assumptions and deviations:
# - Polish customers' times are shown in Dublin time (COUNTRY_TZ maps everything to Dublin).
# - The signatures contain non-GSM characters (a-acute, n-acute, i-acute), so the gateway may send
#   SMS as Unicode (UCS-2) segments, which can split messages at 70 characters per segment.
#   The 160-character cap here counts characters, as specified.
# - House rule vs privacy rule: the INFO line records appointment id, kind, channel and a contact
#   reference ("phone-on-file" or "email-on-file"), never the raw email, phone or name (DPC audit).
# - Day of month is unpadded ("5 Oct 2026").
# - Last-initial form is "Ana M.".

import logging
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

LEAD_FIRST = timedelta(hours=48)
LEAD_SECOND = timedelta(hours=2)
SMS_MAX_LEN = 160
QUIET_START_HOUR = 21  # inclusive
QUIET_END_HOUR = 8     # exclusive
SEND_EVENING_HOUR = 20

DUBLIN = ZoneInfo("Europe/Dublin")
DEFAULT_TZ = DUBLIN
COUNTRY_TZ = {"IE": DUBLIN, "PL": DUBLIN}  # one-line change per country

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIGNATURE_PL = "Grzegorz Szczepański"
SIGNATURE_DEFAULT = "Siobhán Ní Dhuibhir"


class _Malformed(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _nonblank(v):
    return isinstance(v, str) and v.strip() != ""


def _country(appt):
    c = appt.get("country")
    return c.strip().upper() if isinstance(c, str) else ""


def _quiet(dt, tz):
    h = dt.astimezone(tz).hour
    return h >= QUIET_START_HOUR or h < QUIET_END_HOUR


def _prev_evening(dt, tz):
    loc = dt.astimezone(tz)
    d = loc.date() if loc.hour >= QUIET_START_HOUR else loc.date() - timedelta(days=1)
    return datetime.combine(d, time(SEND_EVENING_HOUR), tzinfo=tz)


def _next_morning(dt, tz):
    loc = dt.astimezone(tz)
    d = loc.date() + timedelta(days=1) if loc.hour >= QUIET_START_HOUR else loc.date()
    return datetime.combine(d, time(QUIET_END_HOUR), tzinfo=tz)


def _resolve(nominal, now, starts_at, tz):
    t = nominal
    if _quiet(t, tz):
        t = _prev_evening(t, tz)
    if t < now:
        t = now
        if _quiet(t, tz):
            t = _next_morning(t, tz)
    if t >= starts_at:
        return None
    return t


def _name_candidates(name):
    parts = name.split() if isinstance(name, str) else []
    if not parts:
        return [""]
    first = parts[0]
    cands = [" ".join(parts)]
    if len(parts) > 1:
        cands.append(f"{first} {parts[-1][0]}.")
    cands += [first, first[0], ""]
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _build_text(name, local_start, signature, limit):
    date = f"{local_start.day} {MONTHS[local_start.month - 1]} {local_start.year}"
    hhmm = f"{local_start.hour:02d}:{local_start.minute:02d}"
    text = ""
    for cand in _name_candidates(name):
        greeting = f"Hi {cand}," if cand else "Hi,"
        text = unicodedata.normalize(
            "NFC",
            f"{greeting} reminder: your Brennan Opticians appointment is on {date} at {hhmm}. {signature}")
        if limit is None or len(text) <= limit:
            return text
    return text  # no-name form; date, time and signature are never cut


def _plan_one(appt, now):
    if not isinstance(appt, dict):
        raise _Malformed("not_a_dict")
    starts_at = appt.get("starts_at")
    if starts_at is None:
        raise _Malformed("missing_starts_at")
    if not _is_aware(starts_at):
        raise _Malformed("invalid_or_naive_starts_at")
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() in ("cancelled", "canceled"):
        return []
    if starts_at <= now:
        return []

    if _nonblank(appt.get("phone")) and appt.get("optout_sms_v2") is False:
        channel, contact = "sms", "phone-on-file"
    elif _nonblank(appt.get("email")):
        channel, contact = "email", "email-on-file"
    else:
        return []

    country = _country(appt)
    tz = COUNTRY_TZ.get(country, DEFAULT_TZ)
    signature = SIGNATURE_PL if country == "PL" else SIGNATURE_DEFAULT
    text = _build_text(appt.get("customer_name"), starts_at.astimezone(tz), signature,
                       SMS_MAX_LEN if channel == "sms" else None)

    first = _resolve(starts_at - LEAD_FIRST, now, starts_at, tz)
    second = _resolve(starts_at - LEAD_SECOND, now, starts_at, tz)
    if first is not None and second is not None and first == second:
        first = None  # collapse: keep the 2h reminder

    out = []
    for kind, when in (("48h", first), ("2h", second)):
        if when is None:
            continue
        out.append({"appointment_id": appt.get("id"), "channel": channel,
                    "send_at": when, "text": text})
        logger.info("reminder planned appointment=%s kind=%s channel=%s contact=%s send_at=%s",
                    appt.get("id"), kind, channel, contact, when.isoformat())
    return out


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    result = []
    for appt in appointments:
        try:
            result.extend(_plan_one(appt, now))
        except _Malformed as e:
            aid = appt.get("id") if isinstance(appt, dict) else None
            logger.warning("appointment skipped id=%s reason=%s", aid, e.reason)
        except Exception as e:  # never include message/traceback: may contain PII
            aid = appt.get("id") if isinstance(appt, dict) else None
            logger.warning("appointment skipped id=%s reason=unexpected_%s", aid, type(e).__name__)
    result.sort(key=lambda r: r["send_at"])  # stable: ties keep input order, 48h before 2h
    return result


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-8w64g6ue/test_reminders.py =====
import copy
import logging
import unittest
from datetime import datetime

from reminders import plan_reminders, DUBLIN

SIG = "Siobhán Ní Dhuibhir"
SECRET_EMAIL = "secret.person@example.com"


def d(day, h=0, m=0, month=10):
    return datetime(2026, month, day, h, m, tzinfo=DUBLIN)


def appt(starts_at, **kw):
    a = {"id": "A1", "customer_name": "Ana Murphy", "email": None, "phone": "+353851234567",
         "country": "IE", "status": "booked", "starts_at": starts_at, "optout_sms_v2": False}
    a.update(kw)
    return a


def sends(res):
    return [r["send_at"] for r in res]


class Tests(unittest.TestCase):
    def test_ex1(self):
        r = plan_reminders([appt(d(20, 14))], d(13, 9))
        self.assertEqual(sends(r), [d(18, 14), d(20, 12)])
        self.assertEqual(set(r[0]), {"appointment_id", "channel", "send_at", "text"})

    def test_ex2(self):
        r = plan_reminders([appt(d(14, 15))], d(13, 10))
        self.assertEqual(sends(r), [d(13, 10), d(14, 13)])

    def test_ex3(self):
        r = plan_reminders([appt(d(20, 9, 30))], d(13, 9))
        self.assertEqual(sends(r), [d(18, 9, 30), d(19, 20)])

    def test_ex4(self):
        r = plan_reminders([appt(d(15, 6))], d(13, 20, 30))
        self.assertEqual(sends(r), [d(13, 20, 30), d(14, 20)])

    def test_ex5(self):
        r = plan_reminders([appt(d(14, 12))], d(13, 23, 30))
        self.assertEqual(sends(r), [d(14, 8), d(14, 10)])

    def test_ex6(self):
        r = plan_reminders([appt(d(14, 8, 30))], d(13, 23, 30))
        self.assertEqual(sends(r), [d(14, 8)])
        self.assertEqual(plan_reminders([appt(d(14, 7, 30))], d(13, 23, 30)), [])

    def test_ex7(self):
        now = d(13, 9)
        self.assertEqual(plan_reminders([appt(d(20, 14), status="Cancelled")], now), [])
        self.assertEqual(plan_reminders([appt(d(20, 14), status=" CANCELED ")], now), [])
        self.assertEqual(plan_reminders([appt(d(13, 8))], now), [])
        self.assertEqual(plan_reminders([appt(d(20, 14), phone="", optout_sms_v2=True, email=" ")], now), [])

    def test_ex8(self):
        name = "Bartholomew " + "X" * 288
        r = plan_reminders([appt(d(20, 14), customer_name=name)], d(13, 9))
        for x in r:
            self.assertLessEqual(len(x["text"]), 160)
            self.assertIn("14 Oct 2026 at 14:00", x["text"])
            self.assertTrue(x["text"].endswith(SIG))
        name2 = "X" * 300
        t = plan_reminders([appt(d(20, 14), customer_name=name2)], d(13, 9))[0]["text"]
        self.assertEqual(t, f"Hi X, reminder: your Brennan Opticians appointment is on 20 Oct 2026 at 14:00. {SIG}")

    def test_name_ladder_and_blank(self):
        t = plan_reminders([appt(d(20, 14), customer_name="Ana Murphy")], d(13, 9))[0]["text"]
        self.assertTrue(t.startswith("Hi Ana Murphy, reminder:"))
        t = plan_reminders([appt(d(20, 14), customer_name=None)], d(13, 9))[0]["text"]
        self.assertTrue(t.startswith("Hi, reminder:"))
        t = plan_reminders([appt(d(20, 14), customer_name="Ana " + "M" * 200)], d(13, 9))[0]["text"]
        self.assertTrue(t.startswith("Hi Ana M., reminder:"))

    def test_email_no_limit(self):
        name = "N" * 300
        r = plan_reminders([appt(d(20, 14), customer_name=name, optout_sms_v2=True, email="a@b.ie")], d(13, 9))
        self.assertEqual(r[0]["channel"], "email")
        self.assertIn(name, r[0]["text"])

    def test_ex9(self):
        r = plan_reminders([appt(d(20, 14), country=" pl ")], d(13, 9))
        self.assertTrue(r[0]["text"].endswith("Grzegorz Szczepański"))
        r = plan_reminders([appt(d(20, 14), country=None)], d(13, 9))
        self.assertTrue(r[0]["text"].endswith(SIG))

    def test_ex10(self):
        r = plan_reminders([appt(d(26, 9))], d(20, 9))
        self.assertEqual(r[0]["send_at"], d(24, 10))

    def test_optout_v2_only(self):
        now, s = d(13, 9), d(20, 14)
        a = appt(s, opt_out=True, optout_sms_v2=False)
        self.assertEqual(plan_reminders([a], now)[0]["channel"], "sms")
        b = appt(s, opt_out=False, optout_sms_v2=True, email="a@b.ie")
        self.assertEqual(plan_reminders([b], now)[0]["channel"], "email")
        c = appt(s, email="a@b.ie")
        del c["optout_sms_v2"]
        self.assertEqual(plan_reminders([c], now)[0]["channel"], "email")
        e = appt(s, optout_sms_v2="false", email="a@b.ie")
        self.assertEqual(plan_reminders([e], now)[0]["channel"], "email")
        f = appt(s, optout_sms_v2=0)
        self.assertEqual(plan_reminders([f], now), [])

    def test_sort_and_no_mutation(self):
        a = appt(d(20, 14), id="A")
        b = appt(d(19, 14), id="B")
        orig = copy.deepcopy([a, b])
        r = plan_reminders([a, b], d(13, 9))
        self.assertEqual([a, b], orig)
        self.assertEqual(sends(r), sorted(sends(r)))
        self.assertTrue(all(x >= d(13, 9) for x in sends(r)))

    def test_malformed_skipped(self):
        bad1 = appt(datetime(2026, 10, 20, 14), id="BAD1", email=SECRET_EMAIL)
        bad2 = appt(None, id="BAD2", email=SECRET_EMAIL)
        del bad2["starts_at"]
        good = appt(d(20, 14), id="GOOD")
        r = plan_reminders([bad1, bad2, good], d(13, 9))
        self.assertEqual({x["appointment_id"] for x in r}, {"GOOD"})

    def test_no_email_in_logs(self):
        records = []

        class H(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage() + repr(record.args) + str(record.exc_info)
                               + str(record.exc_text))

        root = logging.getLogger()
        h, old = H(), root.level
        root.addHandler(h)
        root.setLevel(logging.DEBUG)
        try:
            items = [
                appt(d(20, 14), id="OK1", email=SECRET_EMAIL, optout_sms_v2=True),
                appt(datetime(2026, 10, 20, 14), id="BAD1", email=SECRET_EMAIL),
                appt("not a date", id="BAD2", email=SECRET_EMAIL),
                "garbage",
            ]
            plan_reminders(items, d(13, 9))
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        self.assertTrue(records)
        blob = "\n".join(records)
        self.assertNotIn(SECRET_EMAIL, blob)
        self.assertNotIn("secret.person", blob)
        self.assertNotIn("+353851234567", blob)
        self.assertNotIn("Ana", blob)

    def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 9))


if __name__ == "__main__":
    unittest.main()