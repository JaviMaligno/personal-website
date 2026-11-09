"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now) -> list of dicts with keys
appointment_id, channel ("sms" or "email"), send_at (timezone-aware UTC datetime)
and text. The list is sorted ascending by send_at.

Chosen defaults (for client confirmation):
1. Quiet hours are 21:00-07:59 Europe/Dublin. A send time in that window moves back
   to 20:00 Dublin, the most recent 20:00 before the window. If that is before now, it
   moves forward to 08:00 Dublin, provided that is not before the appointment start.
   If neither works, the reminder is dropped and a WARNING is logged.
2. Immediate sends (48h point already passed) follow the same quiet-hours rule.
3. If the 2h point is also already passed, only one immediate reminder is sent.
   Two reminders that collapse to the same send_at are deduplicated.
4. Appointments with starts_at <= now get no reminders.
5. A naive now or starts_at raises ValueError. The message names only the appointment id.
6. Only optout_sms_v2 is read. A missing or null value is treated as opted out
   (conservative: email instead of SMS). Strings such as "true", "1", "yes" and "y" count as true.
7. Channel: SMS if phone is non-blank and not opted out. Otherwise email if email is non-blank.
   Otherwise no reminder, with a WARNING that carries only the appointment id.
8. Status is matched case-insensitively after stripping. Only "cancelled" is excluded.
9. SMS template: "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {time}. {sig}".
   Date is "30 Oct 2026" with fixed English abbreviations. Time is HH:MM in Dublin local time.
   Length is Python len(), capped at 160. Non-GSM-7 characters such as "á" in the signature may make
   some carriers switch to UCS-2 (70-character segments). This is not handled.
10. Name shortening, first candidate that fits: full name, first name, first name plus initial
    (for example "J."), then no name. Date, time and signature are never removed.
11. Email text has no length limit: "Dear {name}," greeting, body with date and time, then the signature.
12. Signature is "Siobhán Ní Dhuibhir", or "Grzegorz Szczepański" when country is "PL" (case-insensitive).
13. Logging: one INFO line per planned reminder with appointment_id, channel and contact.
    SMS contact is the phone masked to its last 4 digits. Email contact is "email on file (redacted)".
    This deliberately departs from logging the full contact because of the DPC audit finding.
14. The legacy folder is not used.
"""

import logging
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _require_aware(value, what, appt_id=None):
    if isinstance(value, datetime) and value.utcoffset() is not None:
        return
    where = what if appt_id is None else f"{what} of appointment {appt_id}"
    raise ValueError(f"{where} must be a timezone-aware datetime")


def _opted_out(appt):
    if appt.get("optout_sms_v2") is None:
        return True  # conservative: unknown consent means no SMS
    v = appt["optout_sms_v2"]
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "y"}
    return bool(v)


def _quiet_adjust(t, now, starts_at):
    """Return a quiet-hours-compliant time >= now and < starts_at, or None."""
    local = t.astimezone(DUBLIN)
    h = local.hour
    if 8 <= h < 21:
        return t
    day = local.date()
    if h >= 21:
        back_day = day
        fwd_day = day + timedelta(days=1)
    else:
        back_day = day - timedelta(days=1)
        fwd_day = day
    back = datetime(back_day.year, back_day.month, back_day.day, 20, 0, tzinfo=DUBLIN)
    forward = datetime(fwd_day.year, fwd_day.month, fwd_day.day, 8, 0, tzinfo=DUBLIN)
    if back >= now:
        return back
    if now <= forward < starts_at:
        return forward
    return None


def _name_candidates(name):
    if not name:
        return [""]
    first = name.split()[0]
    return [name, first, first[0] + ".", ""]


def _sms_text(name, date_s, time_s, sig):
    for cand in _name_candidates(name):
        head = f"Hi {cand}, reminder" if cand else "Reminder"
        text = f"{head} of your Brennan Opticians appointment on {date_s} at {time_s}. {sig}"
        if len(text) <= SMS_MAX:
            return text
    raise ValueError("SMS template does not fit in 160 characters")


def _email_text(name, date_s, time_s, sig):
    greet = f"Dear {name}," if name else "Dear customer,"
    return (f"{greet}\n\n"
            f"This is a reminder of your appointment at Brennan Opticians on "
            f"{date_s} at {time_s} (Irish time).\n\n"
            f"Kind regards,\n{sig}")


def _mask_phone(phone):
    return "****" if len(phone) <= 4 else "*" * (len(phone) - 4) + phone[-4:]


def _plan_one(appt, now):
    appt_id = appt.get("id")
    if str(appt.get("status") or "").strip().lower() == "cancelled":
        return []

    starts_at = appt.get("starts_at")
    _require_aware(starts_at, "starts_at", appt_id)
    if starts_at <= now:
        return []

    t48 = starts_at - timedelta(hours=48)
    t2 = starts_at - timedelta(hours=2)
    if t2 <= now:
        wanted = [now]
    elif t48 < now:
        wanted = [now, t2]
    else:
        wanted = [t48, t2]

    phone = "" if appt.get("phone") is None else str(appt["phone"]).strip()
    email = "" if appt.get("email") is None else str(appt["email"]).strip()
    if phone and not _opted_out(appt):
        channel = "sms"
    elif email:
        channel = "email"
    else:
        log.warning("no reminder for appointment_id=%s: no usable contact", appt_id)
        return []

    local = starts_at.astimezone(DUBLIN)
    date_s = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    country = str(appt.get("country") or "").strip().upper()
    sig = SIG_PL if country == "PL" else SIG_DEFAULT
    name = str(appt.get("customer_name") or "").strip()

    if channel == "sms":
        text = _sms_text(name, date_s, time_s, sig)
        contact = _mask_phone(phone)
    else:
        text = _email_text(name, date_s, time_s, sig)
        contact = "email on file (redacted)"

    out, seen = [], set()
    for when in wanted:
        send_at = _quiet_adjust(when, now, starts_at)
        if send_at is None:
            log.warning("reminder dropped for appointment_id=%s: no quiet-hours-compliant time",
                        appt_id)
            continue
        send_at = send_at.astimezone(UTC)
        if send_at in seen:
            continue
        seen.add(send_at)
        log.info("reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                 appt_id, channel, contact, send_at.isoformat())
        out.append({"appointment_id": appt_id, "channel": channel,
                    "send_at": send_at, "text": text})
    return out


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    result = []
    for appt in appointments:
        result.extend(_plan_one(appt, now))
    result.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    return result


# ---------------------------------------------------------------- tests

def _utc(*args):
    return datetime(*args, tzinfo=UTC)


NOW = _utc(2026, 10, 20, 9, 0)
FAR = _utc(2026, 11, 1, 0, 0)


def _appt(**overrides):
    base = {
        "id": "A",
        "customer_name": "Ann Murphy",
        "email": "ann@example.com",
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": _utc(2026, 10, 30, 14, 0),
        "optout_sms_v2": False,
        "opt_out": True,  # legacy field, must be ignored
    }
    base.update(overrides)
    return base


class TestPlanReminders(unittest.TestCase):

    def test_a1_normal_sms_two_reminders(self):
        r = plan_reminders([_appt()], NOW)
        self.assertEqual([x["send_at"] for x in r],
                         [_utc(2026, 10, 28, 14, 0), _utc(2026, 10, 30, 12, 0)])
        self.assertTrue(all(x["channel"] == "sms" for x in r))
        self.assertIn("30 Oct 2026", r[0]["text"])
        self.assertIn("14:00", r[0]["text"])

    def test_a2_48h_passed_first_immediate(self):
        r = plan_reminders([_appt(starts_at=_utc(2026, 10, 21, 14, 0))], NOW)
        self.assertEqual([x["send_at"] for x in r], [NOW, _utc(2026, 10, 21, 12, 0)])
        # 14:00 UTC on 21 Oct is 15:00 Dublin (IST)
        self.assertIn("15:00", r[1]["text"])
        self.assertIn("21 Oct 2026", r[1]["text"])

    def test_a3_both_passed_immediate_only(self):
        r = plan_reminders([_appt(starts_at=_utc(2026, 10, 20, 10, 30))], NOW)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], NOW)

    def test_a4_cancelled_none(self):
        self.assertEqual(plan_reminders([_appt(status="cancelled")], NOW), [])

    def test_a4_cancelled_excluded_others_kept(self):
        r = plan_reminders([_appt(id="X", status="cancelled"), _appt(id="Y")], NOW)
        self.assertTrue(r)
        self.assertTrue(all(x["appointment_id"] == "Y" for x in r))

    def test_a5_2h_point_quiet_moves_to_prior_2000(self):
        r = plan_reminders([_appt(starts_at=_utc(2026, 10, 30, 23, 0))], NOW)
        self.assertEqual([x["send_at"] for x in r],
                         [_utc(2026, 10, 28, 20, 0), _utc(2026, 10, 30, 20, 0)])

    def test_a6_quiet_boundaries(self):
        self.assertEqual(_quiet_adjust(_utc(2026, 10, 30, 20, 59), NOW, FAR),
                         _utc(2026, 10, 30, 20, 59))
        self.assertEqual(_quiet_adjust(_utc(2026, 10, 30, 21, 0), NOW, FAR),
                         _utc(2026, 10, 30, 20, 0))
        self.assertEqual(_quiet_adjust(_utc(2026, 10, 30, 7, 59), NOW, FAR),
                         _utc(2026, 10, 29, 20, 0))
        self.assertEqual(_quiet_adjust(_utc(2026, 10, 30, 8, 0), NOW, FAR),
                         _utc(2026, 10, 30, 8, 0))

    def test_a7_dst_change_helper(self):
        # 2026-10-25 00:30 UTC is 01:30 IST; 02:30 UTC is 02:30 GMT. Both are quiet.
        expected = _utc(2026, 10, 24, 19, 0)  # 20:00 IST on 24 Oct
        self.assertEqual(_quiet_adjust(_utc(2026, 10, 25, 0, 30), NOW, FAR), expected)
        self.assertEqual(_quiet_adjust(_utc(2026, 10, 25, 2, 30), NOW, FAR), expected)

    def test_a7_dst_change_plan(self):
        r = plan_reminders([_appt(starts_at=_utc(2026, 10, 26, 23, 30))], NOW)
        self.assertEqual([x["send_at"] for x in r],
                         [_utc(2026, 10, 24, 19, 0), _utc(2026, 10, 26, 20, 0)])

    def test_a8_opt_out_uses_optout_sms_v2_only(self):
        r = plan_reminders([_appt(opt_out=True, optout_sms_v2=False)], NOW)
        self.assertTrue(all(x["channel"] == "sms" for x in r))
        r = plan_reminders([_appt(opt_out=False, optout_sms_v2=True)], NOW)
        self.assertTrue(all(x["channel"] == "email" for x in r))

    def test_a8_missing_optout_field_treated_as_opted_out(self):
        appt = _appt()
        del appt["optout_sms_v2"]
        r = plan_reminders([appt], NOW)
        self.assertTrue(all(x["channel"] == "email" for x in r))

    def test_a9_channel_fallback(self):
        r = plan_reminders([_appt(phone=None)], NOW)
        self.assertTrue(r and all(x["channel"] == "email" for x in r))
        r = plan_reminders([_appt(phone="", optout_sms_v2=False)], NOW)
        self.assertTrue(r and all(x["channel"] == "email" for x in r))
        r = plan_reminders([_appt(optout_sms_v2=True, email=None)], NOW)
        self.assertEqual(r, [])
        r = plan_reminders([_appt(phone="+353871234567", optout_sms_v2=True)], NOW)
        self.assertTrue(all(x["channel"] == "email" for x in r))

    def test_a10_sms_length_and_name_shortened(self):
        long_name = ("Maximilian Alexander Fitzgerald-Montgomery-O'Brien Ní Ríordáin-Wolfe "
                     "Junior the Third of Dublin Southside")
        r = plan_reminders([_appt(customer_name=long_name)], NOW)
        for x in r:
            self.assertLessEqual(len(x["text"]), SMS_MAX)
            self.assertIn("30 Oct 2026", x["text"])
            self.assertIn("14:00", x["text"])
            self.assertTrue(x["text"].endswith(SIG_DEFAULT))
            self.assertIn("Maximilian", x["text"])
            self.assertNotIn(long_name, x["text"])

    def test_a10_huge_single_word_name(self):
        r = plan_reminders([_appt(customer_name="X" * 300)], NOW)
        for x in r:
            self.assertLessEqual(len(x["text"]), SMS_MAX)
            self.assertIn("X.,", x["text"])
            self.assertIn("14:00", x["text"])

    def test_a11_pl_signature(self):
        r = plan_reminders([_appt(country="PL"), _appt(id="B", country="pl", phone=None)], NOW)
        self.assertTrue(r)
        for x in r:
            self.assertTrue(x["text"].endswith(SIG_PL))

    def test_a12_sorted(self):
        appts = [_appt(id="1"), _appt(id="2", starts_at=_utc(2026, 11, 5, 10, 0)),
                 _appt(id="3", starts_at=_utc(2026, 10, 25, 15, 0))]
        r = plan_reminders(appts, NOW)
        times = [x["send_at"] for x in r]
        self.assertEqual(times, sorted(times))

    def test_a13_never_past_and_quiet_immediate(self):
        now = _utc(2026, 10, 29, 21, 30)  # quiet hours
        r = plan_reminders([_appt(starts_at=_utc(2026, 10, 30, 9, 0))], now)
        self.assertEqual([x["send_at"] for x in r], [_utc(2026, 10, 30, 8, 0)])
        for x in r:
            self.assertGreaterEqual(x["send_at"], now)

    def test_a14_no_email_in_logs_or_exceptions(self):
        with self.assertLogs(log, level="INFO") as cm:
            plan_reminders([_appt(), _appt(id="E", phone=None)], NOW)
        output = "\n".join(cm.output)
        self.assertNotIn("ann@example.com", output)
        self.assertNotIn("+353871234567", output)
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([_appt(starts_at=datetime(2026, 10, 30, 14, 0))], NOW)
        self.assertNotIn("ann@example.com", str(ctx.exception))

    def test_a15_empty_list(self):
        self.assertEqual(plan_reminders([], NOW), [])

    def test_a16_naive_now_raises_clearly(self):
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([_appt()], datetime(2026, 10, 20, 9, 0))
        self.assertIn("timezone-aware", str(ctx.exception))
        self.assertNotIn("ann@example.com", str(ctx.exception))

    def test_email_text_has_signature_and_no_address(self):
        r = plan_reminders([_appt(phone=None)], NOW)
        self.assertTrue(r)
        for x in r:
            self.assertTrue(x["text"].endswith(SIG_DEFAULT))
            self.assertNotIn("ann@example.com", x["text"])


if __name__ == "__main__":
    unittest.main()