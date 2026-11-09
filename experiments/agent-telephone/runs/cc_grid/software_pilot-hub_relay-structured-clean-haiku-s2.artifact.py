"""Appointment reminder planning for Brennan Opticians.

Single public entry point: plan_reminders(appointments, now).
Returns a list of dicts with keys appointment_id, channel, send_at (timezone-aware, UTC), text.
Sorted by send_at, then appointment_id, then channel.

Provisional defaults used from the PM spec (client to confirm):
- Q1: optout_sms_v2 missing, None, or anything other than False means opted out.
- Q2: 48-hour reminder sent at now only if at least 2 hours remain; otherwise nothing is sent.
- Q3: quiet-hours move target is 20:00:00 Europe/Dublin on the preceding evening.
- Q4: if that moved time is before now, use 08:00 Europe/Dublin the next morning if it is before starts_at; otherwise drop.
- Q5: empty string phone or email is treated as missing; no other validation or normalisation.
- Q6: appointment date shown as dd/mm/yyyy. Q7: appointment times shown in Europe/Dublin, HH:MM.
- Q8: SMS over 160 characters: shorten customer name to first name; if still over, drop and log only the id.
- Q10: the 160-character limit includes the signature.
- Q11: country is a two-letter code, matched case-insensitively; PL gets the Polish signature.
- Q12 (A2, provisional template): email text is "Subject: Appointment reminder", blank line, then a plain-text body ending with the signature.
- Q13: only status "cancelled" (case-insensitive) is excluded.
- Q14: ties sorted by appointment_id ascending (integers numerically), then channel.
- Q15: invalid appointments are skipped and only their id is logged.
- Q16: opted-out customer with no email produces no output; only the id is logged.

Defaults not stated in the spec (flag for client):
- Accepted statuses are booked, confirmed, cancelled, completed. Any other status is treated as invalid and skipped with the id logged.
- A customer who is not opted out but has no phone falls back to email.
- send_at is returned in UTC. Quiet hours and appointment dates are evaluated in Europe/Dublin.
- The log line for an SMS shows the phone number as the contact. For email, the contact is a placeholder; the address is never logged (R15).

SMS encoding risk (Q9): the name "Siobhán" and the signatures contain á and í, which are outside GSM-7. Such SMS will likely be sent as UCS-2, with 70-character segments rather than 160. The 160-character limit is implemented as specified.

Testing note: this module was written without executing the test suite in this environment.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

_LOG = logging.getLogger("brennan.reminders")
_DUBLIN = ZoneInfo("Europe/Dublin")
_UTC = timezone.utc
_SMS_LIMIT = 160
_SIG_IE = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"
_REQUIRED = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")
_KNOWN_STATUSES = frozenset({"booked", "confirmed", "cancelled", "completed"})
_H2 = timedelta(hours=2)
_H48 = timedelta(hours=48)
_QUIET_START = time(21, 0)
_QUIET_END = time(8, 0)


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list of dicts")
    now_utc = now.astimezone(_UTC)
    planned = []
    for appt in appointments:
        try:
            items = _plan_one(appt, now_utc)
        except Exception as exc:  # one bad record must not break the batch; log id only
            _LOG.warning("appointment skipped id=%r: unexpected %s", _safe_id(appt), type(exc).__name__)
            continue
        for msg, name, contact in items:
            planned.append(msg)
            _LOG.info(
                "planned reminder appointment_id=%r to=%r channel=%s contact=%s send_at=%s",
                msg["appointment_id"], name, msg["channel"], contact, msg["send_at"].isoformat(),
            )
    planned.sort(key=_sort_key)
    return planned


def _sort_key(msg):
    aid = msg["appointment_id"]
    id_key = (0, aid, "") if isinstance(aid, int) else (1, 0, str(aid))
    return (msg["send_at"], id_key, msg["channel"])


def _safe_id(appt):
    return appt.get("id") if isinstance(appt, dict) else None


def _skip(aid, reason):
    _LOG.warning("appointment skipped id=%r: %s", aid, reason)
    return []


def _none(aid, reason):
    _LOG.info("no reminder id=%r: %s", aid, reason)
    return []


def _present(value):
    return value if isinstance(value, str) and value else None


def _plan_one(appt, now):
    aid = _safe_id(appt)
    if not isinstance(appt, dict) or any(k not in appt for k in _REQUIRED):
        return _skip(aid, "missing required fields")
    starts = appt["starts_at"]
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        return _skip(aid, "starts_at must be a timezone-aware datetime")
    status = appt["status"]
    if not isinstance(status, str):
        return _skip(aid, "status must be a string")
    status = status.strip().lower()
    if status == "cancelled":
        return _none(aid, "cancelled")
    if status not in _KNOWN_STATUSES:
        return _skip(aid, "unknown status")
    name = appt["customer_name"]
    if not isinstance(name, str):
        return _skip(aid, "customer_name must be a string")
    name = name.strip()
    email = _present(appt["email"])
    phone = _present(appt["phone"])
    starts = starts.astimezone(_UTC)
    if starts <= now:
        return _none(aid, "appointment already started")
    if appt.get("optout_sms_v2") is not False:  # Q1: missing, null or non-False means opted out
        if email is None:
            return _none(aid, "opted out and no email on file")
        channel = "email"
    elif phone is not None:
        channel = "sms"
    elif email is not None:
        channel = "email"  # provisional: no phone, fall back to email
    else:
        return _none(aid, "no phone or email on file")

    country = appt["country"]
    sig = _SIG_PL if isinstance(country, str) and country.strip().upper() == "PL" else _SIG_IE
    local = starts.astimezone(_DUBLIN)
    date_s = local.strftime("%d/%m/%Y")
    time_s = local.strftime("%H:%M")
    contact = phone if channel == "sms" else "(email on file, not logged per R15)"

    out = []
    for hours_before in (48, 2):
        send = _slot(hours_before, starts, now)
        if send is None:
            continue
        send = _quiet_adjust(send, now, starts)
        if send is None:
            _LOG.info("reminder not planned id=%r: no valid time after quiet hours", aid)
            continue
        text = _text(channel, name, sig, date_s, time_s)
        if text is None:
            _LOG.warning("reminder dropped id=%r: SMS over 160 characters after shortening", aid)
            continue
        msg = {"appointment_id": aid, "channel": channel, "send_at": send, "text": text}
        out.append((msg, name, contact))
    return out


def _slot(hours_before, starts, now):
    # starts is UTC-aware, so these subtractions are absolute (DST-safe).
    if hours_before == 2:
        t = starts - _H2
        return t if t >= now else None  # R7: never earlier than now
    t = starts - _H48
    if t > now:
        return t
    if starts - now >= _H2:
        return now  # R6 with Q2 default
    return None


def _quiet_adjust(send, now, starts):
    # send and starts are UTC-aware; quiet hours are judged in Dublin local time.
    local = send.astimezone(_DUBLIN)
    t = local.time()
    if _QUIET_END <= t < _QUIET_START:
        return send
    evening = local.date() if t >= _QUIET_START else local.date() - timedelta(days=1)
    moved = datetime.combine(evening, time(20, 0), tzinfo=_DUBLIN).astimezone(_UTC)
    if moved >= now:
        return moved
    morning = datetime.combine(evening + timedelta(days=1), _QUIET_END, tzinfo=_DUBLIN).astimezone(_UTC)
    if now <= morning < starts:
        return morning
    return None


def _sms(who, date_s, time_s, sig):
    greet = f"Hi {who}, " if who else "Hi, "
    return f"{greet}reminder of your Brennan Opticians appointment on {date_s} at {time_s}. {sig}"


def _text(channel, name, sig, date_s, time_s):
    if channel == "email":
        greet = f"Hello {name}," if name else "Hello,"
        body = (f"{greet}\n\nThis is a reminder of your appointment at Brennan Opticians "
                f"on {date_s} at {time_s} (Irish time).\n\n{sig}")
        return "Subject: Appointment reminder\n\n" + body
    parts = name.split()
    first = parts[0] if parts else ""
    for who in (name, first):  # Q8: shorten name to first name only
        text = _sms(who, date_s, time_s, sig)
        if len(text) <= _SMS_LIMIT:
            return text
    return None


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------

_EMAIL = "client.person@example.invalid"
_NOW = None  # set below after helpers


def _dub(*a):
    return datetime(*a, tzinfo=_DUBLIN)


def _utc(*a):
    return datetime(*a, tzinfo=_UTC)


def _appt(**kw):
    a = {
        "id": 1,
        "customer_name": "Siobhán Murphy",
        "email": _EMAIL,
        "phone": "+353871234567",
        "country": "IE",
        "status": "booked",
        "starts_at": _dub(2026, 10, 20, 10, 0),
        "optout_sms_v2": False,
    }
    a.update(kw)
    return a


_NOW = _utc(2026, 10, 10, 0, 0)


class ScheduleTests(unittest.TestCase):
    def test_48h_and_2h_reminders(self):
        out = plan_reminders([_appt()], _NOW)
        self.assertEqual([m["send_at"] for m in out], [_utc(2026, 10, 18, 9, 0), _utc(2026, 10, 20, 7, 0)])
        self.assertEqual([m["channel"] for m in out], ["sms", "sms"])

    def test_48h_passed_sends_first_now(self):  # R6
        now = _utc(2026, 10, 18, 12, 0)
        out = plan_reminders([_appt()], now)
        self.assertEqual([m["send_at"] for m in out], [now, _utc(2026, 10, 20, 7, 0)])

    def test_under_2h_remaining_sends_nothing(self):  # Q2
        self.assertEqual(plan_reminders([_appt()], _utc(2026, 10, 20, 7, 30)), [])

    def test_exactly_2h_remaining_sends_both_now(self):  # Q2 boundary
        now = _utc(2026, 10, 20, 7, 0)
        out = plan_reminders([_appt()], now)
        self.assertEqual([m["send_at"] for m in out], [now, now])

    def test_no_send_earlier_than_now(self):  # R7
        now = _utc(2026, 10, 18, 12, 0)
        out = plan_reminders([_appt()], now)
        self.assertTrue(all(m["send_at"] >= now for m in out))

    def test_started_appointment_gives_nothing(self):  # A3
        self.assertEqual(plan_reminders([_appt()], _utc(2026, 10, 20, 11, 0)), [])

    def test_empty_input_returns_empty_list(self):
        out = plan_reminders([], _NOW)
        self.assertIsInstance(out, list)
        self.assertEqual(out, [])


class QuietHoursTests(unittest.TestCase):
    def test_2h_reminder_moves_to_previous_evening(self):  # R12
        now = _utc(2026, 10, 18, 12, 0)
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 20, 8, 30))], now)
        self.assertEqual([m["send_at"] for m in out], [now, _utc(2026, 10, 19, 19, 0)])

    def test_window_boundaries(self):  # R12, 21:00 to 08:00
        now = _utc(2026, 10, 1)
        starts = _utc(2026, 10, 30, 10, 0)

        def adj(local_dt):
            return _quiet_adjust(local_dt.astimezone(_UTC), now, starts)

        self.assertEqual(adj(_dub(2026, 10, 20, 8, 0)), _dub(2026, 10, 20, 8, 0))
        self.assertEqual(adj(_dub(2026, 10, 20, 20, 59, 59)), _dub(2026, 10, 20, 20, 59, 59))
        self.assertEqual(adj(_dub(2026, 10, 20, 21, 0)), _dub(2026, 10, 20, 20, 0))
        self.assertEqual(adj(_dub(2026, 10, 20, 7, 59, 59)), _dub(2026, 10, 19, 20, 0))

    def test_fallback_to_morning_when_moved_time_passed(self):  # Q4
        now = _dub(2026, 10, 19, 23, 0).astimezone(_UTC)
        starts = _dub(2026, 10, 20, 10, 0).astimezone(_UTC)
        send = _dub(2026, 10, 20, 7, 30).astimezone(_UTC)
        self.assertEqual(_quiet_adjust(send, now, starts), _dub(2026, 10, 20, 8, 0))

    def test_fallback_dropped_when_morning_is_after_start(self):  # Q4
        now = _dub(2026, 10, 19, 23, 0).astimezone(_UTC)
        starts = _dub(2026, 10, 20, 7, 45).astimezone(_UTC)
        send = _dub(2026, 10, 20, 7, 30).astimezone(_UTC)
        self.assertIsNone(_quiet_adjust(send, now, starts))

    def test_dst_march_quiet_move_across_clock_change(self):  # R13
        now = _utc(2026, 3, 28, 12, 0)
        out = plan_reminders([_appt(starts_at=_dub(2026, 3, 29, 8, 30))], now)
        self.assertEqual([m["send_at"] for m in out], [now, _utc(2026, 3, 28, 20, 0)])

    def test_dst_march_48h_is_absolute_duration(self):  # R13
        out = plan_reminders([_appt(starts_at=_dub(2026, 3, 30, 10, 0))], _utc(2026, 3, 20))
        self.assertEqual([m["send_at"] for m in out], [_utc(2026, 3, 28, 9, 0), _utc(2026, 3, 30, 7, 0)])

    def test_dst_october_quiet_move_across_clock_change(self):  # R13
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 26, 8, 30))], _utc(2026, 10, 24, 0, 0))
        self.assertEqual([m["send_at"] for m in out], [_utc(2026, 10, 24, 8, 30), _utc(2026, 10, 25, 20, 0)])

    def test_dst_october_48h_is_absolute_duration(self):  # R13
        out = plan_reminders([_appt(starts_at=_dub(2026, 10, 26, 10, 0))], _NOW)
        self.assertEqual([m["send_at"] for m in out], [_utc(2026, 10, 24, 10, 0), _utc(2026, 10, 26, 8, 0)])


class SmsAndTextTests(unittest.TestCase):
    def test_text_contains_date_time_and_signature(self):  # R10, R16
        out = plan_reminders([_appt()], _NOW)
        self.assertIn("20/10/2026", out[0]["text"])
        self.assertIn("10:00", out[0]["text"])
        self.assertTrue(out[0]["text"].endswith(_SIG_IE))

    def test_polish_signature_case_insensitive(self):  # R16, Q11
        out = plan_reminders([_appt(country="pl")], _NOW)
        self.assertTrue(all(m["text"].endswith(_SIG_PL) for m in out))

    def test_long_name_shortened_to_first_name(self):  # R11, Q8
        out = plan_reminders([_appt(customer_name="Aoife " + "B" * 70)], _NOW)
        sms = [m for m in out if m["channel"] == "sms"]
        self.assertTrue(sms)
        for m in sms:
            self.assertLessEqual(len(m["text"]), 160)
            self.assertIn("Hi Aoife,", m["text"])
            self.assertNotIn("BBBB", m["text"])

    def test_unshortenable_sms_dropped_and_id_logged(self):  # R11
        with self.assertLogs(_LOG, level="INFO") as cm:
            out = plan_reminders([_appt(id=77, customer_name="C" * 70)], _NOW)
        self.assertEqual(out, [])
        self.assertTrue(any("id=77" in line for line in cm.output))

    def test_opted_out_gets_email_only(self):  # R8, R9
        out = plan_reminders([_appt(optout_sms_v2=True)], _NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual({m["channel"] for m in out}, {"email"})
        self.assertTrue(all("Subject:" in m["text"] and m["text"].endswith(_SIG_IE) for m in out))

    def test_missing_optout_treated_as_opted_out(self):  # Q1
        a = _appt()
        del a["optout_sms_v2"]
        self.assertEqual({m["channel"] for m in plan_reminders([a], _NOW)}, {"email"})

    def test_null_optout_treated_as_opted_out(self):  # Q1
        self.assertEqual({m["channel"] for m in plan_reminders([_appt(optout_sms_v2=None)], _NOW)}, {"email"})

    def test_old_opt_out_field_is_ignored(self):  # R4
        out = plan_reminders([_appt(opt_out=True, optout_sms_v2=False)], _NOW)
        self.assertEqual({m["channel"] for m in out}, {"sms"})

    def test_empty_phone_uses_email(self):  # Q5, R8
        out = plan_reminders([_appt(phone="")], _NOW)
        self.assertEqual({m["channel"] for m in out}, {"email"})

    def test_opted_out_without_email_gives_nothing_and_logs_id(self):  # A4, Q16
        with self.assertLogs(_LOG, level="INFO") as cm:
            out = plan_reminders([_appt(id=5, optout_sms_v2=True, email="")], _NOW)
        self.assertEqual(out, [])
        self.assertTrue(any("id=5" in line for line in cm.output))

    def test_no_phone_no_email_gives_nothing(self):  # A4
        self.assertEqual(plan_reminders([_appt(phone="", email="")], _NOW), [])


class StatusAndOrderingTests(unittest.TestCase):
    def test_cancelled_excluded(self):  # R14
        self.assertEqual(plan_reminders([_appt(status="Cancelled ")], _NOW), [])

    def test_other_status_not_excluded(self):  # Q13
        self.assertEqual(len(plan_reminders([_appt(status="confirmed")], _NOW)), 2)

    def test_unknown_status_skipped_with_id_logged(self):  # A1
        with self.assertLogs(_LOG, level="INFO") as cm:
            out = plan_reminders([_appt(id=9, status="mystery")], _NOW)
        self.assertEqual(out, [])
        self.assertTrue(any("id=9" in line for line in cm.output))

    def test_sorted_by_send_at_then_id_then_channel(self):  # R18, Q14
        out = plan_reminders([_appt(id=10), _appt(id=2)], _NOW)
        self.assertEqual([m["appointment_id"] for m in out], [2, 10, 2, 10])
        self.assertEqual([m["send_at"] for m in out], sorted(m["send_at"] for m in out))


class InputAndPrivacyTests(unittest.TestCase):
    def test_naive_now_raises(self):  # A1
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([_appt()], datetime(2026, 10, 10))
        self.assertNotIn(_EMAIL, str(ctx.exception))

    def test_non_list_raises(self):
        with self.assertRaises(TypeError):
            plan_reminders("nope", _NOW)

    def test_naive_starts_skipped_and_logged(self):  # A1
        with self.assertLogs(_LOG, level="INFO") as cm:
            out = plan_reminders([_appt(id=3, starts_at=datetime(2026, 10, 20, 10, 0))], _NOW)
        self.assertEqual(out, [])
        self.assertTrue(any("id=3" in line for line in cm.output))

    def test_missing_key_skipped_and_logged(self):  # A1
        a = _appt(id=4)
        del a["phone"]
        with self.assertLogs(_LOG, level="INFO") as cm:
            out = plan_reminders([a], _NOW)
        self.assertEqual(out, [])
        self.assertTrue(any("id=4" in line for line in cm.output))

    def test_no_email_in_logs_or_errors(self):  # R15
        good = _appt(id=1)
        opted_no_email = _appt(id=2, optout_sms_v2=True, email="")
        bad_start = _appt(id=3, starts_at=datetime(2026, 10, 20, 10, 0))
        broken = {"id": 4, "email": _EMAIL}
        with self.assertLogs(_LOG, level="DEBUG") as cm:
            out = plan_reminders([good, opted_no_email, bad_start, broken], _NOW)
        self.assertTrue(out)
        log_text = "\n".join(cm.output)
        self.assertNotIn(_EMAIL, log_text)
        self.assertNotIn("example.invalid", log_text)
        with self.assertRaises(ValueError) as ctx:
            plan_reminders([good], datetime(2026, 10, 10))
        self.assertNotIn(_EMAIL, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()