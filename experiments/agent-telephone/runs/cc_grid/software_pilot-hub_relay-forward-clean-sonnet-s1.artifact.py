"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now). Pure function, standard library only.
Run the tests with: python this_module.py

Assumptions and points for the client to confirm:
- A 2h reminder whose point has passed is sent at `now` (subject to quiet hours).
- "Immediately" inside quiet hours (21:00-08:00 Dublin) is deferred to the next 08:00.
- Appointments starting around 08:00 may get no reminder (nothing may go out before 08:00).
- Output has no recipient field; the caller resolves contact details from appointment_id.
- Running twice produces duplicates; deduplication is the caller's job.
- Accented characters (e.g. in the signature) may make an SMS go as Unicode (70-char segments).
- PL customers still see Dublin local times.
- House rule asks to log "who and how (channel and contact)", but the DPC audit forbids
  logging email addresses; so INFO lines carry appointment_id and channel only, never contact data.
"""
import copy
import logging
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX = 160


def _nonblank(v):
    return isinstance(v, str) and bool(v.strip())


def _quiet(dt):
    h = dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _at_local(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN).astimezone(UTC)


def _shift_back(t):
    d = t.astimezone(DUBLIN).date()
    if t.astimezone(DUBLIN).hour < 8:
        d -= timedelta(days=1)
    return _at_local(d, 20)


def _next_open(now):
    loc = now.astimezone(DUBLIN)
    d = loc.date() if loc.hour < 8 else loc.date() + timedelta(days=1)
    return _at_local(d, 8)


def _send_time(t, now):
    if t < now:
        t = now
    if _quiet(t):
        s = _shift_back(t)
        if s < now:
            s = _next_open(now) if _quiet(now) else now
        t = s
    return t


def _name_options(name):
    parts = name.split()
    if not parts:
        yield ""
        return
    yield " ".join(parts)
    if len(parts) > 1:
        yield f"{parts[0]} {parts[-1][0]}."
    yield parts[0]
    for k in range(len(parts[0]) - 1, 0, -1):
        yield parts[0][:k] + "."
    yield ""


def _build(name, date_s, time_s, sig, sms):
    def make(n):
        greet = f"Hi {n}," if n else "Hi,"
        return unicodedata.normalize(
            "NFC",
            f"{greet} reminder: your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}",
        )

    if not sms:
        return make(" ".join(name.split()))
    text = ""
    for opt in _name_options(name):
        text = make(opt)
        if len(text) <= SMS_MAX:
            break
    return text


def _plan_one(a, now):
    aid = a.get("id")
    status = a.get("status")
    if isinstance(status, str) and status.strip().lower() in ("cancelled", "canceled"):
        logger.debug("skip id=%s reason=cancelled", aid)
        return []
    starts = a["starts_at"]
    if not isinstance(starts, datetime) or starts.tzinfo is None:
        raise ValueError("starts_at must be an aware datetime")
    starts = starts.astimezone(UTC)
    if starts <= now:
        logger.debug("skip id=%s reason=started", aid)
        return []

    phone_ok = _nonblank(a.get("phone"))
    optout = a.get("optout_sms_v2")
    if phone_ok and optout is False:
        channel = "sms"
    else:
        if phone_ok and not isinstance(optout, bool):
            logger.warning("id=%s reason=optout_sms_v2_invalid_treated_as_opted_out", aid)
        if not _nonblank(a.get("email")):
            logger.warning("skip id=%s reason=no_contact", aid)
            return []
        channel = "email"

    country = a.get("country")
    pl = isinstance(country, str) and country.strip().upper() == "PL"
    sig = "Grzegorz Szczepański" if pl else "Siobhán Ní Dhuibhir"
    loc = starts.astimezone(DUBLIN)
    name = a.get("customer_name")
    text = _build(name if isinstance(name, str) else "",
                  loc.strftime("%d/%m/%Y"), loc.strftime("%H:%M"), sig, channel == "sms")

    t48 = _send_time(starts - timedelta(hours=48), now)
    t2 = _send_time(starts - timedelta(hours=2), now)
    out = []
    if t48 < starts and not (t2 < starts and t48 >= t2):
        out.append(t48)
    if t2 < starts:
        out.append(t2)
    return [{"appointment_id": aid, "channel": channel,
             "send_at": s.astimezone(DUBLIN), "text": text} for s in out]


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    result = []
    for a in appointments:
        try:
            result.extend(_plan_one(a, now))
        except Exception:
            try:
                aid = a.get("id")
            except Exception:
                aid = None
            logger.warning("skip id=%s reason=bad_record", aid)
    result.sort(key=lambda r: r["send_at"])
    for r in result:
        logger.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                    r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return result


# ----------------------------------------------------------------- tests

def L(*args):
    return datetime(*args, tzinfo=DUBLIN)


NOW = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)


def appt(**kw):
    d = {"id": "A1", "customer_name": "Mary O'Brien", "email": "mary@example.com",
         "phone": "+353851234567", "country": "IE", "status": "booked",
         "starts_at": L(2026, 10, 20, 14, 0), "optout_sms_v2": False}
    d.update(kw)
    return d


class PlanTests(unittest.TestCase):
    def test_basic(self):
        r = plan_reminders([appt()], NOW)
        self.assertEqual([x["send_at"] for x in r], [L(2026, 10, 18, 14, 0), L(2026, 10, 20, 12, 0)])
        self.assertEqual(set(r[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertEqual(r[0]["channel"], "sms")
        self.assertEqual(r[0]["text"], "Hi Mary O'Brien, reminder: your Brennan Opticians "
                         "appointment is on 20/10/2026 at 14:00. Siobhán Ní Dhuibhir")
        self.assertEqual(r[0]["send_at"].tzinfo, DUBLIN)

    def test_48h_passed(self):
        now = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)
        r = plan_reminders([appt()], now)
        self.assertEqual([x["send_at"] for x in r], [now, L(2026, 10, 20, 12, 0)])

    def test_back_shift(self):
        r = plan_reminders([appt(starts_at=L(2026, 10, 20, 8, 30))], NOW)
        self.assertEqual(r[1]["send_at"], L(2026, 10, 19, 20, 0))

    def test_back_shift_in_past(self):
        now = L(2026, 10, 19, 20, 30)
        r = plan_reminders([appt(starts_at=L(2026, 10, 20, 8, 30))], now)
        self.assertEqual([x["send_at"] for x in r], [now])

    def test_quiet_now(self):
        now = L(2026, 10, 19, 22, 0)
        r = plan_reminders([appt(starts_at=L(2026, 10, 20, 9, 0))], now)
        self.assertEqual([x["send_at"] for x in r], [L(2026, 10, 20, 8, 0)])

    def test_drop(self):
        self.assertEqual(plan_reminders([appt(starts_at=L(2026, 10, 20, 8, 0))],
                                        L(2026, 10, 20, 7, 0)), [])

    def test_boundaries(self):
        self.assertEqual(plan_reminders([appt(starts_at=NOW)], NOW), [])
        r = plan_reminders([appt(starts_at=NOW + timedelta(minutes=1))], NOW)
        self.assertEqual([x["send_at"] for x in r], [NOW])
        r = plan_reminders([appt(starts_at=L(2026, 10, 20, 23, 0))], NOW)
        self.assertEqual(r[1]["send_at"], L(2026, 10, 20, 20, 0))
        r = plan_reminders([appt(starts_at=L(2026, 10, 20, 10, 0))], NOW)
        self.assertEqual(r[1]["send_at"], L(2026, 10, 20, 8, 0))

    def test_utc_trap(self):
        s = datetime(2026, 7, 1, 23, 30, tzinfo=UTC)
        r = plan_reminders([appt(starts_at=s)], datetime(2026, 6, 1, tzinfo=UTC))
        self.assertIn("02/07/2026 at 00:30", r[0]["text"])

    def test_dst(self):
        s = L(2026, 10, 26, 14, 0)
        r = plan_reminders([appt(starts_at=s)], NOW)
        self.assertEqual(r[0]["send_at"], s.astimezone(UTC) - timedelta(hours=48))
        self.assertEqual(r[0]["send_at"].hour, 15)

    def test_channels(self):
        def ch(**kw):
            r = plan_reminders([appt(**kw)], NOW)
            return {x["channel"] for x in r}
        self.assertEqual(ch(), {"sms"})
        self.assertEqual(ch(optout_sms_v2=True), {"email"})
        self.assertEqual(ch(optout_sms_v2=None), {"email"})
        self.assertEqual(ch(optout_sms_v2="false"), {"email"})
        self.assertEqual(ch(opt_out=True), {"sms"})
        self.assertEqual(ch(phone="  "), {"email"})
        self.assertEqual(ch(phone=None), {"email"})
        d = appt()
        del d["optout_sms_v2"]
        self.assertEqual({x["channel"] for x in plan_reminders([d], NOW)}, {"email"})
        self.assertEqual(ch(phone=None, email=" "), set())
        self.assertEqual(ch(optout_sms_v2=True, email=None), set())

    def test_signature(self):
        t = plan_reminders([appt(country=" pl ")], NOW)[0]["text"]
        self.assertTrue(t.endswith("Grzegorz Szczepański"))
        t = plan_reminders([appt(country=None)], NOW)[0]["text"]
        self.assertTrue(t.endswith("Siobhán Ní Dhuibhir"))

    def test_length(self):
        name = "Bartholomew " + "X" * 150 + " Fitzgerald-Montgomery"
        for r in plan_reminders([appt(customer_name=name)], NOW):
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("20/10/2026 at 14:00", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))
        e = plan_reminders([appt(customer_name=name, optout_sms_v2=True)], NOW)[0]["text"]
        self.assertIn(name, e)
        self.assertIn("Hi Mary O'Brien,",
                      plan_reminders([appt()], NOW)[0]["text"])
        mid = plan_reminders([appt(customer_name="Bartholomew " + "Y" * 120)], NOW)[0]["text"]
        self.assertTrue(mid.startswith("Hi Bartholomew Y."))

    def test_logging(self):
        with self.assertLogs(level="DEBUG") as cm:
            r = plan_reminders([appt(), appt(id="A2", optout_sms_v2=True),
                                appt(id="A3", status="cancelled"), {"id": "A4"}], NOW)
        out = "\n".join(cm.output)
        self.assertNotIn("mary@example.com", out)
        self.assertNotIn("Mary", out)
        self.assertNotIn("+353", out)
        self.assertEqual(sum(1 for rec in cm.records if rec.levelno == logging.INFO), len(r))
        self.assertIn("A4", out)
        for x in r:
            self.assertNotIn("mary@example.com", x["text"])

    def test_cancelled_past(self):
        for s in (" Cancelled ", "CANCELED", "cancelled"):
            self.assertEqual(plan_reminders([appt(status=s)], NOW), [])
        self.assertEqual(plan_reminders([appt(starts_at=L(2026, 10, 1, 9, 0))], NOW), [])

    def test_errors_and_purity(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 10, 0))
        items = [appt(), {"id": "bad"}, appt(id="A9", starts_at=datetime(2026, 11, 1))]
        before = copy.deepcopy(items)
        r = plan_reminders(items, NOW)
        self.assertEqual(items, before)
        self.assertEqual({x["appointment_id"] for x in r}, {"A1"})

    def test_sorted_and_never_past(self):
        starts = [L(2026, 10, 20, 7, 0) + timedelta(minutes=47 * i) for i in range(40)]
        appts = [appt(id=str(i), starts_at=s) for i, s in enumerate(starts)]
        for k in range(0, 24 * 60 * 4, 37):
            now = datetime(2026, 10, 17, 0, 0, tzinfo=UTC) + timedelta(minutes=k)
            r = plan_reminders(appts, now)
            times = [x["send_at"] for x in r]
            self.assertEqual(times, sorted(times))
            by_id = {a["id"]: a["starts_at"] for a in appts}
            for x in r:
                self.assertGreaterEqual(x["send_at"], now)
                self.assertLess(x["send_at"], by_id[x["appointment_id"]])
                self.assertFalse(_quiet(x["send_at"]))


if __name__ == "__main__":
    unittest.main()