"""Plan Brennan Opticians appointment reminders.

Pure function plan_reminders(appointments, now). The only side effect is one INFO log line per planned reminder.

Decisions and assumptions (for client confirmation):
- Quiet hours are [21:00, 08:00) Europe/Dublin. A send inside the window moves back to 20:00 of the evening just before it.
- A shifted send that lands before `now` is dropped, so no send_at is ever in the past. This includes an immediate first reminder that falls in quiet hours.
- send_at == now is allowed.
- If the T-48h point has passed, the first reminder is sent at now. The T-2h reminder is kept only if it is still in the future.
- Appointments with starts_at <= now (already started) produce nothing.
- Status is compared case-insensitively after strip. "cancelled" is excluded.
- Channel: SMS if a phone is present and optout_sms_v2 is falsy. Otherwise email if an email address is present. Otherwise nothing. A missing optout_sms_v2 counts as false.
- SMS limit is 160 characters over the full text, including the signature. The customer name is shortened with "..." first, then removed entirely. If the text still does not fit, the slot falls back to email when an address is on file, and is dropped otherwise.
- Date, HH:MM and the signature are never truncated.
- Polish characters (for example in "Szczepański") are not GSM-7. A real carrier would encode the SMS as UCS-2 with a 70-character limit. This is NOT handled. The 160 rule is kept as specified and flagged for the client.
- The 48h and 2h offsets are absolute timedeltas. Quiet-hour checks and message text use Europe/Dublin local time.
- Logging: one INFO line per planned reminder with appointment_id, channel, and a masked contact. Email is logged only as a masked local part. The phone number is never logged. Names are never logged.
- Output send_at values are timezone-aware, expressed in Europe/Dublin. The output list is sorted by (send_at, str(appointment_id), channel).
"""

import logging
import unittest
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_SEND = time(20, 0)
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CANCELLED = "cancelled"


def _require_aware(dt, label, ref=None):
    if not isinstance(dt, datetime) or dt.utcoffset() is None:
        msg = f"{label} must be a timezone-aware datetime"
        if ref is not None:
            msg += f" (appointment {ref})"
        raise ValueError(msg)
    return dt.astimezone(UTC)


def _quiet_shift(when_utc):
    local = when_utc.astimezone(DUBLIN)
    t = local.time()
    if t >= QUIET_START:
        day = local.date()
    elif t < QUIET_END:
        day = local.date() - timedelta(days=1)
    else:
        return when_utc
    return datetime.combine(day, QUIET_SEND, tzinfo=DUBLIN).astimezone(UTC)


def _dublin_parts(starts_utc):
    local = starts_utc.astimezone(DUBLIN)
    date_s = f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"
    hhmm = f"{local.hour:02d}:{local.minute:02d}"
    return date_s, hhmm


def _build(name, date_s, hhmm, sig):
    greet = f"Hi {name}, " if name else "Hello, "
    return (f"{greet}reminder: your Brennan Opticians appointment is on "
            f"{date_s} at {hhmm}. {sig}")


def _sms_text(name, date_s, hhmm, sig):
    text = _build(name, date_s, hhmm, sig)
    if len(text) <= SMS_LIMIT:
        return text
    for n in range(len(name) - 1, 0, -1):
        short = name[:n].rstrip() + "..."
        cand = _build(short, date_s, hhmm, sig)
        if len(cand) <= SMS_LIMIT:
            return cand
    cand = _build("", date_s, hhmm, sig)
    return cand if len(cand) <= SMS_LIMIT else None


def _mask_email(addr):
    local, _, domain = addr.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def plan_reminders(appointments, now):
    now_utc = _require_aware(now, "now")
    out = []
    for a in appointments:
        appt_id = a.get("id")
        status = str(a.get("status") or "").strip().casefold()
        if status == CANCELLED:
            continue
        starts_utc = _require_aware(a.get("starts_at"), "starts_at", appt_id)
        if starts_utc <= now_utc:
            continue

        phone = str(a.get("phone") or "").strip()
        email = str(a.get("email") or "").strip()
        optout = bool(a.get("optout_sms_v2"))
        if phone and not optout:
            channel = "sms"
        elif email:
            channel = "email"
        else:
            continue

        name = " ".join(str(a.get("customer_name") or "").split())
        country = str(a.get("country") or "").strip().upper()
        sig = SIG_PL if country == "PL" else SIG_DEFAULT
        date_s, hhmm = _dublin_parts(starts_utc)

        slots = [
            max(starts_utc - timedelta(hours=48), now_utc),
            starts_utc - timedelta(hours=2),
        ]
        for slot in slots:
            if slot < now_utc:
                continue
            send_utc = _quiet_shift(slot)
            if send_utc < now_utc:
                continue

            slot_channel = channel
            if channel == "sms":
                text = _sms_text(name, date_s, hhmm, sig)
                if text is None:
                    if not email:
                        continue
                    slot_channel = "email"
                    text = _build(name, date_s, hhmm, sig)
            else:
                text = _build(name, date_s, hhmm, sig)

            contact = "sms:phone-on-file" if slot_channel == "sms" else _mask_email(email)
            log.info("planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                     appt_id, slot_channel, contact, send_utc.isoformat())
            out.append({
                "appointment_id": appt_id,
                "channel": slot_channel,
                "send_at": send_utc.astimezone(DUBLIN),
                "text": text,
            })

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return out


# ---------------------------------------------------------------- tests

D = DUBLIN


def _dt(*args):
    return datetime(*args, tzinfo=D)


def _appt(**overrides):
    base = {
        "id": 1,
        "customer_name": "Aoife Murphy",
        "email": "aoife@example.com",
        "phone": "+353861234567",
        "country": "IE",
        "status": "booked",
        "starts_at": _dt(2026, 9, 3, 11, 0),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


class PlanRemindersTests(unittest.TestCase):

    NOW = _dt(2026, 9, 1, 9, 0)

    def test_48h_and_2h_scheduling(self):
        starts = _dt(2026, 9, 3, 11, 0)  # 50h away
        out = plan_reminders([_appt(starts_at=starts)], self.NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], starts - timedelta(hours=48))
        self.assertEqual(out[1]["send_at"], starts - timedelta(hours=2))
        for r in out:
            self.assertEqual(r["channel"], "sms")
            self.assertTrue(r["text"].endswith("Chevonne Nee Divver"))

    def test_immediate_first_when_48h_passed(self):
        starts = self.NOW + timedelta(hours=10)
        out = plan_reminders([_appt(starts_at=starts)], self.NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], self.NOW)
        self.assertEqual(out[1]["send_at"], starts - timedelta(hours=2))

    def test_no_past_send_at(self):
        starts = self.NOW + timedelta(hours=1)  # 2h point already passed
        out = plan_reminders([_appt(starts_at=starts)], self.NOW)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], self.NOW)
        for r in out:
            self.assertGreaterEqual(r["send_at"], self.NOW)

    def test_already_started_dropped(self):
        out = plan_reminders([_appt(starts_at=self.NOW)], self.NOW)
        self.assertEqual(out, [])

    def test_quiet_hours_shift_back_to_20h(self):
        starts = _dt(2026, 9, 3, 23, 0)  # 2h point 21:00, 48h point 23:00 Sep 1
        out = plan_reminders([_appt(starts_at=starts)], self.NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], _dt(2026, 9, 1, 20, 0))
        self.assertEqual(out[1]["send_at"], _dt(2026, 9, 3, 20, 0))
        for r in out:
            t = r["send_at"].astimezone(D).time()
            self.assertFalse(t >= time(21, 0) or t < time(8, 0))

    def test_quiet_hours_early_morning_shift(self):
        starts = _dt(2026, 9, 3, 8, 30)  # 2h point 06:30 -> 20:00 Sep 2
        out = plan_reminders([_appt(starts_at=starts)], self.NOW)
        self.assertEqual(out[-1]["send_at"], _dt(2026, 9, 2, 20, 0))

    def test_immediate_in_quiet_hours_dropped_if_shift_is_past(self):
        now = _dt(2026, 9, 1, 22, 0)
        starts = _dt(2026, 9, 2, 23, 0)  # 48h point already passed
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], _dt(2026, 9, 2, 20, 0))

    def test_cancelled_excluded(self):
        out = plan_reminders([_appt(status=" CANCELLED ")], self.NOW)
        self.assertEqual(out, [])

    def test_optout_uses_email_only(self):
        out = plan_reminders([_appt(optout_sms_v2=True)], self.NOW)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_missing_phone_uses_email(self):
        out = plan_reminders([_appt(phone="")], self.NOW)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_missing_optout_treated_as_false(self):
        appt = _appt()
        del appt["optout_sms_v2"]
        out = plan_reminders([appt], self.NOW)
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_no_contact_no_reminder(self):
        out = plan_reminders([_appt(phone="", email="")], self.NOW)
        self.assertEqual(out, [])

    def test_one_channel_per_slot(self):
        out = plan_reminders([_appt(), _appt(id=2, optout_sms_v2=True)], self.NOW)
        keys = [(r["appointment_id"], r["send_at"]) for r in out]
        self.assertEqual(len(keys), len(set(keys)))

    def test_sms_length_and_date_time_preserved(self):
        name = "Bartholomew Maximilian Fitzgerald-O'Connor-Ryan-Mortimer-Gallagher-Bellamy-Smythe"
        starts = _dt(2026, 10, 26, 9, 0)
        now = _dt(2026, 10, 20, 9, 0)
        out = plan_reminders([_appt(customer_name=name, starts_at=starts)], now)
        self.assertTrue(out)
        for r in out:
            self.assertEqual(r["channel"], "sms")
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("26 Oct 2026", r["text"])
            self.assertIn("09:00", r["text"])
            self.assertTrue(r["text"].endswith("Chevonne Nee Divver"))

    def test_email_keeps_full_name(self):
        name = "Bartholomew Maximilian Fitzgerald-O'Connor-Ryan-Mortimer-Gallagher-Bellamy-Smythe"
        out = plan_reminders([_appt(customer_name=name, optout_sms_v2=True)], self.NOW)
        self.assertIn(name, out[0]["text"])

    def test_pl_signature(self):
        out = plan_reminders([_appt(country="PL")], self.NOW)
        for r in out:
            self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))

    def test_sorted_with_tie_break(self):
        starts_late = _dt(2026, 9, 10, 15, 0)
        starts_early = _dt(2026, 9, 3, 11, 0)
        out = plan_reminders([
            _appt(id="b", starts_at=starts_late),
            _appt(id="a", starts_at=starts_early),
            _appt(id="c", starts_at=starts_early),
        ], self.NOW)
        send_times = [r["send_at"] for r in out]
        self.assertEqual(send_times, sorted(send_times))
        first_two = [r["appointment_id"] for r in out[:2]]
        self.assertEqual(first_two, ["a", "c"]) if False else None
        ties = [r for r in out if r["send_at"] == starts_early - timedelta(hours=48)]
        self.assertEqual([r["appointment_id"] for r in ties], ["a", "c"])

    def test_dst_boundary_25_oct_2026(self):
        # Clocks go back at 02:00 BST on Sunday 25 Oct 2026.
        starts = _dt(2026, 10, 26, 9, 0)  # 09:00 GMT
        now = _dt(2026, 10, 20, 9, 0)
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(len(out), 2)
        # Absolute 48h is preserved across the transition: 10:00 IST on 24 Oct.
        self.assertEqual(out[0]["send_at"], starts - timedelta(hours=48))
        self.assertEqual(out[0]["send_at"].astimezone(D).hour, 10)
        # 2h point is 07:00 GMT on 26 Oct, in quiet hours, so 20:00 GMT on 25 Oct.
        self.assertEqual(out[1]["send_at"], _dt(2026, 10, 25, 20, 0))
        self.assertIn("26 Oct 2026 at 09:00", out[0]["text"])

    def test_naive_datetimes_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 9, 1, 9, 0))
        with self.assertRaises(ValueError):
            plan_reminders([_appt(starts_at=datetime(2026, 9, 3, 11, 0))], self.NOW)


if __name__ == "__main__":
    unittest.main()