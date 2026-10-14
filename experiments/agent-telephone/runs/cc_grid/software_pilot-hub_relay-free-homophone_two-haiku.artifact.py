# /abs/path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-x7zs_ygw/reminders.py
# NOTE: This session has no file or shell tools, so this file was not written to disk and the tests were not run.
# Save it at the path above, then run: python -I /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-x7zs_ygw/test_reminders.py
#
# Defaults chosen where the client did not specify (for the report):
#   - SECOND_LEAD = 2h (proposed).
#   - Quiet-hour shift to 20:00 Dublin, and the fallback to now or the next 08:00 (proposed, unconfirmed).
#   - Missing name in email: "Hello," (no name).
#   - Status compared case-insensitively after trimming; None is sendable.
#   - Phone: any non-blank string is valid.
#   - SMS length counted in Python characters (code points), not bytes or UCS-2 units.
#   - Email contact in logs is redacted; SMS contact logs only the last 4 digits.
"""Appointment reminder planning for Brennan Opticians."""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

FIRST_LEAD = timedelta(hours=48)
# PROPOSED DEFAULT: client said "some hours before" with no number.
SECOND_LEAD = timedelta(hours=2)

QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
EVENING_SEND = time(20, 0)  # quiet-hour shift target (proposed default)

SMS_MAX_LEN = 160
SIGNOFF_DEFAULT = "Siobhán Ní Dhuibhir"
SIGNOFF_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _in_quiet(dt_utc):
    t = dt_utc.astimezone(DUBLIN).time()
    return t >= QUIET_START or t < QUIET_END


def _quiet_shift(dt_utc):
    """Move a quiet-hour instant back to 20:00 Dublin on the same or previous evening."""
    local = dt_utc.astimezone(DUBLIN)
    day = local.date()
    if local.time() < QUIET_END:
        day -= timedelta(days=1)
    return datetime.combine(day, EVENING_SEND, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(now_utc):
    """Next 08:00 Dublin local after a quiet-hour 'now'."""
    local = now_utc.astimezone(DUBLIN)
    day = local.date()
    if local.time() >= QUIET_START:
        day += timedelta(days=1)
    return datetime.combine(day, QUIET_END, tzinfo=DUBLIN).astimezone(UTC)


def _settle(target, now_utc):
    """Return a send instant >= now_utc that is outside quiet hours.

    Caller guarantees target >= now_utc.
    """
    if not _in_quiet(target):
        return target
    shifted = _quiet_shift(target)
    if shifted >= now_utc:
        return shifted
    if not _in_quiet(now_utc):
        return now_utc
    return _next_morning(now_utc)


def _date_time_text(starts_utc):
    local = starts_utc.astimezone(DUBLIN)
    date = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    return date, f"{local.hour:02d}:{local.minute:02d}"


def _clean_name(raw):
    if not isinstance(raw, str):
        return ""
    return " ".join(raw.split())


def _name_variants(full):
    """Name forms in SMS fallback order: full, first name, initial with full stop."""
    if not full:
        return []
    first = full.split(" ")[0]
    return [full, first, first[0] + "."]


def _signoff(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIGNOFF_PL
    return SIGNOFF_DEFAULT


def _sms_text(kind, names, date, clock, signoff):
    if kind == "first":
        core = f"reminder of your Brennan Opticians appointment on {date} at {clock}. {signoff}"
    else:
        core = f"your Brennan Opticians appointment is on {date} at {clock}. See you soon! {signoff}"
    for name in names:
        text = f"Hi {name}, {core}"
        if len(text) <= SMS_MAX_LEN:
            return text
    # Greeting dropped; this form is always short enough.
    return core[0].upper() + core[1:]


def _email_text(full_name, date, clock, signoff):
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    return (f"{greeting}\n"
            f"This is a reminder of your appointment at Brennan Opticians on {date} at {clock}.\n"
            f"Kind regards,\n"
            f"{signoff}")


def _pick_channel(a):
    has_email = isinstance(a.get("email"), str) and a["email"].strip() != ""
    has_phone = isinstance(a.get("phone"), str) and a["phone"].strip() != ""
    if bool(a.get("optout_sms_v2")):
        return "email" if has_email else None
    if has_phone:
        return "sms"
    if has_email:
        return "email"
    return None


def _contact(channel, a):
    """Log-safe contact label. Never includes the email address."""
    if channel == "sms":
        digits = a["phone"].strip()
        return "sms:***" + (digits[-4:] if len(digits) > 4 else "")
    return "email:address-redacted"


def _plan_one(a, now_utc):
    appt_id = a.get("id")
    status = a.get("status")
    if status is not None and str(status).strip().lower() == "cancelled":
        return []

    starts = a.get("starts_at")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError(f"starts_at must be timezone-aware (appointment {appt_id})")
    starts_utc = starts.astimezone(UTC)
    if starts_utc <= now_utc:
        return []

    channel = _pick_channel(a)
    if channel is None:
        return []

    slots = [("first", _settle(max(starts_utc - FIRST_LEAD, now_utc), now_utc))]
    second_target = starts_utc - SECOND_LEAD
    if second_target >= now_utc:
        slots.append(("second", _settle(second_target, now_utc)))

    date, clock = _date_time_text(starts_utc)
    full_name = _clean_name(a.get("customer_name"))
    signoff = _signoff(a.get("country"))

    out = []
    for kind, send_at in slots:
        if channel == "sms":
            text = _sms_text(kind, _name_variants(full_name), date, clock, signoff)
        else:
            text = _email_text(full_name, date, clock, signoff)
        log.info("reminder planned appointment_id=%s channel=%s to=%s send_at=%s",
                 appt_id, channel, _contact(channel, a), send_at.isoformat())
        out.append({"appointment_id": appt_id, "channel": channel,
                    "send_at": send_at, "text": text})
    return out


def plan_reminders(appointments, now):
    if now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    rows = []
    for a in appointments:
        rows.extend(_plan_one(a, now_utc))
    rows.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return rows


# /abs/path: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-x7zs_ygw/test_reminders.py
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reminders as R

D = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=D)


def dub(*args):
    return datetime(*args, tzinfo=D)


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def appt(**kw):
    a = {"id": "A1", "customer_name": "Aoife Murphy", "email": "aoife@example.com",
         "phone": "+353871234567", "country": "IE", "status": "booked",
         "starts_at": dub(2026, 10, 20, 14, 0), "optout_sms_v2": False}
    a.update(kw)
    return a


def plan(*appts, now=NOW):
    return R.plan_reminders(list(appts), now)


def times(rows):
    return [r["send_at"] for r in rows]


def is_quiet(dt):
    h = dt.astimezone(D).hour
    return h >= 21 or h < 8


class TimingTests(unittest.TestCase):
    def test_48h_and_2h(self):
        rows = plan(appt())
        self.assertEqual(times(rows), [dub(2026, 10, 18, 14, 0), dub(2026, 10, 20, 12, 0)])

    def test_first_sent_now_when_48h_passed(self):
        now = dub(2026, 10, 19, 10, 0)
        rows = plan(appt(), now=now)
        self.assertEqual(times(rows), [now, dub(2026, 10, 20, 12, 0)])

    def test_exact_now_is_not_past(self):
        now = dub(2026, 10, 18, 14, 0)
        rows = plan(appt(), now=now)
        self.assertEqual(times(rows)[0], now)
        self.assertEqual(len(rows), 2)

    def test_second_omitted_when_past(self):
        now = dub(2026, 10, 20, 12, 30)
        rows = plan(appt(), now=now)
        self.assertEqual(times(rows), [now])

    def test_dst_absolute_arithmetic(self):
        rows = plan(appt(starts_at=dub(2026, 10, 26, 10, 0)))
        self.assertEqual(rows[0]["send_at"], utc(2026, 10, 24, 10, 0))
        self.assertEqual(rows[0]["send_at"].astimezone(D).hour, 11)

    def test_past_appointment_produces_nothing(self):
        self.assertEqual(plan(appt(starts_at=dub(2026, 10, 10, 11, 0))), [])


class QuietTests(unittest.TestCase):
    def test_2330_shifts_to_2000_same_evening(self):
        rows = plan(appt(starts_at=dub(2026, 10, 21, 1, 30)))
        self.assertEqual(times(rows), [dub(2026, 10, 18, 20, 0), dub(2026, 10, 20, 20, 0)])

    def test_0600_shifts_to_previous_evening(self):
        rows = plan(appt(starts_at=dub(2026, 10, 20, 6, 0)))
        self.assertEqual(times(rows), [dub(2026, 10, 17, 20, 0), dub(2026, 10, 19, 20, 0)])

    def test_shifted_before_now_uses_now(self):
        now = dub(2026, 10, 18, 9, 0)
        rows = plan(appt(starts_at=dub(2026, 10, 20, 6, 0)), now=now)
        self.assertEqual(times(rows)[0], now)
        self.assertEqual(len(rows), 2)

    def test_now_in_quiet_hours_sends_next_morning(self):
        now = dub(2026, 10, 19, 22, 0)
        rows = plan(appt(starts_at=dub(2026, 10, 20, 0, 30)), now=now)
        self.assertEqual(times(rows), [dub(2026, 10, 20, 8, 0), dub(2026, 10, 20, 8, 0)])

    def test_never_before_now_or_in_quiet(self):
        base = NOW.astimezone(UTC)
        appts = [appt(id=str(i), starts_at=base + timedelta(minutes=37 * i))
                 for i in range(1, 400)]
        rows = plan(*appts)
        self.assertTrue(rows)
        for r in rows:
            self.assertGreaterEqual(r["send_at"], NOW)
            self.assertFalse(is_quiet(r["send_at"]))
        self.assertEqual(times(rows), sorted(times(rows)))


class ChannelTests(unittest.TestCase):
    def test_optout_email_only(self):
        rows = plan(appt(optout_sms_v2=True))
        self.assertEqual({r["channel"] for r in rows}, {"email"})
        self.assertEqual(len(rows), 2)

    def test_optout_without_email_gives_nothing(self):
        self.assertEqual(plan(appt(optout_sms_v2=True, email="")), [])
        self.assertEqual(plan(appt(optout_sms_v2=True, email=None)), [])

    def test_old_opt_out_field_ignored(self):
        rows = plan(appt(opt_out=True, optout_sms_v2=False))
        self.assertEqual({r["channel"] for r in rows}, {"sms"})

    def test_missing_optout_treated_as_false(self):
        a = appt()
        del a["optout_sms_v2"]
        self.assertEqual({r["channel"] for r in plan(a)}, {"sms"})

    def test_missing_phone_gives_email(self):
        for phone in ("   ", None, ""):
            rows = plan(appt(phone=phone))
            self.assertEqual({r["channel"] for r in rows}, {"email"})

    def test_cancelled_gives_nothing(self):
        self.assertEqual(plan(appt(status="cancelled")), [])

    def test_no_contact_gives_nothing(self):
        self.assertEqual(plan(appt(phone="", email="")), [])


class TextTests(unittest.TestCase):
    def test_sms_cap_keeps_date_and_time(self):
        long_name = "Maximilian Alexander-Montgomery Wolfeschlegelsteinhausenbergerdorff"
        rows = plan(appt(customer_name=long_name))
        self.assertTrue(rows)
        for r in rows:
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("20 Oct 2026", r["text"])
            self.assertIn("14:00", r["text"])
            self.assertTrue(r["text"].endswith(R.SIGNOFF_DEFAULT))

    def test_missing_name_drops_greeting(self):
        rows = plan(appt(customer_name=None))
        for r in rows:
            self.assertFalse(r["text"].startswith("Hi"))
            self.assertIn("20 Oct 2026", r["text"])
            self.assertIn("14:00", r["text"])

    def test_pl_signoff_sms_and_email(self):
        for r in plan(appt(country=" pl ")):
            self.assertTrue(r["text"].endswith(R.SIGNOFF_PL))
        for r in plan(appt(country=" pl ", optout_sms_v2=True)):
            self.assertEqual(r["channel"], "email")
            self.assertTrue(r["text"].endswith(R.SIGNOFF_PL))

    def test_email_body_format(self):
        rows = plan(appt(optout_sms_v2=True))
        expected = ("Hello Aoife Murphy,\n"
                    "This is a reminder of your appointment at Brennan Opticians on 20 Oct 2026 at 14:00.\n"
                    "Kind regards,\n"
                    "Siobhán Ní Dhuibhir")
        self.assertEqual(rows[0]["text"], expected)


class SortTests(unittest.TestCase):
    def test_sorted_with_tiebreak(self):
        a = appt(id="B", starts_at=dub(2026, 10, 20, 14, 0))
        b = appt(id="A", starts_at=dub(2026, 10, 20, 14, 0))
        c = appt(id="C", starts_at=dub(2026, 10, 22, 9, 0))
        rows = plan(a, b, c)
        keys = [(r["send_at"], r["appointment_id"], r["channel"]) for r in rows]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(rows[0]["appointment_id"], "A")
        self.assertEqual(rows[1]["appointment_id"], "B")


if __name__ == "__main__":
    unittest.main()