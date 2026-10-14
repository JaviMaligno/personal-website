"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now). Pure apart from one INFO log
line per planned reminder (appointment id, channel, phone number; never email).

AMBIGUITY, PLEASE CONFIRM WITH THE CLIENT (compliance risk)
  The client wrote "text them if they have a phone number, if optout_sms_v2
  is true". The field name suggests that True means the customer HAS OPTED OUT.
  The PM suggested the fail-safe reading (True = opted out, so do not text).
  This module implements the client's LITERAL wording: SMS is sent only when
  optout_sms_v2 is True; missing, None or non-bool means no SMS. If the field
  really means "opted out", people who opted out would be texted. The rule
  lives in one predicate, _sms_allowed(); flipping it is a one-line change.

OTHER OPEN POINTS FOR THE CLIENT
  - Email is never used, not even as a fallback; "email" is never emitted.
  - If the 2h point has already passed, the 2h reminder is dropped, not sent late.
  - The function is stateless: running it again re-plans the same reminders
    (including an "immediate" one at each run's now), so the caller must
    de-duplicate across runs.
  - Texts with fadas/diacritics (e.g. Siobhan Ni Dhuibhir, Szczepanski) are
    sent as UCS-2, so one SMS segment holds only 70 characters; a 160-character
    text may bill as 3 segments or more.
  - Times are Europe/Dublin even for the Krakow branch (country PL); Krakow
    local time is normally 1 hour ahead of Dublin.
"""
import copy
import logging
import unicodedata
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
MAX_SMS = 160
logger = logging.getLogger(__name__)


def _sms_allowed(appt):
    """Opt-out predicate. LITERAL client reading: send only if flag is True.
    To use the fail-safe reading, change to: `... is False`-style logic."""
    return appt.get("optout_sms_v2") is True


def _aware(dt, what):
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")
    return dt.astimezone(UTC)


def _quiet(local):
    return local.hour >= 21 or local.hour < 8


def _wall(day, hour):
    return datetime.combine(day, time(hour), tzinfo=DUB).astimezone(UTC)


def _place(point, now):
    cand = max(point, now)
    loc = cand.astimezone(DUB)
    if not _quiet(loc):
        return cand
    day = loc.date() if loc.hour >= 21 else loc.date() - timedelta(days=1)
    moved = _wall(day, 20)
    if moved >= now:
        return moved
    nl = now.astimezone(DUB)
    if not _quiet(nl):
        return now
    day = nl.date() + timedelta(days=1) if nl.hour >= 21 else nl.date()
    return _wall(day, 8)


def _text(appt, starts):
    loc = starts.astimezone(DUB)
    country = str(appt.get("country") or "").strip().upper()
    sig = "Grzegorz Szczepański" if country == "PL" else "Siobhán Ní Dhuibhir"
    name = unicodedata.normalize("NFC", " ".join(str(appt.get("customer_name") or "").split()))
    tokens = name.split()
    options = [name]
    if tokens:
        options += [tokens[0], ".".join(t[0] for t in tokens).upper() + "."]
    options.append("")
    tail = (f"reminder: your Brennan Opticians appointment is on "
            f"{loc:%d/%m/%Y} at {loc:%H:%M}. {sig}")
    text = ""
    for opt in options:
        text = unicodedata.normalize("NFC", f"Hi {opt}, {tail}" if opt else f"Hi, {tail}")
        if len(text) <= MAX_SMS:
            break
    return text


def _idkey(i):
    return (0, i, "") if isinstance(i, int) else (1, 0, str(i))


def plan_reminders(appointments, now):
    now = _aware(now, "now")
    items = []
    for a in appointments:
        if str(a.get("status") or "").strip().casefold() == "cancelled":
            continue
        starts = _aware(a["starts_at"], "starts_at")
        phone = a.get("phone")
        if not (isinstance(phone, str) and phone.strip()) or not _sms_allowed(a):
            continue
        phone = phone.strip()
        slots = []
        for order, hours in ((0, 48), (1, 2)):
            point = starts - timedelta(hours=hours)
            if order == 1 and point < now:
                continue
            when = _place(point, now)
            if when >= starts:
                continue
            slots.append((order, when))
        if len(slots) == 2 and slots[0][1] == slots[1][1]:
            slots = slots[1:]
        text = _text(a, starts)
        for order, when in slots:
            out = {"appointment_id": a.get("id"), "channel": "sms",
                   "send_at": when.astimezone(DUB), "text": text}
            logger.info("reminder planned: appointment_id=%s channel=sms contact=%s send_at=%s",
                        a.get("id"), phone, out["send_at"].isoformat())
            items.append((when, _idkey(a.get("id")), order, out))
    items.sort(key=lambda t: t[:3])
    return [t[3] for t in items]


# ----------------------------- tests -----------------------------

def D(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUB)


EMAIL = "mary.murphy@example.com"


def appt(**kw):
    base = dict(id="a1", customer_name="Mary Murphy", email=EMAIL, phone="+353851234567",
                country="IE", status="booked", starts_at=D(2026, 6, 10, 14),
                optout_sms_v2=True)
    base.update(kw)
    return base


class PlanTests(unittest.TestCase):
    NOW = D(2026, 6, 1, 9)

    def run_one(self, now=None, **kw):
        return plan_reminders([appt(**kw)], now or self.NOW)

    def test_cancelled(self):
        self.assertEqual(self.run_one(status=" CanCelled "), [])

    def test_optout_and_phone(self):
        for v in (False, None, "true", 1):
            self.assertEqual(self.run_one(optout_sms_v2=v), [])
        self.assertEqual(plan_reminders([{k: v for k, v in appt().items()
                                          if k != "optout_sms_v2"}], self.NOW), [])
        for p in ("", "   ", None):
            self.assertEqual(self.run_one(phone=p), [])

    def test_shape_and_timing(self):
        r = self.run_one()
        self.assertEqual([x["send_at"] for x in r], [D(2026, 6, 8, 14), D(2026, 6, 10, 12)])
        for x in r:
            self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(x["channel"], "sms")
            self.assertEqual(x["send_at"].tzinfo, DUB)
        self.assertEqual(r[0]["text"], "Hi Mary Murphy, reminder: your Brennan Opticians "
                         "appointment is on 10/06/2026 at 14:00. Siobhán Ní Dhuibhir")

    def test_immediate(self):
        r = self.run_one(starts_at=D(2026, 6, 2, 14), now=D(2026, 6, 1, 10))
        self.assertEqual([x["send_at"] for x in r], [D(2026, 6, 1, 10), D(2026, 6, 2, 12)])

    def test_same_send_at_keeps_one(self):
        r = self.run_one(starts_at=D(2026, 6, 1, 12), now=D(2026, 6, 1, 10))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], D(2026, 6, 1, 10))

    def test_2h_passed_dropped(self):
        r = self.run_one(starts_at=D(2026, 6, 1, 9, 30))
        self.assertEqual([x["send_at"] for x in r], [self.NOW])

    def test_never_past_or_after_start(self):
        starts = D(2026, 6, 2, 15)
        for k in range(200):
            now = D(2026, 6, 1) + timedelta(minutes=37 * k)
            for x in self.run_one(now=now, starts_at=starts):
                self.assertTrue(now <= x["send_at"] < starts)
        self.assertEqual(self.run_one(starts_at=self.NOW), [])
        self.assertEqual(self.run_one(starts_at=D(2026, 5, 1)), [])

    def test_quiet_boundaries(self):
        now = D(2026, 6, 1, 8)
        cases = {(23, 0): D(2026, 6, 1, 20), (22, 59): D(2026, 6, 1, 20, 59),
                 (9, 59): D(2026, 6, 1, 7, 59), (10, 0): D(2026, 6, 1, 8)}
        for (h, m), expect in cases.items():
            r = self.run_one(now=now, starts_at=D(2026, 6, 1, h, m))
            exp = expect if expect >= now else now
            if (h, m) == (9, 59):
                exp = D(2026, 6, 1, 8)  # 07:59 is quiet -> 20:00 prev day < now -> now
            self.assertEqual(r[-1]["send_at"], exp, (h, m))
        r = self.run_one(now=D(2026, 6, 1, 7), starts_at=D(2026, 6, 2, 9, 59))
        self.assertEqual(r[-1]["send_at"], D(2026, 6, 1, 20))

    def test_now_in_quiet_hours(self):
        r = self.run_one(now=D(2026, 6, 1, 23), starts_at=D(2026, 6, 2, 12))
        self.assertEqual([x["send_at"] for x in r], [D(2026, 6, 2, 8), D(2026, 6, 2, 10)])
        r = self.run_one(now=D(2026, 6, 2, 3), starts_at=D(2026, 6, 2, 12))
        self.assertEqual([x["send_at"] for x in r], [D(2026, 6, 2, 8), D(2026, 6, 2, 10)])
        self.assertEqual(self.run_one(now=D(2026, 6, 1, 23), starts_at=D(2026, 6, 2, 3)), [])

    def test_dst_march(self):
        now = D(2026, 3, 20, 12)
        r = self.run_one(now=now, starts_at=D(2026, 3, 29, 12))
        self.assertEqual(r[0]["send_at"].astimezone(UTC), datetime(2026, 3, 27, 11, tzinfo=UTC))
        self.assertEqual(r[1]["send_at"].astimezone(UTC), datetime(2026, 3, 29, 9, tzinfo=UTC))
        r = self.run_one(now=now, starts_at=D(2026, 3, 29, 8, 30))
        s = r[-1]["send_at"]
        self.assertEqual((s.day, s.hour, s.utcoffset()), (28, 20, timedelta(0)))

    def test_dst_october(self):
        now = D(2026, 10, 20, 12)
        r = self.run_one(now=now, starts_at=D(2026, 10, 25, 12))
        self.assertEqual((r[0]["send_at"].day, r[0]["send_at"].hour), (23, 13))
        r = self.run_one(now=now, starts_at=D(2026, 10, 25, 8, 30))
        s = r[-1]["send_at"]
        self.assertEqual((s.day, s.hour, s.utcoffset()), (24, 20, timedelta(hours=1)))
        self.assertEqual(s.astimezone(UTC), datetime(2026, 10, 24, 19, tzinfo=UTC))

    def test_pl_signature(self):
        r = self.run_one(country=" pl ")
        self.assertTrue(r[0]["text"].endswith(". Grzegorz Szczepański"))
        r = self.run_one(customer_name="Zo\u0065\u0301 Ni\u0301")
        self.assertEqual(r[0]["text"], unicodedata.normalize("NFC", r[0]["text"]))
        self.assertTrue(r[0]["text"].endswith("Siobhán Ní Dhuibhir"))
        self.assertTrue(self.run_one(customer_name="")[0]["text"].startswith("Hi, reminder:"))

    def test_long_name(self):
        tail = "on 10/06/2026 at 14:00. Siobhán Ní Dhuibhir"
        cases = [("A" * 150 + " Smith", "Hi A.S., "),
                 ("Bartholomew " + "X" * 150, "Hi Bartholomew, "),
                 ("X" * 300, "Hi, ")]
        for name, prefix in cases:
            t = self.run_one(customer_name=name)[0]["text"]
            self.assertLessEqual(len(t), 160)
            self.assertTrue(t.startswith(prefix), t)
            self.assertTrue(t.endswith(tail))

    def test_sorting(self):
        now = D(2026, 6, 1, 10)
        appts = [appt(id="b", starts_at=D(2026, 6, 1, 12)),
                 appt(id="a", starts_at=D(2026, 6, 1, 12)),
                 appt(id="c", starts_at=D(2026, 6, 3, 14))]
        r = plan_reminders(appts, now)
        keys = [(x["send_at"].astimezone(UTC), x["appointment_id"]) for x in r]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([x["appointment_id"] for x in r[:2]], ["a", "b"])
        c = [x["send_at"] for x in r if x["appointment_id"] == "c"]
        self.assertEqual(c, sorted(c))

    def test_no_mutation(self):
        appts = [appt(), appt(id="z", status="cancelled")]
        before = copy.deepcopy(appts)
        plan_reminders(appts, self.NOW)
        self.assertEqual(appts, before)

    def test_naive_raises_without_data(self):
        bad = appt(starts_at=datetime(2026, 6, 10, 14))
        with self.assertRaises(ValueError) as c:
            plan_reminders([bad], self.NOW)
        self.assertNotIn(EMAIL, str(c.exception))
        self.assertNotIn("Mary", str(c.exception))
        with self.assertRaises(ValueError):
            plan_reminders([appt()], datetime(2026, 6, 1, 9))

    def test_no_email_in_logs(self):
        with self.assertLogs(logger, "INFO") as cm:
            r = plan_reminders([appt()], self.NOW)
        out = "\n".join(cm.output)
        self.assertNotIn(EMAIL, out)
        self.assertEqual(len(cm.records), len(r))
        self.assertIn("sms", out)
        self.assertIn("+353851234567", out)


if __name__ == "__main__":
    unittest.main()