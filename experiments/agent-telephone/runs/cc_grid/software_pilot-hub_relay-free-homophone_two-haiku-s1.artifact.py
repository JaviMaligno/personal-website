# -*- coding: utf-8 -*-
"""Appointment reminder planning for Brennan Opticians.

plan_reminders() is pure: it plans reminders and sends nothing. It logs one
INFO line per planned reminder.

Assumptions and open decisions (for client confirmation):
1. SECOND_REMINDER_HOURS = 4 is an assumption. The client did not give N.
2. Quiet-hours collision (the 20:00 move lands before now). QUIET_COLLISION
   is "send_now": the reminder is sent at now, even inside quiet hours.
   The alternative "defer_0800" sends at the next 08:00 Dublin time, and the
   reminder is dropped if that is not before starts_at.
3. Both reminders collapsing to now: KEEP_BOTH_IF_COLLAPSED = True, so both
   are kept, as the client suggested.
4. Date format: "Tue 20 Oct 2026". Day and month names are fixed English
   abbreviations, so the output does not depend on the system locale.
5. optout_sms_v2 missing or not a bool is treated as opted out (email).
6. SMS shortening: the full name is tried first, then the first given name,
   then the name truncated with "...". If none fits, the name is dropped and
   the greeting becomes "Hi,". The date, time and signature are never shortened.
7. The SMS limit is a character count (<= 160). The signature contains
   non-GSM-7 letters (for example, á, í, ń), so the real SMS segment count
   (UCS-2 encoding) may be larger than the character count suggests.
8. send_at values are returned in UTC. The 48h and 4h offsets are elapsed
   time, computed in UTC.
9. Logging: each INFO line has appointment_id, channel, and a masked contact.
   SMS contacts show only the last 4 phone digits. Email contacts show a
   truncated SHA-256 of the normalised address. Email addresses are never
   logged, which follows the audit finding in rule 9 and is a reconciliation
   of the house logging rule with it.
10. Reminders deferred past starts_at are dropped (defer mode only).
"""
import hashlib
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
FIRST_REMINDER_HOURS = 48
SECOND_REMINDER_HOURS = 4  # ASSUMPTION: N not given by client
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
DEFER_TIME = time(20, 0)
QUIET_COLLISION = "send_now"  # or "defer_0800"
KEEP_BOTH_IF_COLLAPSED = True
SMS_MAX_CHARS = 160
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

if not 0 < SECOND_REMINDER_HOURS < FIRST_REMINDER_HOURS:
    raise ValueError("invalid reminder configuration")
if QUIET_COLLISION not in ("send_now", "defer_0800"):
    raise ValueError("invalid quiet collision configuration")


def _require_aware(value, what):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")


def _is_quiet(dt_utc):
    t = dt_utc.astimezone(DUBLIN).time()
    return t >= QUIET_START or t < QUIET_END


def _previous_evening(dt_utc):
    local = dt_utc.astimezone(DUBLIN)
    day = local.date()
    if local.time() < QUIET_END:
        day -= timedelta(days=1)
    return datetime.combine(day, DEFER_TIME, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(dt_utc):
    local = dt_utc.astimezone(DUBLIN)
    day = local.date()
    if local.time() >= QUIET_END:
        day += timedelta(days=1)
    return datetime.combine(day, QUIET_END, tzinfo=DUBLIN).astimezone(UTC)


def _schedule(base, now, starts_utc):
    if base < now:
        base = now
    if not _is_quiet(base):
        return base
    moved = _previous_evening(base)
    if moved >= now:
        return moved
    if QUIET_COLLISION == "send_now":
        return now
    deferred = _next_morning(now)
    return deferred if deferred < starts_utc else None


def _choose_channel(appt):
    optout = appt.get("optout_sms_v2")
    if not isinstance(optout, bool):
        optout = True
    phone = appt.get("phone")
    email = appt.get("email")
    if isinstance(phone, str) and phone.strip() and not optout:
        return "sms", phone.strip()
    if isinstance(email, str) and email.strip():
        return "email", email.strip()
    return None, None


def _clean_name(value):
    return value.strip() if isinstance(value, str) else ""


def _compose(name, date_str, time_str, sig):
    greeting = f"Hi {name}, " if name else "Hi, "
    return (f"{greeting}your Brennan Opticians appointment is on "
            f"{date_str} at {time_str}. {sig}")


def _sms_text(name, date_str, time_str, sig):
    options = [name]
    parts = name.split()
    if parts and parts[0] != name:
        options.append(parts[0])
    for cand in options:
        text = _compose(cand, date_str, time_str, sig)
        if len(text) <= SMS_MAX_CHARS:
            return text
    for k in range(len(name) - 1, 0, -1):
        cand = name[:k].rstrip() + "..."
        text = _compose(cand, date_str, time_str, sig)
        if len(text) <= SMS_MAX_CHARS:
            return text
    return _compose("", date_str, time_str, sig)


def _mask(channel, contact):
    if channel == "sms":
        digits = "".join(ch for ch in contact if ch.isdigit())
        return "phone:***" + digits[-4:]
    digest = hashlib.sha256(contact.lower().encode("utf-8")).hexdigest()[:10]
    return "email:sha256:" + digest


def _plan_one(appt, now_utc):
    starts_at = appt.get("starts_at")
    _require_aware(starts_at, "starts_at")
    if appt.get("status") == "cancelled":
        return []
    starts_utc = starts_at.astimezone(UTC)
    if starts_utc <= now_utc:
        return []
    channel, contact = _choose_channel(appt)
    if channel is None:
        return []

    r1 = _schedule(starts_utc - timedelta(hours=FIRST_REMINDER_HOURS),
                   now_utc, starts_utc)
    r2 = _schedule(starts_utc - timedelta(hours=SECOND_REMINDER_HOURS),
                   now_utc, starts_utc)
    times = [r1, r2]
    if not KEEP_BOTH_IF_COLLAPSED and r1 is not None and r1 == r2:
        times = [r1]

    name = _clean_name(appt.get("customer_name"))
    sig = SIGNATURE_PL if appt.get("country") == "PL" else SIGNATURE
    local = starts_utc.astimezone(DUBLIN)
    date_str = (f"{_DAYS[local.weekday()]} {local.day} "
                f"{_MONTHS[local.month - 1]} {local.year}")
    time_str = f"{local.hour:02d}:{local.minute:02d}"

    out = []
    for send_at in times:
        if send_at is None:
            continue
        if channel == "sms":
            text = _sms_text(name, date_str, time_str, sig)
            if len(text) > SMS_MAX_CHARS:
                raise ValueError("SMS text exceeds limit")
        else:
            text = _compose(name, date_str, time_str, sig)
        out.append({
            "appointment_id": appt.get("id"),
            "channel": channel,
            "send_at": send_at,
            "text": text,
        })
        log.info("planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                 appt.get("id"), channel, _mask(channel, contact),
                 send_at.isoformat())
    return out


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        planned.extend(_plan_one(appt, now_utc))
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


def _appt(**overrides):
    appt = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": "aoife@example.com",
        "phone": "+353861234567",
        "country": "IE",
        "status": "booked",
        "starts_at": datetime(2026, 10, 20, 10, 0, tzinfo=DUBLIN),
        "optout_sms_v2": False,
    }
    appt.update(overrides)
    return appt


NOW_OCT10 = datetime(2026, 10, 10, 12, 0, tzinfo=DUBLIN)


class PlanRemindersTests(unittest.TestCase):

    def test_sms_gets_two_sms(self):
        out = plan_reminders([_appt()], NOW_OCT10)
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])
        self.assertEqual(out[0]["send_at"], datetime(2026, 10, 18, 9, 0, tzinfo=UTC))
        self.assertEqual(out[1]["send_at"], datetime(2026, 10, 19, 19, 0, tzinfo=UTC))
        self.assertIn("Tue 20 Oct 2026 at 10:00", out[0]["text"])
        self.assertTrue(out[0]["text"].endswith(" Siobhán Ní Dhuibhir"))

    def test_optout_gets_email_only(self):
        out = plan_reminders([_appt(optout_sms_v2=True)], NOW_OCT10)
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_missing_optout_defaults_to_email(self):
        appt = _appt()
        del appt["optout_sms_v2"]
        out = plan_reminders([appt], NOW_OCT10)
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_no_phone_uses_email(self):
        for phone in (None, "", "   "):
            out = plan_reminders([_appt(phone=phone)], NOW_OCT10)
            self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_no_phone_no_email_gets_nothing(self):
        out = plan_reminders([_appt(phone=None, email="")], NOW_OCT10)
        self.assertEqual(out, [])

    def test_cancelled_gets_nothing(self):
        self.assertEqual(plan_reminders([_appt(status="cancelled")], NOW_OCT10), [])

    def test_past_appointment_gets_nothing(self):
        appt = _appt(starts_at=NOW_OCT10 - timedelta(hours=1))
        self.assertEqual(plan_reminders([appt], NOW_OCT10), [])

    def test_48h_past_sends_first_at_now(self):
        now = datetime(2026, 10, 19, 12, 0, tzinfo=DUBLIN)
        out = plan_reminders([_appt()], now)
        self.assertEqual(out[0]["send_at"], now.astimezone(UTC))
        for r in out:
            self.assertGreaterEqual(r["send_at"], now.astimezone(UTC))

    def test_quiet_collision_collapses_both_to_now(self):
        now = datetime(2026, 10, 19, 20, 30, tzinfo=DUBLIN)
        appt = _appt(starts_at=datetime(2026, 10, 20, 6, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(len(out), 2)
        self.assertEqual([r["send_at"] for r in out], [now.astimezone(UTC)] * 2)

    def test_spring_dst_quiet_move(self):
        now = datetime(2026, 3, 25, 12, 0, tzinfo=UTC)
        appt = _appt(starts_at=datetime(2026, 3, 30, 8, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(out[0]["send_at"], datetime(2026, 3, 27, 20, 0, tzinfo=UTC))
        self.assertEqual(out[1]["send_at"], datetime(2026, 3, 29, 19, 0, tzinfo=UTC))

    def test_autumn_dst_quiet_move(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=DUBLIN)
        appt = _appt(starts_at=datetime(2026, 10, 27, 8, 30, tzinfo=DUBLIN))
        out = plan_reminders([appt], now)
        self.assertEqual(out[0]["send_at"], datetime(2026, 10, 25, 8, 30, tzinfo=UTC))
        self.assertEqual(out[1]["send_at"], datetime(2026, 10, 26, 20, 0, tzinfo=UTC))

    def test_no_send_in_quiet_hours(self):
        out = plan_reminders([_appt()], NOW_OCT10)
        for r in out:
            local = r["send_at"].astimezone(DUBLIN)
            self.assertFalse(local.hour >= 21 or local.hour < 8)

    def test_sorted_output(self):
        appts = [_appt(id="B2"), _appt(id="A1", starts_at=datetime(2026, 10, 21, 15, 0, tzinfo=DUBLIN))]
        out = plan_reminders(appts, NOW_OCT10)
        keys = [(r["send_at"], str(r["appointment_id"]), r["channel"]) for r in out]
        self.assertEqual(keys, sorted(keys))

    def test_long_name_sms_fits(self):
        out = plan_reminders([_appt(customer_name="Q" * 300)], NOW_OCT10)
        for r in out:
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("Tue 20 Oct 2026 at 10:00", r["text"])
            self.assertTrue(r["text"].endswith(" Siobhán Ní Dhuibhir"))

    def test_polish_signature(self):
        out = plan_reminders([_appt(country="PL", optout_sms_v2=True)], NOW_OCT10)
        self.assertTrue(out[0]["text"].endswith(" Grzegorz Szczepański"))

    def test_naive_datetimes_rejected_without_data(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([_appt()], datetime(2026, 10, 10, 12, 0))
        self.assertNotIn("@", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 10, 0))], NOW_OCT10)
        self.assertNotIn("@", str(cm.exception))

    def test_logs_never_contain_email(self):
        with self.assertLogs(__name__, level="INFO") as cm:
            plan_reminders([_appt(optout_sms_v2=True)], NOW_OCT10)
        self.assertEqual(len(cm.output), 2)
        for line in cm.output:
            self.assertNotIn("aoife@example.com", line)
            self.assertIn("channel=email", line)


if __name__ == "__main__":
    unittest.main()