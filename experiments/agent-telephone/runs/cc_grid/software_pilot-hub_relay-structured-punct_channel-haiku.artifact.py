"""Appointment reminder planning for Brennan Opticians (v1, SMS only).

plan_reminders() is pure: it returns planned reminders and never sends anything.
It is stateless, so repeated calls with the same input return the same reminders.

Decisions and flags for the client and support:
- Opt-out (Q1): only optout_sms_v2 is read, and only an explicit False permits SMS.
  None, a missing key, or any other value means opted out. Email is never used.
- R18 encoding: length is len() of the text as written. Messages containing
  a-acute, i-acute or n-acute (as in the signatures) are UCS-2 and really hold
  70 characters per segment. Behaviour is deliberately unchanged; flagged only.
- R20 departs from the literal R9 wording when 20:00 has already passed. The send
  time is then now, or 08:00 the next morning if now is inside quiet hours.
- R5/R21: when the 48-hour point has passed, exactly one reminder is produced at
  now, using the 2-hour text. The spec gives a single template (R17), so both
  reminder kinds share one text until the client says otherwise.
- R8 "initial" is the first letter of the first name followed by a full stop.
- Logging identifies the recipient by appointment_id only. Phone numbers and email
  addresses are never logged or placed in exception messages.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders", "ReminderError"]

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX = 160
H48 = timedelta(hours=48)
H2 = timedelta(hours=2)
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED = ("id", "customer_name", "status", "starts_at")


class ReminderError(Exception):
    """Raised when an appointment's fixed SMS parts cannot fit in SMS_MAX characters."""


def _is_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _send_time(t, now):
    """Return the send time for candidate t (aware, UTC), honouring R9, R20 and R6."""
    if t < now:
        t = now
    local = t.astimezone(DUBLIN)
    if not _is_quiet(local):
        return t
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    evening = datetime.combine(day, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)
    if evening >= now:
        return evening
    now_local = now.astimezone(DUBLIN)
    if not _is_quiet(now_local):
        return now
    day = now_local.date() + timedelta(days=1) if now_local.hour >= 21 else now_local.date()
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)


def _render(name, local, sig):
    date_s = f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"
    return (f"Brennan Opticians: {name}, your appointment is on {date_s} "
            f"at {local.hour:02d}:{local.minute:02d}. {sig}")


def _sms_text(aid, name, local, sig):
    first = name.split()[0] if name else ""
    options = [name, first, (first[:1] + ".") if first else "", ""]
    for candidate in options:
        text = _render(candidate, local, sig)
        if len(text) <= SMS_MAX:
            return text
    raise ReminderError(f"appointment {aid}: fixed SMS parts exceed {SMS_MAX} characters")


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    out = []
    for a in appointments:
        if not isinstance(a, dict):
            log.warning("skipping entry: not a mapping")
            continue
        aid = a.get("id")
        name = a.get("customer_name")
        missing = [k for k in REQUIRED if a.get(k) in (None, "")]
        if "customer_name" not in missing and not (isinstance(name, str) and name.split()):
            missing.append("customer_name")
        starts = a.get("starts_at")
        if starts is not None and not isinstance(starts, datetime):
            if "starts_at" not in missing:
                missing.append("starts_at")
        if missing:
            log.warning("skipping appointment id=%s: missing or invalid fields: %s",
                        aid, ", ".join(missing))
            continue
        if starts.utcoffset() is None:
            raise ValueError(f"appointment {aid}: starts_at must be timezone-aware")
        if a.get("status") == "cancelled":
            continue
        s = starts.astimezone(UTC)
        if s < now:
            continue
        phone = a.get("phone")
        if not isinstance(phone, str) or not phone.strip():
            continue
        if a.get("optout_sms_v2") is not False:
            continue
        if s - H48 < now:
            candidates = [now]
        else:
            candidates = [s - H48, s - H2]
        send_times = sorted({_send_time(t, now) for t in candidates})
        if not send_times:
            continue
        sig = SIG_PL if a.get("country") == "PL" else SIG_DEFAULT
        text = _sms_text(aid, " ".join(name.split()), starts.astimezone(DUBLIN), sig)
        for st in send_times:
            log.info("planned reminder appointment_id=%s channel=sms "
                     "recipient=customer(phone redacted) send_at=%s", aid, st.isoformat())
            out.append({"appointment_id": aid, "channel": "sms",
                        "send_at": st, "text": text})
    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return out


if __name__ == "__main__":
    import unittest

    def _utc(*args):
        return datetime(*args, tzinfo=UTC)

    def _appt(starts, **overrides):
        base = {
            "id": "A1",
            "customer_name": "Aoife Murphy",
            "email": "aoife.murphy@example.invalid",
            "phone": "+353871234567",
            "country": "IE",
            "status": "booked",
            "starts_at": starts,
            "optout_sms_v2": False,
        }
        base.update(overrides)
        return base

    NOW = _utc(2026, 10, 13, 9, 0)
    STARTS = _utc(2026, 10, 15, 14, 0)
    SIG_IE_TEXT = "Brennan Opticians: Aoife Murphy, your appointment is on 15 Oct 2026 at 15:00. Siobhán Ní Dhuibhir"

    class RemindersTests(unittest.TestCase):

        def sends(self, appts, now=NOW):
            return [r["send_at"] for r in plan_reminders(appts, now)]

        def test_r4_offsets_are_absolute_elapsed_time(self):
            self.assertEqual(self.sends([_appt(STARTS)]),
                             [_utc(2026, 10, 13, 14, 0), _utc(2026, 10, 15, 12, 0)])

        def test_r3_text_uses_dublin_local_time_and_template(self):
            out = plan_reminders([_appt(STARTS)], NOW)
            self.assertEqual(out[0]["text"], SIG_IE_TEXT)

        def test_r5_48h_passed_sends_single_reminder_at_now(self):
            now = _utc(2026, 10, 14, 9, 0)
            out = plan_reminders([_appt(STARTS)], now)
            self.assertEqual([r["send_at"] for r in out], [now])
            self.assertEqual(out[0]["text"], SIG_IE_TEXT)

        def test_r21_both_points_passed_future_start(self):
            now = _utc(2026, 10, 15, 13, 0)
            self.assertEqual(self.sends([_appt(STARTS)], now), [now])

        def test_r21_past_start_produces_nothing(self):
            self.assertEqual(self.sends([_appt(STARTS)], _utc(2026, 10, 15, 15, 0)), [])

        def test_r6_and_r9_invariants_hold_across_scenarios(self):
            scenarios = [
                (NOW, STARTS),
                (_utc(2026, 10, 12, 12, 0), _utc(2026, 10, 14, 23, 0)),
                (_utc(2026, 10, 14, 21, 30), _utc(2026, 10, 17, 0, 0)),
                (_utc(2026, 10, 14, 19, 30), _utc(2026, 10, 16, 21, 0)),
                (_utc(2026, 10, 15, 13, 0), STARTS),
                (_utc(2026, 10, 20, 12, 0), _utc(2026, 10, 26, 10, 0)),
            ]
            for now, starts in scenarios:
                with self.subTest(now=now, starts=starts):
                    for r in plan_reminders([_appt(starts)], now):
                        self.assertGreaterEqual(r["send_at"], now)
                        local = r["send_at"].astimezone(DUBLIN)
                        self.assertFalse(local.hour >= 21 or local.hour < 8)

        def test_r7_sms_only_when_phone_present_and_opted_in(self):
            no_key = _appt(STARTS)
            del no_key["optout_sms_v2"]
            cases = {
                "no phone": _appt(STARTS, phone=None),
                "empty phone": _appt(STARTS, phone=""),
                "blank phone": _appt(STARTS, phone="   "),
                "opted out": _appt(STARTS, optout_sms_v2=True),
                "opt-out null": _appt(STARTS, optout_sms_v2=None),
                "opt-out missing": no_key,
            }
            for label, a in cases.items():
                with self.subTest(label):
                    self.assertEqual(plan_reminders([a], NOW), [])

        def test_r2_old_opt_out_field_is_ignored(self):
            out = plan_reminders([_appt(STARTS, opt_out=True)], NOW)
            self.assertEqual(len(out), 2)
            self.assertTrue(all(r["channel"] == "sms" for r in out))

        def test_r8_name_shortened_to_first_name(self):
            name = "Aoife " + "O" * 80
            out = plan_reminders([_appt(STARTS, customer_name=name)], NOW)
            self.assertEqual(out[0]["text"],
                             "Brennan Opticians: Aoife, your appointment is on 15 Oct 2026 "
                             "at 15:00. Siobhán Ní Dhuibhir")

        def test_r8_name_shortened_to_initial(self):
            name = "A" * 80 + " Murphy"
            out = plan_reminders([_appt(STARTS, customer_name=name)], NOW)
            self.assertEqual(out[0]["text"],
                             "Brennan Opticians: A., your appointment is on 15 Oct 2026 "
                             "at 15:00. Siobhán Ní Dhuibhir")

        def test_r8_fixed_parts_too_long_raises(self):
            local = datetime(2026, 10, 15, 15, 0, tzinfo=DUBLIN)
            with self.assertRaises(ReminderError):
                _sms_text("A1", "Aoife", local, "S" * 200)

        def test_r8_all_texts_within_limit(self):
            name = "B" * 200
            for r in plan_reminders([_appt(STARTS, customer_name=name)], NOW):
                self.assertLessEqual(len(r["text"]), SMS_MAX)

        def test_r9_quiet_hours_move_to_previous_evening(self):
            now = _utc(2026, 10, 12, 12, 0)
            starts = _utc(2026, 10, 14, 23, 0)  # local 00:00 on 15 Oct
            self.assertEqual(self.sends([_appt(starts)], now),
                             [_utc(2026, 10, 12, 19, 0), _utc(2026, 10, 14, 19, 0)])

        def test_r20_quiet_now_uses_next_morning_0800(self):
            now = _utc(2026, 10, 14, 21, 30)
            starts = _utc(2026, 10, 17, 0, 0)
            self.assertEqual(self.sends([_appt(starts)], now),
                             [_utc(2026, 10, 15, 7, 0), _utc(2026, 10, 16, 19, 0)])

        def test_r20_passed_evening_outside_quiet_uses_now(self):
            now = _utc(2026, 10, 14, 19, 30)
            starts = _utc(2026, 10, 16, 21, 0)
            self.assertEqual(self.sends([_appt(starts)], now),
                             [now, _utc(2026, 10, 16, 19, 0)])

        def test_r10_cancelled_excluded(self):
            self.assertEqual(plan_reminders([_appt(STARTS, status="cancelled")], NOW), [])

        def test_r12_signatures(self):
            ie = plan_reminders([_appt(STARTS, country="IE")], NOW)[0]["text"]
            pl = plan_reminders([_appt(STARTS, country="PL")], NOW)[0]["text"]
            self.assertTrue(ie.endswith("Siobhán Ní Dhuibhir"))
            self.assertTrue(pl.endswith("Grzegorz Szczepański"))
            self.assertNotIn("Siobhán", pl)

        def test_r14_dst_absolute_offsets_across_clock_change(self):
            now = _utc(2026, 10, 20, 12, 0)
            starts = _utc(2026, 10, 26, 10, 0)  # clocks go back on 25 Oct
            out = plan_reminders([_appt(starts)], now)
            self.assertEqual([r["send_at"] for r in out],
                             [_utc(2026, 10, 24, 10, 0), _utc(2026, 10, 26, 8, 0)])
            self.assertIn("26 Oct 2026 at 10:00", out[0]["text"])

        def test_r15_sorted_by_send_at_then_id(self):
            appts = [
                _appt(STARTS, id="B"),
                _appt(STARTS, id="A"),
                _appt(_utc(2026, 10, 14, 14, 0), id="C"),
            ]
            out = plan_reminders(appts, NOW)
            self.assertEqual(
                [(r["send_at"], r["appointment_id"]) for r in out],
                [(_utc(2026, 10, 13, 9, 0), "C"),
                 (_utc(2026, 10, 13, 14, 0), "A"),
                 (_utc(2026, 10, 13, 14, 0), "B"),
                 (_utc(2026, 10, 15, 12, 0), "A"),
                 (_utc(2026, 10, 15, 12, 0), "B")])

        def test_r19_naive_starts_at_rejected_without_leaking_contacts(self):
            appt = _appt(datetime(2026, 10, 15, 14, 0))
            with self.assertRaises(ValueError) as ctx:
                plan_reminders([appt], NOW)
            self.assertNotIn(appt["email"], str(ctx.exception))
            self.assertNotIn(appt["phone"], str(ctx.exception))

        def test_r19_naive_now_rejected(self):
            with self.assertRaises(ValueError):
                plan_reminders([_appt(STARTS)], datetime(2026, 10, 13, 9, 0))

        def test_r19_missing_fields_skipped_with_report(self):
            with self.assertLogs("brennan.reminders", level="WARNING") as cm:
                out = plan_reminders([_appt(STARTS, customer_name="")], NOW)
            self.assertEqual(out, [])
            self.assertTrue(any("customer_name" in line for line in cm.output))

        def test_logs_contain_no_contact_details(self):
            appt = _appt(STARTS)
            with self.assertLogs("brennan.reminders", level="INFO") as cm:
                plan_reminders([appt], NOW)
            joined = "\n".join(cm.output)
            self.assertIn("channel=sms", joined)
            self.assertIn("appointment_id=A1", joined)
            self.assertNotIn(appt["email"], joined)
            self.assertNotIn(appt["phone"], joined)

        def test_r22_stateless_repeat_calls_match(self):
            appts = [_appt(STARTS)]
            self.assertEqual(plan_reminders(appts, NOW), plan_reminders(appts, NOW))

    unittest.main(verbosity=2)