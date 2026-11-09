"""Brennan Opticians appointment reminder planning.

Pure logic: no I/O, no logging, no datetime.now(). `now` is an input.
Not executed in the authoring environment. Files were not written and tests were not run.

Known contradictions in the spec (implemented as literally written, see tests):
- Drop rule (send_at >= start_at is dropped) conflicts with the examples "immediate send at 22:00 gives 08:00 next day" and "at 03:00 gives 08:00 same day". When both points have passed, start_at <= now + 2h, so the 08:00 clamp is always >= start_at and is dropped.
- The clamp rule ("now before 08:00 gives 08:00 same day, else 08:00 next day") conflicts with "first allowed moment at or after now" when now is in allowed hours (for example 20:30) and the candidate is in quiet hours. Implemented as the explicit 08:00 rule.
- Rung 2 initials produce a double period ("with A. B..") because the template ends with a period.

Open items (CLIENT CONFIRM): 2-hour offset; quiet window and timezone; 08:00 clamp vs drop; 48h-passed/2h-pending gives no immediate send; no-phone email fallback; missing optout treated as False; status match rule; signature field and name form; shortening ladder; len() vs GSM-7/UCS-2; date format; email wording; PL behaviour (none attached); field names; duplicate appointment_id (not deduplicated).
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
OFFSETS = (timedelta(hours=2), timedelta(hours=48))  # CLIENT CONFIRM 2h; 2h first for dedupe priority
QUIET_START = 21  # inclusive, Dublin wall clock
QUIET_END = 8  # exclusive
QUIET_MOVE_HOUR = 20
SMS_LIMIT = 160
PREFIX = "Brennan Opticians: appointment"


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def is_pl(code):
    return isinstance(code, str) and code.strip().upper() == "PL"


def _channel(appt):
    status = appt.get("status")
    if isinstance(status, str) and status.strip().lower() == "cancelled":
        return None
    phone = appt.get("phone")
    email = appt.get("email")
    has_phone = isinstance(phone, str) and phone.strip() != ""
    has_email = isinstance(email, str) and email.strip() != ""
    if has_phone and appt.get("optout_sms_v2") is not True:
        return "sms"
    if has_email:
        return "email"
    return None


def _in_quiet(local):
    return local.hour >= QUIET_START or local.hour < QUIET_END


def _quiet_adjust(t, now):
    local = t.astimezone(DUBLIN)
    if not _in_quiet(local):
        return t
    day = local.date()
    if local.hour >= QUIET_START:
        target_day = day
    else:
        target_day = day - timedelta(days=1)
    target = datetime(target_day.year, target_day.month, target_day.day,
                      QUIET_MOVE_HOUR, tzinfo=DUBLIN)
    if target >= now:
        return target
    nl = now.astimezone(DUBLIN)
    d = nl.date() if nl.hour < QUIET_END else nl.date() + timedelta(days=1)
    return datetime(d.year, d.month, d.day, QUIET_END, tzinfo=DUBLIN)


def _name(signature):
    if not isinstance(signature, str):
        return ""
    return " ".join(signature.split())


def _initials(name):
    return " ".join(w[0] + "." for w in name.split())


def _sms_text(local, name):
    base = f"{PREFIX} {local.strftime('%d/%m/%Y')} at {local.strftime('%H:%M')}"
    last = f"{base}."
    assert len(last) <= SMS_LIMIT
    if name:
        for who in (name, _initials(name)):
            text = f"{base} with {who}."
            if len(text) <= SMS_LIMIT:
                return text
    return last


def _email_text(local, name):
    base = f"{PREFIX} {local.strftime('%d/%m/%Y')} at {local.strftime('%H:%M')}"
    return f"{base} with {name}." if name else f"{base}."


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime") from None
    out = []
    for appt in appointments:
        aid = appt.get("appointment_id")
        start = appt.get("start_at")
        if not _aware(start):
            raise ValueError(
                f"appointment {aid}: start_at must be a timezone-aware datetime"
            ) from None
        channel = _channel(appt)
        if channel is None or start <= now:
            continue
        local_start = start.astimezone(DUBLIN)
        name = _name(appt.get("signature"))
        if channel == "sms":
            text = _sms_text(local_start, name)
        else:
            text = _email_text(local_start, name)
        pending = [c for c in (start - h for h in OFFSETS) if c > now] or [now]
        kept = []
        for candidate in pending:
            send = _quiet_adjust(candidate, now)
            if send >= start or send in kept:
                continue
            kept.append(send)
        for send in kept:
            out.append({
                "appointment_id": aid,
                "channel": channel,
                "send_at": send.astimezone(UTC),
                "text": text,
            })
    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"])))
    return out


# ===== test_reminders.py (separate file, shown after this marker) =====
# import logging
# import unittest
# from datetime import datetime, timezone
# from zoneinfo import ZoneInfo
#
# import reminders as R
#
# D = ZoneInfo("Europe/Dublin")
# UTC = timezone.utc
# EMAIL = "customer.secret@example.com"
#
#
# def dub(*a):
#     return datetime(*a, tzinfo=D)
#
#
# def utc(*a):
#     return datetime(*a, tzinfo=UTC)
#
#
# def appt(start, **kw):
#     a = {"appointment_id": "A1", "start_at": start, "status": "booked",
#          "phone": "+353870000000", "email": None, "optout_sms_v2": False,
#          "country_code": "IE", "signature": "Brennan"}
#     a.update(kw)
#     return a
#
#
# def sends(start, now, **kw):
#     return [r["send_at"] for r in R.plan_reminders([appt(start, **kw)], now)]
#
#
# NOW = dub(2026, 10, 1, 9, 0)
# START = dub(2026, 10, 5, 10, 0)
#
#
# class ChannelTests(unittest.TestCase):
#     def test_cancelled_variants_excluded(self):
#         for s in ("cancelled", "Cancelled", " CANCELLED "):
#             with self.subTest(status=s):
#                 self.assertEqual(R.plan_reminders([appt(START, status=s)], NOW), [])
#
#     def test_other_statuses_included(self):
#         for s in ("no_show", "completed", None):
#             with self.subTest(status=s):
#                 self.assertEqual(len(R.plan_reminders([appt(START, status=s)], NOW)), 2)
#
#     def test_sms_when_phone_and_not_opted_out(self):
#         r = R.plan_reminders([appt(START)], NOW)
#         self.assertTrue(r and all(x["channel"] == "sms" for x in r))
#
#     def test_email_when_opted_out_with_email(self):
#         r = R.plan_reminders([appt(START, optout_sms_v2=True, email=EMAIL)], NOW)
#         self.assertTrue(r and all(x["channel"] == "email" for x in r))
#
#     def test_nothing_when_opted_out_without_email(self):
#         self.assertEqual(R.plan_reminders([appt(START, optout_sms_v2=True)], NOW), [])
#
#     def test_nothing_when_no_phone_no_email(self):
#         self.assertEqual(R.plan_reminders([appt(START, phone=None)], NOW), [])
#
#     def test_email_when_phone_blank(self):
#         r = R.plan_reminders([appt(START, phone="   ", email=EMAIL)], NOW)
#         self.assertTrue(r and all(x["channel"] == "email" for x in r))
#
#     def test_ignores_old_opt_out_field(self):
#         r = R.plan_reminders([appt(START, opt_out=True)], NOW)
#         self.assertTrue(r and all(x["channel"] == "sms" for x in r))
#
#     def test_empty_input(self):
#         self.assertEqual(R.plan_reminders([], NOW), [])
#
#     def test_is_pl(self):
#         self.assertTrue(R.is_pl(" pl "))
#         self.assertFalse(R.is_pl("IE"))
#
#
# class ScheduleTests(unittest.TestCase):
#     def test_both_pending(self):
#         self.assertEqual(sends(START, NOW), [utc(2026, 10, 3, 9, 0), utc(2026, 10, 5, 7, 0)])
#
#     def test_only_2h_pending(self):
#         self.assertEqual(sends(dub(2026, 10, 5, 12, 0), dub(2026, 10, 5, 7, 0)),
#                          [utc(2026, 10, 5, 9, 0)])
#
#     def test_both_passed_immediate(self):
#         now = dub(2026, 10, 5, 11, 0)
#         self.assertEqual(sends(dub(2026, 10, 5, 12, 0), now), [now.astimezone(UTC)])
#
#     def test_start_passed_nothing(self):
#         self.assertEqual(sends(dub(2026, 10, 5, 12, 0), dub(2026, 10, 5, 12, 0)), [])
#         self.assertEqual(sends(dub(2026, 10, 5, 12, 0), dub(2026, 10, 5, 13, 0)), [])
#
#     def test_0700_moves_to_2000_previous_day(self):
#         self.assertIn(utc(2026, 10, 5, 19, 0), sends(dub(2026, 10, 6, 9, 0), NOW))
#
#     def test_2130_moves_to_2000_same_day(self):
#         self.assertIn(utc(2026, 10, 6, 19, 0), sends(dub(2026, 10, 6, 23, 30), NOW))
#
#     def test_2100_is_quiet(self):
#         self.assertIn(utc(2026, 10, 6, 19, 0), sends(dub(2026, 10, 6, 23, 0), NOW))
#
#     def test_0800_is_not_quiet(self):
#         self.assertIn(utc(2026, 10, 6, 7, 0), sends(dub(2026, 10, 6, 10, 0), NOW))
#
#     def test_clamp_to_0800_next_day_not_past(self):
#         # 20:00 target (Oct 5) is before now (21:30), so clamp to 08:00 Oct 6.
#         self.assertEqual(sends(dub(2026, 10, 6, 9, 0), dub(2026, 10, 5, 21, 30)),
#                          [utc(2026, 10, 6, 7, 0)])
#
#     def test_immediate_in_quiet_hours_dropped_by_drop_rule(self):
#         # Both points passed, so start <= now + 2h; the 08:00 clamp is >= start and is dropped.
#         # This contradicts the spec examples (22:00 -> 08:00 next day; 03:00 -> 08:00 same day).
#         self.assertEqual(sends(dub(2026, 10, 6, 0, 0), dub(2026, 10, 5, 22, 0)), [])
#         self.assertEqual(sends(dub(2026, 10, 6, 4, 0), dub(2026, 10, 6, 3, 0)), [])
#
#     def test_invariant_window_and_quiet(self):
#         now = dub(2026, 10, 1, 9, 0)
#         for h in range(24):
#             for m in (0, 30):
#                 start = dub(2026, 10, 7, h, m)
#                 for r in R.plan_reminders([appt(start)], now):
#                     s = r["send_at"]
#                     self.assertTrue(now <= s < start)
#                     local = s.astimezone(D)
#                     self.assertFalse(local.hour >= 21 or local.hour < 8)
#
#
# class TextTests(unittest.TestCase):
#     def first_text(self, **kw):
#         return R.plan_reminders([appt(START, **kw)], NOW)[0]["text"]
#
#     def test_rung1(self):
#         self.assertEqual(self.first_text(),
#                          "Brennan Opticians: appointment 05/10/2026 at 10:00 with Brennan.")
#
#     def test_rung2_initials_for_long_name(self):
#         sig = "A" * 60 + " " + "B" * 59
#         self.assertEqual(self.first_text(signature=sig),
#                          "Brennan Opticians: appointment 05/10/2026 at 10:00 with A. B..")
#
#     def test_rung3_pathological(self):
#         sig = " ".join(["x"] * 100)
#         self.assertEqual(self.first_text(signature=sig),
#                          "Brennan Opticians: appointment 05/10/2026 at 10:00.")
#
#     def test_sms_length_within_limit(self):
#         for sig in ("Brennan", "x" * 300, " ".join(["y"] * 100), "Siobhán Ní Dhuibhir"):
#             for r in R.plan_reminders([appt(START, signature=sig)], NOW):
#                 self.assertLessEqual(len(r["text"]), 160)
#
#     def test_non_ascii_preserved(self):
#         self.assertIn("Siobhán Ní Dhuibhir",
#                       self.first_text(signature="Siobhán Ní Dhuibhir"))
#
#     def test_whitespace_collapsed(self):
#         self.assertIn("with Brennan Opticians.",
#                       self.first_text(signature="  Brennan   Opticians "))
#
#     def test_email_text_full_name_no_limit(self):
#         sig = "Ab " * 100
#         r = R.plan_reminders([appt(START, optout_sms_v2=True, email=EMAIL, signature=sig)], NOW)
#         self.assertIn(" ".join(sig.split()), r[0]["text"])
#
#
# class OrderingTests(unittest.TestCase):
#     def test_sorted_and_tie_broken(self):
#         a = appt(START, appointment_id="B")
#         b = appt(START, appointment_id="A")
#         c = appt(dub(2026, 10, 6, 10, 0), appointment_id="C")
#         res = R.plan_reminders([a, c, b], NOW)
#         keys = [(r["send_at"], r["appointment_id"]) for r in res]
#         self.assertEqual(keys, sorted(keys))
#         first = res[0]["send_at"]
#         self.assertEqual([r["appointment_id"] for r in res if r["send_at"] == first], ["A", "B"])
#
#     def test_no_mutation(self):
#         a = appt(START, email=EMAIL)
#         snapshot = dict(a)
#         R.plan_reminders([a], NOW)
#         self.assertEqual(a, snapshot)
#
#
# class ValidationAndPrivacyTests(unittest.TestCase):
#     def test_naive_now_raises_without_leaking(self):
#         with self.assertRaises(ValueError) as cm:
#             R.plan_reminders([appt(START, email=EMAIL, phone=None)], datetime(2026, 10, 1, 9, 0))
#         self.assertNotIn(EMAIL, str(cm.exception))
#
#     def test_naive_start_raises_without_leaking(self):
#         a = appt(datetime(2026, 10, 5, 10, 0), email=EMAIL, phone=None)
#         with self.assertRaises(ValueError) as cm:
#             R.plan_reminders([a], NOW)
#         self.assertNotIn(EMAIL, str(cm.exception))
#
#     def test_nothing_logged_and_no_email_in_output(self):
#         records = []
#
#         class Capture(logging.Handler):
#             def emit(self, record):
#                 records.append(record)
#
#         root = logging.getLogger()
#         handler = Capture(logging.DEBUG)
#         old_level = root.level
#         root.addHandler(handler)
#         root.setLevel(logging.DEBUG)
#         try:
#             res = R.plan_reminders([appt(START, optout_sms_v2=True, email=EMAIL)], NOW)
#         finally:
#             root.removeHandler(handler)
#             root.setLevel(old_level)
#         self.assertEqual(records, [])
#         self.assertNotIn(EMAIL, str(res))
#         self.assertNotIn(EMAIL, repr(res))
#
#
# class DstTests(unittest.TestCase):
#     def test_summer_and_winter(self):
#         self.assertIn(utc(2026, 7, 1, 7, 0), sends(dub(2026, 7, 1, 10, 0), dub(2026, 6, 20, 9, 0)))
#         self.assertIn(utc(2026, 12, 1, 8, 0), sends(dub(2026, 12, 1, 10, 0), dub(2026, 11, 20, 9, 0)))
#
#
# class KeyTests(unittest.TestCase):
#     def test_result_keys_exact(self):
#         for r in R.plan_reminders([appt(START)], NOW):
#             self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
#
#
# if __name__ == "__main__":
#     unittest.main()