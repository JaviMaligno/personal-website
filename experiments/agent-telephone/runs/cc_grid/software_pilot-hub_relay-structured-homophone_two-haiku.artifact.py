"""Brennan Opticians appointment reminder planner.

plan_reminders() is a pure planning function. It returns reminder dicts and sends nothing.

PENDING defaults implemented (client has not confirmed):
- R3: optout_sms_v2 missing or None is treated as opted out (email channel).
- R8: opted-in customer with no phone number: that reminder is dropped and a WARNING is logged.
- R10: date format is "D Mon YYYY" (e.g. "14 Oct 2026"); time is HH:MM Europe/Dublin.
- R11: if the 20:00 target is before now, use 08:00 Europe/Dublin (the end of the quiet window) if it is still before starts_at and not before now; otherwise drop the reminder.
- R12: only status "cancelled" (case-insensitive, trimmed) is excluded. Status values handled: any string. None other than "cancelled" was specified, so all other values are planned normally.
- R18: if the 2-hour point has passed and starts_at is in the future, one reminder is returned at now with the second-reminder text. The quiet-hours rule still applies.

Gaps to report:
- R4 vs R8/R13: the email channel has no recipient field. No address is emitted, so downstream must resolve the recipient from appointment_id.
- House logging rule vs R13: SMS log lines show only the last 4 digits of the phone. Email log lines show "email on file" and no address. R13 takes precedence over the contact-logging rule.
- R9 wording: SMS is measured with Python len(), as specified. Non-ASCII signature characters may be sent as UCS-2 by carriers, which would reduce the real per-segment limit.

Tests are in the unittest block at the bottom of this module. They were not executed in this session because no execution tools were available.
"""

import logging
import re
import unittest
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders", "AppointmentError"]

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
SMS_MAX = 160
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED = ("id", "customer_name", "email", "phone", "country",
            "status", "starts_at", "optout_sms_v2")
LEAD_FIRST = timedelta(hours=48)
LEAD_SECOND = timedelta(hours=2)


class AppointmentError(ValueError):
    """Raised for malformed input. Messages name the appointment id only."""


def _validate(index, raw):
    if not isinstance(raw, dict):
        raise AppointmentError(f"appointment at index {index} is not a dict")
    ident_raw = raw.get("id")
    if isinstance(ident_raw, bool) or not isinstance(ident_raw, (str, int)) or ident_raw == "":
        ident_label = f"appointment at index {index}"
    else:
        ident_label = f"appointment {ident_raw!r}"
    for key in REQUIRED:
        if key not in raw:
            raise AppointmentError(f"{ident_label} is missing required key {key!r}")
    ident = ident_raw
    if isinstance(ident, bool) or not isinstance(ident, (str, int)) or ident == "":
        raise AppointmentError(f"appointment at index {index} has a malformed id")
    label = f"appointment {ident!r}"
    for key in ("customer_name", "email", "country", "status"):
        if not isinstance(raw[key], str):
            raise AppointmentError(f"{label} has malformed {key!r}")
    phone = raw["phone"]
    if phone is not None and not isinstance(phone, str):
        raise AppointmentError(f"{label} has malformed 'phone'")
    opt = raw["optout_sms_v2"]
    if opt is not None and not isinstance(opt, bool):
        raise AppointmentError(f"{label} has malformed 'optout_sms_v2'")
    s = raw["starts_at"]
    if not isinstance(s, datetime) or s.utcoffset() is None:
        raise AppointmentError(f"{label} has malformed 'starts_at' (must be timezone-aware)")
    return ident, label


def _at_dublin(d, hour):
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=DUBLIN).astimezone(UTC)


def _quiet_adjust(when, starts_utc, now_utc):
    """Return a UTC send time outside 21:00-08:00 Dublin, or None to drop."""
    local = when.astimezone(DUBLIN)
    h = local.hour
    if 8 <= h < 21:
        return when
    if h >= 21:
        target_day = local.date()
        end_day = local.date() + timedelta(days=1)
    else:
        target_day = local.date() - timedelta(days=1)
        end_day = local.date()
    target = _at_dublin(target_day, 20)
    if target >= now_utc:
        return target
    end = _at_dublin(end_day, 8)
    if now_utc <= end < starts_utc:
        return end
    return None


def _body(kind, name, date_s, time_s, sig):
    lead = "Reminder. " if kind == "second" else ""
    if name:
        core = f"Hi {name}, your appointment at Brennan Opticians is on {date_s} at {time_s}."
    else:
        core = f"Your appointment at Brennan Opticians is on {date_s} at {time_s}."
    return f"{lead}{core} {sig}"


def _plan_one(ident, label, raw, starts_utc, now_utc):
    if starts_utc <= now_utc:
        return []
    second_at = starts_utc - LEAD_SECOND
    first_at = starts_utc - LEAD_FIRST
    if second_at <= now_utc:
        slots = [("second", now_utc)]
    elif first_at <= now_utc:
        slots = [("first", now_utc), ("second", second_at)]
    else:
        slots = [("first", first_at), ("second", second_at)]

    optout = raw["optout_sms_v2"]
    phone = raw["phone"]
    has_phone = isinstance(phone, str) and phone.strip() != ""
    if optout is not False:
        channel = "email"
    elif has_phone:
        channel = "sms"
    else:
        log.warning("no phone number for appointment %r; no SMS planned", ident)
        return []

    country = raw["country"].strip().upper()
    sig = SIG_PL if country == "PL" else SIG_DEFAULT
    local = starts_utc.astimezone(DUBLIN)
    date_s = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    full = raw["customer_name"].strip()
    first = full.split()[0] if full else ""
    digits = re.sub(r"\D", "", phone) if has_phone else ""

    out = []
    for kind, when in slots:
        send = _quiet_adjust(when, starts_utc, now_utc)
        if send is None:
            log.debug("dropped reminder appointment=%r kind=%s: no valid quiet-hours slot", ident, kind)
            continue
        if not (now_utc <= send < starts_utc):
            continue
        if channel == "sms":
            text = None
            for name in (full, first, ""):
                cand = _body(kind, name, date_s, time_s, sig)
                if len(cand) <= SMS_MAX:
                    text = cand
                    break
            if text is None:
                raise AppointmentError(f"{label} SMS text cannot fit in {SMS_MAX} characters")
            contact = f"phone ending {digits[-4:]}"
        else:
            text = _body(kind, full, date_s, time_s, sig)
            contact = "email on file"
        log.info("planned reminder appointment=%r kind=%s channel=%s to=%s send_at=%s",
                 ident, kind, channel, contact, send.isoformat())
        out.append({"appointment_id": ident, "channel": channel,
                    "send_at": send, "text": text})
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise AppointmentError("now must be a timezone-aware datetime")
    if not isinstance(appointments, list):
        raise AppointmentError("appointments must be a list")
    now_utc = now.astimezone(UTC)
    seen = set()
    results = []
    for index, raw in enumerate(appointments):
        ident, label = _validate(index, raw)
        if ident in seen:
            raise AppointmentError(f"duplicate {label}")
        seen.add(ident)
        if raw["status"].strip().lower() == "cancelled":
            continue
        starts_utc = raw["starts_at"].astimezone(UTC)
        results.extend(_plan_one(ident, label, raw, starts_utc, now_utc))
    results.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return results


if __name__ == "__main__":
    def _appt(**kw):
        base = dict(id="a1", customer_name="Anna Kowalska", email="anna@example.com",
                    phone="+353861234567", country="IE", status="booked",
                    starts_at=datetime(2026, 10, 20, 10, 0, tzinfo=DUBLIN),
                    optout_sms_v2=False)
        base.update(kw)
        return base

    NOW = datetime(2026, 10, 10, 0, 0, tzinfo=UTC)

    class PlanTests(unittest.TestCase):

        def test_optout_v2_used_and_opt_out_ignored(self):
            a = _appt(optout_sms_v2=False)
            a["opt_out"] = True
            r = plan_reminders([a], NOW)
            self.assertEqual(len(r), 2)
            self.assertTrue(all(x["channel"] == "sms" for x in r))
            b = _appt(optout_sms_v2=True)
            b["opt_out"] = False
            r = plan_reminders([b], NOW)
            self.assertTrue(all(x["channel"] == "email" for x in r))

        def test_null_optout_treated_as_email(self):
            r = plan_reminders([_appt(optout_sms_v2=None)], NOW)
            self.assertTrue(all(x["channel"] == "email" for x in r))

        def test_timing_48h_and_2h(self):
            r = plan_reminders([_appt()], NOW)
            self.assertEqual([x["send_at"] for x in r],
                             [datetime(2026, 10, 18, 9, 0, tzinfo=UTC),
                              datetime(2026, 10, 20, 7, 0, tzinfo=UTC)])

        def test_immediate_send_when_48h_passed(self):
            now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
            r = plan_reminders([_appt()], now)
            self.assertEqual(r[0]["send_at"], now)
            self.assertEqual(r[1]["send_at"], datetime(2026, 10, 20, 7, 0, tzinfo=UTC))

        def test_two_hour_only_when_2h_passed(self):
            now = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
            r = plan_reminders([_appt()], now)
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0]["send_at"], now)
            self.assertTrue(r[0]["text"].startswith("Reminder."))

        def test_no_reminders_for_started_appointment(self):
            now = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
            self.assertEqual(plan_reminders([_appt()], now), [])

        def test_no_send_before_now_or_at_start(self):
            a = _appt()
            for hours in (0, 30, 47, 49, 60, 71):
                now = datetime(2026, 10, 20, 9, 0, tzinfo=UTC) - timedelta(hours=hours)
                for x in plan_reminders([a], now):
                    self.assertTrue(now <= x["send_at"] < a["starts_at"].astimezone(UTC))

        def test_sms_length_limit_keeps_date_time_and_signature(self):
            name = "Maximiliana Konstantinopoulou-Papadakis Vasquez-Ferreira"
            r = plan_reminders([_appt(customer_name=name)], NOW)
            sms = [x for x in r if x["channel"] == "sms"]
            self.assertTrue(sms)
            for x in sms:
                self.assertLessEqual(len(x["text"]), SMS_MAX)
                self.assertTrue(x["text"].endswith(SIG_DEFAULT))
                self.assertIn("20 Oct 2026", x["text"])
                self.assertIn("10:00", x["text"])

        def test_quiet_hours_shift_to_previous_20h(self):
            a = _appt(starts_at=datetime(2026, 10, 15, 9, 0, tzinfo=DUBLIN))
            now = datetime(2026, 10, 13, 0, 0, tzinfo=UTC)
            r = plan_reminders([a], now)
            self.assertEqual(r[0]["send_at"], datetime(2026, 10, 13, 8, 0, tzinfo=UTC))
            self.assertEqual(r[1]["send_at"], datetime(2026, 10, 14, 19, 0, tzinfo=UTC))

        def test_quiet_hours_fallback_to_08h_when_20h_passed(self):
            a = _appt(starts_at=datetime(2026, 10, 15, 9, 0, tzinfo=DUBLIN))
            now = datetime(2026, 10, 14, 19, 30, tzinfo=UTC)
            r = plan_reminders([a], now)
            self.assertEqual([x["send_at"] for x in r],
                             [datetime(2026, 10, 14, 19, 30, tzinfo=UTC),
                              datetime(2026, 10, 15, 7, 0, tzinfo=UTC)])

        def test_quiet_hours_drop_when_08h_not_before_start(self):
            a = _appt(starts_at=datetime(2026, 10, 15, 8, 0, tzinfo=DUBLIN))
            now = datetime(2026, 10, 14, 19, 30, tzinfo=UTC)
            r = plan_reminders([a], now)
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0]["send_at"], now)

        def test_cancelled_excluded(self):
            self.assertEqual(plan_reminders([_appt(status="  CANCELLED ")], NOW), [])

        def test_pl_signature(self):
            r = plan_reminders([_appt(country=" pl ", customer_name="Jan")], NOW)
            self.assertTrue(r)
            for x in r:
                self.assertTrue(x["text"].endswith(SIG_PL))

        def test_sorted_with_tiebreak(self):
            a = _appt(id="b")
            b = _appt(id="a")
            r = plan_reminders([a, b], NOW)
            keys = [(x["send_at"], x["appointment_id"], x["channel"]) for x in r]
            self.assertEqual(keys, sorted(keys))
            self.assertEqual(r[0]["appointment_id"], "a")

        def test_dst_fall_back_elapsed_48h(self):
            a = _appt(starts_at=datetime(2026, 10, 26, 10, 0, tzinfo=DUBLIN))
            r = plan_reminders([a], NOW)
            self.assertEqual(r[0]["send_at"], datetime(2026, 10, 24, 10, 0, tzinfo=UTC))
            self.assertIn("26 Oct 2026 at 10:00", r[1]["text"])

        def test_dst_spring_forward_elapsed_48h(self):
            a = _appt(starts_at=datetime(2027, 3, 29, 10, 0, tzinfo=DUBLIN))
            now = datetime(2027, 3, 1, 0, 0, tzinfo=UTC)
            r = plan_reminders([a], now)
            self.assertEqual(r[0]["send_at"], datetime(2027, 3, 27, 9, 0, tzinfo=UTC))
            self.assertIn("29 Mar 2027 at 10:00", r[1]["text"])

        def test_no_email_in_logs_or_errors(self):
            with self.assertLogs(level="INFO") as cm:
                plan_reminders([_appt()], NOW)
            joined = "\n".join(cm.output)
            self.assertNotIn("anna@example.com", joined)
            self.assertNotIn("@", joined)
            with self.assertRaises(AppointmentError) as ctx:
                plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 10, 0))], NOW)
            self.assertNotIn("@", str(ctx.exception))
            self.assertIn("a1", str(ctx.exception))

        def test_missing_key_raises(self):
            a = _appt()
            del a["phone"]
            with self.assertRaises(AppointmentError) as ctx:
                plan_reminders([a], NOW)
            self.assertIn("phone", str(ctx.exception))
            self.assertNotIn("@", str(ctx.exception))

        def test_duplicate_ids_raise(self):
            with self.assertRaises(AppointmentError):
                plan_reminders([_appt(), _appt()], NOW)

        def test_opted_in_without_phone_dropped(self):
            self.assertEqual(plan_reminders([_appt(phone=None)], NOW), [])

        def test_output_keys_exact(self):
            for x in plan_reminders([_appt()], NOW):
                self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})

    unittest.main()
</br>