# ===== brennan_reminders.py =====
"""Appointment reminder planning for Brennan Opticians.

Single entry point: plan_reminders(appointments, now).

Stateless: plan_reminders does not record what was sent. The caller must
de-duplicate reminders across repeated runs (R19).

Assumptions:
- Offsets are elapsed time (UTC arithmetic): 48h and 2h before starts_at.
- Returned send_at values are timezone-aware UTC datetimes.
- If the 48h point has passed at now, the first reminder is sent at now (R5).
- Quiet hours are 21:00 to 08:00 Europe/Dublin. 21:00 is quiet, 08:00 is allowed.
- A send time in quiet hours moves to 20:00 Europe/Dublin on the evening that
  opens the quiet window: the same date if the time is 21:00 or later, the
  previous date if the time is before 08:00.
- If that 20:00 is before now: send at now if now is in allowed hours,
  otherwise send at the next 08:00 Europe/Dublin at or after now. The
  allowed-hours case is a deviation from the default "next 08:00 after now",
  made because sending at now satisfies R6 and R10.
- If the 2h point has passed at now, the second reminder is dropped.
- An appointment at or before now produces no reminders (R23).
- Channel: SMS if phone is present and not opted out. Email if opted out (or
  optout_sms_v2 is missing, R25) and phone is present, or if phone is missing
  and not opted out (R21). Opted out with no phone gives no reminder. Email
  channel with an empty email address gives no reminder.
- Email reminders carry no address field (open schema question). The address
  is never returned or logged.
- Email subject is not produced. The body is a placeholder containing the
  greeting, date, time and signature (copy pending the client).
- SMS: len() characters, limit 160. The name is truncated with "..." first and
  dropped entirely if still too long. Date, time and signature are always kept.
  Non-GSM characters (for example the diacritics in the Polish signature) would
  switch SMS to UCS-2 with a 70-character limit. This is flagged, not implemented.
- Date format: "14 Oct 2026" with day zero-padded, and "at HH:MM", both in
  Europe/Dublin.
- Required fields: id, customer_name, email, status, starts_at. Optional
  fields: phone, country, optout_sms_v2. Malformed records raise ValueError
  naming only the field and index, never a value.
- status is compared after strip().lower() to "cancelled" (R11, R22).
- Country "PL" is an exact, case-sensitive match. Missing country gets the
  default signature (R26).
- id may be str or int. Ties in send_at are ordered by str(appointment_id), then text.
- Logging: one INFO line per planned reminder with appointment_id and channel only.
  The house rule asks for the contact in the log, but R12 forbids logging customer
  data, so the contact is omitted. This conflict is flagged.

Open items for the client:
- Email subject and body copy.
- Recipient field in the reminder schema for email reminders.
- SMS character set (GSM or UCS-2) and the effective length limit.
- Date format in texts.
- Whether send_at should be returned in UTC or Europe/Dublin.
- Logging: house rule (contact in log) versus R12 (no customer data in logs).

Tests: not executed in this session (no tool access).
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
EVENING_SEND = time(20, 0)
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED = ("id", "customer_name", "email", "status", "starts_at")


def _is_aware(value):
    return isinstance(value, datetime) and value.utcoffset() is not None


def _bad(index, field):
    return ValueError(f"appointment at index {index} has invalid field '{field}'")


def _parse(index, rec):
    if not isinstance(rec, dict):
        raise ValueError(f"appointment at index {index} is not a mapping")
    for key in REQUIRED:
        if rec.get(key) is None:
            raise ValueError(f"appointment at index {index} is missing field '{key}'")
    appt_id = rec["id"]
    if isinstance(appt_id, bool) or not isinstance(appt_id, (str, int)):
        raise _bad(index, "id")
    for key in ("customer_name", "email", "status"):
        if not isinstance(rec[key], str):
            raise _bad(index, key)
    if not _is_aware(rec["starts_at"]):
        raise _bad(index, "starts_at")
    phone = rec.get("phone")
    if phone is not None and not isinstance(phone, str):
        raise _bad(index, "phone")
    country = rec.get("country")
    if country is not None and not isinstance(country, str):
        raise _bad(index, "country")
    optout = rec.get("optout_sms_v2")
    if optout is None:
        optout = True
    if not isinstance(optout, bool):
        raise _bad(index, "optout_sms_v2")
    return {
        "id": appt_id,
        "name": rec["customer_name"].strip(),
        "email": rec["email"].strip(),
        "phone": (phone or "").strip(),
        "country": country,
        "status": rec["status"].strip().lower(),
        "starts_at": rec["starts_at"],
        "optout": optout,
    }


def _channel(appt):
    has_phone = bool(appt["phone"])
    has_email = bool(appt["email"])
    if appt["optout"]:
        return "email" if has_phone and has_email else None
    if has_phone:
        return "sms"
    return "email" if has_email else None


def _signature(country):
    return SIG_PL if country == "PL" else SIG_DEFAULT


def _when(starts_at):
    local = starts_at.astimezone(DUBLIN)
    return f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}", local.strftime("%H:%M")


def _sms_body(name, date, clock, sig):
    greet = f"Hi {name}. " if name else ""
    return f"{greet}Appointment: {date} at {clock} (Brennan Opticians)\n{sig}"


def _sms_text(name, date, clock, sig):
    text = _sms_body(name, date, clock, sig)
    if len(text) <= SMS_LIMIT:
        return text
    for keep in range(len(name) - 1, 0, -1):
        short = _sms_body(name[:keep].rstrip() + "...", date, clock, sig)
        if len(short) <= SMS_LIMIT:
            return short
    return _sms_body("", date, clock, sig)


def _email_text(name, date, clock, sig):
    greet = f"Hello {name},\n\n" if name else ""
    return f"{greet}Appointment: {date} at {clock} (Brennan Opticians)\n\n{sig}"


def _is_quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _allowed_at(send_utc, now_utc):
    local = send_utc.astimezone(DUBLIN)
    if not _is_quiet(local):
        return send_utc
    if local.time() >= QUIET_START:
        evening = local.date()
    else:
        evening = local.date() - timedelta(days=1)
    target = datetime.combine(evening, EVENING_SEND, tzinfo=DUBLIN).astimezone(UTC)
    if target >= now_utc:
        return target
    now_local = now_utc.astimezone(DUBLIN)
    if not _is_quiet(now_local):
        return now_utc
    day = now_local.date()
    if now_local.time() >= QUIET_START:
        day += timedelta(days=1)
    return datetime.combine(day, QUIET_END, tzinfo=DUBLIN).astimezone(UTC)


def plan_reminders(appointments, now):
    """Plan appointment reminders.

    Stateless: this function does not record what was sent. The caller must
    de-duplicate reminders across repeated runs (R19).

    Args:
        appointments: iterable of appointment dicts (see module notes).
        now: timezone-aware datetime. A naive datetime raises ValueError (R18).

    Returns:
        List of dicts with exactly the keys appointment_id, channel
        ("sms" or "email"), send_at (aware UTC datetime) and text, sorted by
        send_at ascending, ties ordered by appointment_id (R15, R24).

    Raises:
        ValueError for a naive or non-datetime now, or for a malformed record.
        Error messages never contain customer data.
    """
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for index, rec in enumerate(appointments):
        appt = _parse(index, rec)
        if appt["status"] == "cancelled":
            continue
        starts_utc = appt["starts_at"].astimezone(UTC)
        if starts_utc <= now_utc:
            continue
        channel = _channel(appt)
        if channel is None:
            continue
        date, clock = _when(appt["starts_at"])
        sig = _signature(appt["country"])
        if channel == "sms":
            text = _sms_text(appt["name"], date, clock, sig)
        else:
            text = _email_text(appt["name"], date, clock, sig)
        slots = [max(starts_utc - FIRST_OFFSET, now_utc)]
        second = starts_utc - SECOND_OFFSET
        if second >= now_utc:
            slots.append(second)
        for raw in slots:
            send_at = _allowed_at(raw, now_utc)
            planned.append({
                "appointment_id": appt["id"],
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            logger.info("planned reminder appointment_id=%s channel=%s",
                        appt["id"], channel)
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["text"]))
    return planned


# ===== test_brennan_reminders.py =====
import unittest
from datetime import datetime, timezone

from brennan_reminders import plan_reminders

UTC = timezone.utc
NOW = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)


def u(*args):
    return datetime(*args, tzinfo=UTC)


def make(**overrides):
    rec = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": "aoife.murphy@example.com",
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": u(2026, 10, 20, 13, 30),  # 14:30 Europe/Dublin
        "optout_sms_v2": False,
    }
    rec.update(overrides)
    return rec


def send_times(out):
    return [r["send_at"] for r in out]


class PlanRemindersTests(unittest.TestCase):

    def test_48h_and_2h_timing(self):
        out = plan_reminders([make()], NOW)
        self.assertEqual(send_times(out), [u(2026, 10, 18, 13, 30), u(2026, 10, 20, 11, 30)])
        self.assertEqual({r["channel"] for r in out}, {"sms"})
        self.assertEqual(set(out[0]), {"appointment_id", "channel", "send_at", "text"})
        for r in out:
            self.assertIn("20 Oct 2026 at 14:30", r["text"])
            self.assertTrue(r["text"].endswith("Chevonne Nee Divver"))

    def test_48h_passed_sends_at_now(self):
        now = u(2026, 10, 18, 15, 0)
        out = plan_reminders([make()], now)
        self.assertEqual(send_times(out), [now, u(2026, 10, 20, 11, 30)])

    def test_2h_passed_drops_second(self):
        now = u(2026, 10, 20, 12, 0)
        out = plan_reminders([make()], now)
        self.assertEqual(send_times(out), [now])

    def test_now_in_allowed_hours_sends_now(self):
        now = u(2026, 10, 13, 19, 30)
        out = plan_reminders([make(starts_at=u(2026, 10, 13, 21, 0))], now)
        self.assertEqual(send_times(out), [now])

    def test_quiet_hours_shift_to_previous_20_00(self):
        out = plan_reminders([make(starts_at=u(2026, 10, 16, 22, 30))], NOW)
        self.assertEqual(send_times(out), [u(2026, 10, 14, 19, 0), u(2026, 10, 16, 19, 0)])

    def test_early_morning_moves_to_previous_evening(self):
        out = plan_reminders([make(starts_at=u(2026, 10, 15, 4, 0))], NOW)
        self.assertEqual(send_times(out), [u(2026, 10, 12, 19, 0), u(2026, 10, 14, 19, 0)])

    def test_08_00_allowed_and_21_00_quiet(self):
        out = plan_reminders([make(starts_at=u(2026, 10, 15, 9, 0))], NOW)
        self.assertEqual(out[1]["send_at"], u(2026, 10, 15, 7, 0))  # 08:00 IST allowed
        out = plan_reminders([make(starts_at=u(2026, 10, 15, 22, 0))], NOW)
        self.assertEqual(out[1]["send_at"], u(2026, 10, 15, 19, 0))  # 21:00 IST quiet

    def test_quiet_conflict_sends_next_08_00(self):
        now = u(2026, 10, 13, 21, 0)  # 22:00 IST, quiet
        out = plan_reminders([make(starts_at=u(2026, 10, 14, 11, 0))], now)
        self.assertEqual(send_times(out), [u(2026, 10, 14, 7, 0), u(2026, 10, 14, 9, 0)])

    def test_dst_offsets_are_elapsed_time(self):
        out = plan_reminders([make(starts_at=u(2026, 10, 26, 10, 0))], NOW)
        self.assertEqual(send_times(out), [u(2026, 10, 24, 10, 0), u(2026, 10, 26, 8, 0)])
        self.assertIn("26 Oct 2026 at 10:00", out[0]["text"])

    def test_sms_length_keeps_time_and_signature(self):
        name = ("Maximilian Alexander Bartholomew Fitzgerald-Montgomery-Smythe-"
                "O'Connor-Vanderbilt-Hargreaves")
        out = plan_reminders([make(customer_name=name)], NOW)
        self.assertTrue(out)
        for r in out:
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("20 Oct 2026 at 14:30", r["text"])
            self.assertTrue(r["text"].endswith("Chevonne Nee Divver"))
        self.assertIn("...", out[0]["text"])

    def test_short_name_not_truncated(self):
        out = plan_reminders([make()], NOW)
        self.assertIn("Aoife Murphy", out[0]["text"])
        self.assertNotIn("...", out[0]["text"])

    def test_opt_out_uses_email(self):
        out = plan_reminders([make(optout_sms_v2=True)], NOW)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_missing_or_empty_phone_uses_email(self):
        for phone in (None, ""):
            out = plan_reminders([make(phone=phone)], NOW)
            self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_missing_optout_treated_as_opted_out(self):
        rec = make()
        del rec["optout_sms_v2"]
        out = plan_reminders([rec], NOW)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_missing_phone_and_opted_out_no_reminder(self):
        out = plan_reminders([make(phone="", optout_sms_v2=True)], NOW)
        self.assertEqual(out, [])

    def test_cancelled_excluded(self):
        out = plan_reminders([make(status="cancelled"), make(id="X", status=" Cancelled ")], NOW)
        self.assertEqual(out, [])

    def test_other_status_passes_through(self):
        out = plan_reminders([make(status="no_show")], NOW)
        self.assertEqual(len(out), 2)

    def test_pl_signature(self):
        out = plan_reminders([make(country="PL")], NOW)
        self.assertTrue(out[0]["text"].endswith("Grzegorz Szczepański"))

    def test_pl_match_is_case_sensitive(self):
        out = plan_reminders([make(country="pl")], NOW)
        self.assertTrue(out[0]["text"].endswith("Chevonne Nee Divver"))

    def test_missing_country_gets_default_signature(self):
        rec = make()
        del rec["country"]
        out = plan_reminders([rec], NOW)
        self.assertTrue(out[0]["text"].endswith("Chevonne Nee Divver"))

    def test_sorted_with_ties_by_id(self):
        appts = [
            make(id="B2", starts_at=u(2026, 10, 20, 13, 30)),
            make(id="A1", starts_at=u(2026, 10, 20, 13, 30)),
            make(id="C3", starts_at=u(2026, 10, 15, 15, 0)),
        ]
        out = plan_reminders(appts, NOW)
        keys = [(r["send_at"], r["appointment_id"]) for r in out]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(keys[0], (u(2026, 10, 13, 15, 0), "C3"))
        self.assertEqual(keys[1], (u(2026, 10, 15, 13, 0), "C3"))
        self.assertEqual(keys[2:4], [(u(2026, 10, 18, 13, 30), "A1"),
                                     (u(2026, 10, 18, 13, 30), "B2")])

    def test_past_appointment_no_reminders(self):
        out = plan_reminders([make(starts_at=u(2026, 10, 10, 9, 0))], NOW)
        self.assertEqual(out, [])

    def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([make()], datetime(2026, 10, 10, 10, 0))

    def test_naive_starts_at_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([make(starts_at=datetime(2026, 10, 20, 13, 30))], NOW)

    def test_email_never_in_logs(self):
        secret = "secret.person@example.com"
        rec = make(email=secret, phone=None)
        with self.assertLogs(level="INFO") as cm:
            out = plan_reminders([rec], NOW)
        self.assertTrue(out)
        logged = "\n".join(cm.output)
        self.assertNotIn(secret, logged)
        self.assertNotIn("secret", logged)
        for r in out:
            self.assertNotIn("@", r["text"])

    def test_error_messages_have_no_customer_data(self):
        rec = make(email="secret.person@example.com",
                   starts_at=datetime(2026, 10, 20, 13, 30))  # naive, malformed
        with self.assertRaises(ValueError) as cm:
            plan_reminders([rec], NOW)
        message = str(cm.exception)
        self.assertNotIn("secret", message)
        self.assertNotIn("Aoife", message)


if __name__ == "__main__":
    unittest.main()