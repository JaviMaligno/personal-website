"""Reminder planner for Brennan Opticians appointments.

Date format in texts: "Tue 14 Oct" (English day/month abbreviations, Dublin local).
Only SMS reminders are ever produced; "email" is a legal channel value but unused.
Malformed means a missing key (id, customer_name, phone, country, status,
starts_at) or a naive/non-datetime starts_at. optout_sms_v2 may be absent.
"""
import logging
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("reminders")
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
MAX_LEN = 160
OPTOUT_TRUE_MEANS_OPTED_OUT = True  # PM-ASSUMPTION pending client (R8)
REQUIRED = ("id", "customer_name", "phone", "country", "status", "starts_at")
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def choose_channel(appt):
    """Return "sms" or None. The ONLY place for opt-out polarity and the
    no-email-fallback rule. SMS requires a non-empty phone and not opted out.
    A missing or None optout_sms_v2 is treated as not opted out. The legacy
    opt_out field is never read."""
    phone = appt.get("phone")
    if not isinstance(phone, str) or not phone.strip():
        return None
    flag = appt.get("optout_sms_v2")
    opted_out = (flag is True) if OPTOUT_TRUE_MEANS_OPTED_OUT else (flag is False)
    return None if opted_out else "sms"


def _in_window(local):
    return local.hour >= 21 or local.hour < 8


def _at(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN).astimezone(UTC)


def adjust_send_time(t, now, start):
    """Apply the quiet-hours rule (R10) with R7 precedence. Returns an aware
    UTC datetime, or None if the reminder must be dropped."""
    t = max(t, now)
    local = t.astimezone(DUBLIN)
    if _in_window(local):
        day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
        res = _at(day, 20)
        if res < now:
            ln = now.astimezone(DUBLIN)
            if not _in_window(ln):
                res = now
            else:
                day = ln.date() if ln.hour < 8 else ln.date() + timedelta(days=1)
                res = _at(day, 8)
    else:
        res = t
    return res if res < start else None


def _signature(appt):
    country = appt.get("country")
    if isinstance(country, str) and country.strip().upper() == "PL":
        return "Grzegorz Szczepański"
    return "Siobhán Ní Dhuibhir"


def _text(appt, start, aid):
    local = start.astimezone(DUBLIN)
    when = (f"{DAYS[local.weekday()]} {local.day} {MONTHS[local.month - 1]}"
            f" at {local:%H:%M}")
    sig = _signature(appt)
    name = " ".join(str(appt.get("customer_name") or "").split())
    first = name.split(" ")[0] if name else ""
    cands = [name, first]
    cands += [first[:k].rstrip() + "…" for k in range(len(first) - 1, 0, -1)]
    cands.append("")
    for i, c in enumerate(cands):
        greet = f"Hi {c}," if c else "Hi,"
        text = unicodedata.normalize(
            "NFC",
            f"{greet} reminder: your Brennan Opticians appointment is on {when}. {sig}")
        if len(text) <= MAX_LEN:
            if c != name:
                log.info("appointment %s: customer name shortened", aid)
            return text
    raise ValueError("text too long")


def _plan_one(appt, now):
    start = appt["starts_at"]
    if not isinstance(start, datetime) or start.tzinfo is None \
            or start.utcoffset() is None:
        raise ValueError("bad starts_at")
    aid = appt["id"]
    status = appt["status"]
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        log.info("appointment %s: skipped, cancelled", aid)
        return []
    start = start.astimezone(UTC)
    if start <= now:
        log.info("appointment %s: skipped, already started", aid)
        return []
    if choose_channel(appt) is None:
        log.info("appointment %s: skipped, no phone or opted out", aid)
        return []
    text = _text(appt, start, aid)
    r2 = adjust_send_time(start - timedelta(hours=2), now, start)
    r48 = adjust_send_time(start - timedelta(hours=48), now, start)
    if r2 is None:
        log.info("appointment %s: 2h reminder dropped (at/after start)", aid)
    if r48 is None:
        log.info("appointment %s: 48h reminder dropped (at/after start)", aid)
    elif r2 is not None and r48 >= r2:
        log.info("appointment %s: 48h reminder dropped (collides with 2h)", aid)
        r48 = None
    out = []
    for order, when in ((0, r48), (1, r2)):
        if when is not None:
            log.info("appointment %s: planned reminder via sms to %s at %s",
                     aid, appt["phone"].strip(), when.isoformat())
            out.append((when, str(aid), order, {
                "appointment_id": aid, "channel": "sms",
                "send_at": when, "text": text}))
    return out


def plan_reminders(appointments, now):
    now = now.astimezone(UTC)
    items = []
    for appt in appointments:
        aid = appt.get("id") if isinstance(appt, dict) else None
        try:
            if any(k not in appt for k in REQUIRED):
                raise KeyError("missing key")
            items.extend(_plan_one(appt, now))
        except Exception as exc:  # never include the appointment in output
            log.warning("appointment %s: malformed, skipped (%s)",
                        aid, type(exc).__name__)
    items.sort(key=lambda i: i[:3])
    return [i[3] for i in items]


# ---------------------------------------------------------------- tests
def _appt(**kw):
    a = {"id": "a1", "customer_name": "Mary Murphy", "email": "x@example.com",
         "phone": "+353851234567", "country": "IE", "status": "booked",
         "starts_at": datetime(2026, 7, 15, 14, 30, tzinfo=UTC),
         "optout_sms_v2": False}
    a.update(kw)
    return a


NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


class Tests(unittest.TestCase):
    def test_basic_keys_sorted_and_times(self):
        r = plan_reminders([_appt()], NOW)
        self.assertEqual(len(r), 2)
        for x in r:
            self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(x["channel"], "sms")
        s = datetime(2026, 7, 15, 14, 30, tzinfo=UTC)
        self.assertEqual([x["send_at"] for x in r],
                         [s - timedelta(hours=48), s - timedelta(hours=2)])

    def test_dublin_summer_and_winter_text(self):
        t = plan_reminders([_appt()], NOW)[0]["text"]
        self.assertIn("Wed 15 Jul at 15:30", t)
        w = _appt(starts_at=datetime(2026, 1, 20, 10, 0, tzinfo=UTC))
        t = plan_reminders([w], datetime(2026, 1, 1, tzinfo=UTC))[0]["text"]
        self.assertIn("Tue 20 Jan at 10:00", t)
        late = _appt(starts_at=datetime(2026, 7, 15, 23, 30, tzinfo=UTC))
        t = plan_reminders([late], NOW)[0]["text"]
        self.assertIn("Thu 16 Jul at 00:30", t)

    def test_48h_passed_sends_now(self):
        now = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
        a = _appt(starts_at=datetime(2026, 7, 1, 20, 0, tzinfo=UTC))
        r = plan_reminders([a], now)
        self.assertEqual([x["send_at"] for x in r],
                         [now, datetime(2026, 7, 1, 18, 0, tzinfo=UTC)])
        self.assertTrue(all(x["send_at"] >= now for x in r))

    def test_optout_and_phone(self):
        self.assertEqual(plan_reminders([_appt(optout_sms_v2=True)], NOW), [])
        self.assertEqual(plan_reminders([_appt(phone="  ")], NOW), [])
        self.assertEqual(plan_reminders([_appt(phone=None)], NOW), [])
        self.assertEqual(len(plan_reminders([_appt(opt_out=True)], NOW)), 2)
        b = _appt()
        del b["optout_sms_v2"]
        self.assertEqual(len(plan_reminders([b], NOW)), 2)
        self.assertEqual(choose_channel(_appt(optout_sms_v2=None)), "sms")

    def test_length_name_and_pl_signature(self):
        a = _appt(customer_name="Bartholomew " + "X" * 300, country=" pl ")
        for x in plan_reminders([a], NOW):
            self.assertLessEqual(len(x["text"]), 160)
            self.assertTrue(x["text"].endswith("Grzegorz Szczepański"))
            self.assertIn("15:30", x["text"])
        b = _appt(customer_name="Y" * 400)
        t = plan_reminders([b], NOW)[0]["text"]
        self.assertLessEqual(len(t), 160)
        self.assertTrue(t.endswith("Siobhán Ní Dhuibhir"))
        self.assertIn("…", t)

    def test_quiet_hours_moved_back(self):
        a = _appt(starts_at=datetime(2026, 7, 15, 8, 0, tzinfo=UTC))  # 09:00 IST
        r = plan_reminders([a], NOW)
        self.assertEqual(r[1]["send_at"], datetime(2026, 7, 14, 19, 0, tzinfo=UTC))
        for x in r:
            h = x["send_at"].astimezone(DUBLIN).hour
            self.assertTrue(8 <= h < 21)

    def test_quiet_hours_winter(self):
        a = _appt(starts_at=datetime(2026, 1, 20, 7, 0, tzinfo=UTC))
        r = plan_reminders([a], datetime(2026, 1, 1, tzinfo=UTC))
        self.assertEqual(r[1]["send_at"], datetime(2026, 1, 19, 20, 0, tzinfo=UTC))

    def test_cancelled(self):
        self.assertEqual(plan_reminders([_appt(status=" Cancelled ")], NOW), [])

    def test_2h_kept_over_48h(self):
        now = datetime(2026, 7, 1, 22, 30, tzinfo=UTC)  # 23:30 Dublin
        a = _appt(starts_at=datetime(2026, 7, 2, 9, 0, tzinfo=UTC))
        r = plan_reminders([a], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], datetime(2026, 7, 2, 7, 0, tzinfo=UTC))

    def test_drop_at_or_after_start_and_started(self):
        now = datetime(2026, 7, 1, 20, 30, tzinfo=UTC)  # 21:30 Dublin
        a = _appt(starts_at=datetime(2026, 7, 1, 21, 0, tzinfo=UTC))
        self.assertEqual(plan_reminders([a], now), [])
        p = _appt(starts_at=datetime(2026, 6, 1, tzinfo=UTC))
        self.assertEqual(plan_reminders([p], NOW), [])

    def test_malformed_skipped_and_no_email_in_logs(self):
        s = "sentinel-secret@leak.example"
        bad1 = _appt(id="bad1", email=s, starts_at=datetime(2026, 7, 15, 14, 30))
        bad2 = {"id": "bad2", "email": s}
        with self.assertLogs("reminders", level="DEBUG") as cm:
            r = plan_reminders([bad1, bad2, _appt(email=s)], NOW)
        self.assertEqual(len(r), 2)
        blob = "\n".join(cm.output) + "\n".join(x["text"] for x in r)
        self.assertNotIn(s, blob)
        self.assertNotIn("sentinel", blob)
        self.assertIn("bad1", blob)
        self.assertIn("bad2", blob)

    def test_sorted_across_appointments(self):
        a = _appt(id="b", starts_at=datetime(2026, 7, 20, 12, 0, tzinfo=UTC))
        r = plan_reminders([a, _appt()], NOW)
        times = [x["send_at"] for x in r]
        self.assertEqual(times, sorted(times))


if __name__ == "__main__":
    unittest.main()