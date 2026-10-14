"""Appointment reminder planning for Brennan Opticians (standard library only).

Entry point: plan_reminders(appointments, now).

Decisions that may change after client confirmation are isolated in the
constants block and in the marked helpers below:
- TWO_HOUR_OFFSET (R6): 2-hour reminder offset, not yet confirmed by the client.
- R20: a quiet-hours shift that lands before now is replaced by now. If now is
  itself inside quiet hours, the reminder is still sent at now. This is an
  unresolved conflict for the client.
- R21: if both reminders collapse to the same send_at (both at now), only the
  2-hour reminder is kept.
- R23: if the SMS cannot fit after name shortening, the reminder goes by email.
  With the current template this is only reachable if SMS_MAX_LENGTH is lowered.
  If there is no email either, no reminder is returned.
- R24: only "cancelled" is excluded by status.
- R25: ties are sorted by appointment_id.
- R26/R27: no contact route, or opt-out with no email, gives no reminder.
- Logging conflict: the house rule asks for the contact in each INFO line, but
  R14 forbids logging customer data. The log line therefore carries only
  appointment_id, channel and send_at. The client needs to decide this.
- SMS length uses len() on code points. GSM-7 encoding is not modelled.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders", "FIRST_OFFSET", "TWO_HOUR_OFFSET", "SMS_MAX_LENGTH"]

LOG = logging.getLogger("brennan_reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

# Isolated configuration. Change here only.
FIRST_OFFSET = timedelta(hours=48)
TWO_HOUR_OFFSET = timedelta(hours=2)  # R6: unconfirmed by client
SMS_MAX_LENGTH = 160
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_SHIFT_TO = time(20, 0)
EXCLUDED_STATUSES = frozenset({"cancelled"})  # R13 / R24
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
EMAIL_SUBJECT = "Your Brennan Opticians appointment reminder"  # sender-side only; not returned (R28)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _fmt_date(local):
    return f"{local.day:02d} {MONTHS[local.month - 1]} {local.year}"


def _fmt_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def _body(name, date_s, time_s, sig):
    who = f" ({name})" if name else ""
    return f"Brennan Opticians{who}: appointment {date_s} at {time_s}. {sig}"


def _sms_text(name, date_s, time_s, sig):
    base = _body("", date_s, time_s, sig)
    if len(base) > SMS_MAX_LENGTH:
        return None  # R23: caller falls back to email
    budget = SMS_MAX_LENGTH - len(base) - len(" ()")
    if budget < 1:
        return base
    if len(name) > budget:
        # R11: shorten the name only; date, time and signature are kept.
        name = name[: budget - 3].rstrip() + "..." if budget >= 4 else name[:budget]
    return _body(name, date_s, time_s, sig)


def _in_quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _schedule(send_at, now):
    """Apply R8, R12 and R20 to one planned send time."""
    if send_at < now:
        send_at = now
    local = send_at.astimezone(DUBLIN)
    if not _in_quiet(local):
        return send_at
    day = local.date()
    if local.time() < QUIET_END:
        day -= timedelta(days=1)
    evening = datetime.combine(day, QUIET_SHIFT_TO, tzinfo=DUBLIN).astimezone(UTC)
    # R20: a shifted time before now becomes now (also covers now inside quiet hours).
    return now if evening < now else evening


def _choose(sms_preferred, email, name, date_s, time_s, sig):
    """Return (channel, text) or None. Never both channels (R10)."""
    if sms_preferred:
        text = _sms_text(name, date_s, time_s, sig)
        if text is not None:
            return "sms", text
    if email:
        return "email", _body(name, date_s, time_s, sig)
    return None


def _plan_one(appt, now):
    if appt.get("status") in EXCLUDED_STATUSES:
        return []
    starts = appt["starts_at"]
    if starts.utcoffset() is None:
        raise ValueError("starts_at must be timezone-aware")
    if starts <= now:  # R22
        return []

    sms_preferred = bool(appt.get("phone")) and not appt.get("optout_sms_v2")  # R3, R9
    email = appt.get("email")

    t_first = starts - FIRST_OFFSET
    t_second = starts - TWO_HOUR_OFFSET
    if t_second <= now:  # R21: 2-hour point passed, send only one reminder now
        slots = [now]
    elif t_first <= now:  # R7
        slots = [now, t_second]
    else:
        slots = [t_first, t_second]

    sends = [_schedule(t, now) for t in slots]
    if len(sends) == 2 and sends[0] == sends[1]:  # R21: avoid two messages at once
        sends = sends[1:]

    local = starts.astimezone(DUBLIN)
    sig = SIGNATURE_PL if appt.get("country") == "PL" else SIGNATURE  # R15
    picked = _choose(sms_preferred, email, appt.get("customer_name") or "",
                     _fmt_date(local), _fmt_time(local), sig)
    if picked is None:  # R26, R27, or R23 with no email fallback
        return []
    channel, text = picked
    return [
        {"appointment_id": appt["id"], "channel": channel,
         "send_at": s.astimezone(UTC), "text": text}  # R29
        for s in sends
    ]


def plan_reminders(appointments, now):
    if now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(UTC)
    out = []
    for appt in appointments:
        out.extend(_plan_one(appt, now))
    out.sort(key=lambda r: (r["send_at"], r["appointment_id"]))  # R17, R25
    for r in out:
        LOG.info("reminder planned appointment_id=%s channel=%s send_at=%s",
                 r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return out


# ---------------------------------------------------------------- tests

def _utc(*a):
    return datetime(*a, tzinfo=UTC)


def _appt(**kw):
    base = {
        "id": "a1", "customer_name": "Mary Murphy", "email": "mary@example.com",
        "phone": "+353871234567", "country": "IE", "status": "booked",
        "starts_at": None, "optout_sms_v2": False,
    }
    base.update(kw)
    return base


class TestPlanReminders(unittest.TestCase):

    def test_48h_and_2h_timing(self):
        now = _utc(2026, 10, 10, 12, 0)
        starts = _utc(2026, 10, 14, 14, 0)  # 15:00 IST
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_utc(2026, 10, 12, 14, 0), _utc(2026, 10, 14, 12, 0)])
        self.assertTrue(all(r["channel"] == "sms" for r in out))
        self.assertIn("14 Oct 2026 at 15:00", out[0]["text"])
        self.assertTrue(all(r["send_at"].utcoffset().total_seconds() == 0 for r in out))

    def test_past_48h_sends_first_now(self):
        now = _utc(2026, 10, 13, 12, 0)
        starts = _utc(2026, 10, 14, 14, 0)
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [now, _utc(2026, 10, 14, 12, 0)])

    def test_past_2h_sends_only_one_now(self):
        now = _utc(2026, 10, 14, 12, 30)
        starts = _utc(2026, 10, 14, 14, 0)
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], now)

    def test_started_or_now_after_start_gives_nothing(self):
        starts = _utc(2026, 10, 14, 14, 0)
        self.assertEqual(plan_reminders([_appt(starts_at=starts)], starts), [])
        self.assertEqual(plan_reminders([_appt(starts_at=starts)],
                                        starts + timedelta(hours=1)), [])

    def test_quiet_hours_evening_shift(self):
        now = _utc(2026, 10, 10, 12, 0)
        starts = _utc(2026, 10, 12, 22, 0)  # 23:00 IST
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_utc(2026, 10, 10, 19, 0), _utc(2026, 10, 12, 19, 0)])

    def test_quiet_hours_morning_shift(self):
        now = _utc(2026, 10, 10, 12, 0)
        starts = _utc(2026, 10, 14, 7, 0)  # 08:00 IST
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_utc(2026, 10, 12, 7, 0), _utc(2026, 10, 13, 19, 0)])

    def test_quiet_hours_boundaries(self):
        now = _utc(2026, 10, 10, 12, 0)
        # 08:00 local is allowed, not shifted.
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 9, 0))], now)
        self.assertEqual(out[-1]["send_at"], _utc(2026, 10, 14, 7, 0))
        # 21:00 local is quiet and shifts to 20:00 the same evening.
        now2 = _utc(2026, 10, 13, 12, 0)
        out2 = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 22, 0))], now2)
        self.assertEqual(out2[-1]["send_at"], _utc(2026, 10, 14, 19, 0))

    def test_quiet_shift_before_now_uses_now(self):  # R20
        now = _utc(2026, 10, 13, 19, 30)
        starts = _utc(2026, 10, 13, 23, 0)  # 00:00 IST on 14 Oct
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], now)
        self.assertIn("14 Oct 2026 at 00:00", out[0]["text"])

    def test_now_inside_quiet_hours_sends_now(self):  # R20 edge case, unresolved for client
        now = _utc(2026, 10, 13, 22, 0)  # 23:00 IST
        starts = _utc(2026, 10, 15, 14, 0)
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(out[0]["send_at"], now)
        self.assertEqual(out[1]["send_at"], _utc(2026, 10, 15, 12, 0))

    def test_dst_day_timing(self):
        now = _utc(2026, 10, 20, 12, 0)
        starts = _utc(2026, 10, 26, 10, 0)  # 10:00 GMT after DST ends
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_utc(2026, 10, 24, 10, 0), _utc(2026, 10, 26, 8, 0)])
        self.assertIn("26 Oct 2026 at 10:00", out[0]["text"])

    def test_dst_quiet_shift_uses_local_gmt_evening(self):
        now = _utc(2026, 10, 20, 12, 0)
        starts = _utc(2026, 10, 26, 9, 0)  # 07:00 GMT two-hour point is quiet
        out = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(out[-1]["send_at"], _utc(2026, 10, 25, 20, 0))

    def test_cancelled_excluded(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    status="cancelled")], _utc(2026, 10, 10, 12, 0))
        self.assertEqual(out, [])

    def test_optout_uses_email(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    optout_sms_v2=True)], _utc(2026, 10, 10, 12, 0))
        self.assertTrue(out)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_optout_without_email_gives_nothing(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    optout_sms_v2=True, email="")],
                             _utc(2026, 10, 10, 12, 0))
        self.assertEqual(out, [])

    def test_legacy_opt_out_field_ignored(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    opt_out=True)], _utc(2026, 10, 10, 12, 0))
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_no_phone_uses_email(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    phone=None)], _utc(2026, 10, 10, 12, 0))
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_no_phone_and_no_email_gives_nothing(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    phone=None, email=None)], _utc(2026, 10, 10, 12, 0))
        self.assertEqual(out, [])

    def test_sms_long_name_keeps_date_time_and_signature(self):
        name = "Maximilian " * 20
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    customer_name=name)], _utc(2026, 10, 10, 12, 0))
        for r in out:
            self.assertEqual(r["channel"], "sms")
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("14 Oct 2026 at 15:00", r["text"])
            self.assertTrue(r["text"].endswith(SIGNATURE))

    def test_sms_too_long_falls_back_to_email(self):
        with mock.patch.object(__import__(__name__), "SMS_MAX_LENGTH", 40):
            out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0))],
                                 _utc(2026, 10, 10, 12, 0))
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_pl_signature(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                    country="PL")], _utc(2026, 10, 10, 12, 0))
        for r in out:
            self.assertTrue(r["text"].endswith(SIGNATURE_PL))
            self.assertNotIn("Siobhán", r["text"])

    def test_sort_order_and_ties(self):
        now = _utc(2026, 10, 10, 12, 0)
        out = plan_reminders([
            _appt(id="b2", starts_at=_utc(2026, 10, 14, 14, 0)),
            _appt(id="a1", starts_at=_utc(2026, 10, 14, 14, 0)),
            _appt(id="c3", starts_at=_utc(2026, 10, 15, 14, 0)),
        ], now)
        keys = [(r["send_at"], r["appointment_id"]) for r in out]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([out[0]["appointment_id"], out[1]["appointment_id"]], ["a1", "b2"])

    def test_no_send_before_now(self):
        now = _utc(2026, 10, 13, 20, 30)
        for hours in (-1, 0, 1, 2, 3, 5, 24, 47, 49, 100):
            with self.subTest(hours=hours):
                starts = now + timedelta(hours=hours)
                for r in plan_reminders([_appt(starts_at=starts)], now):
                    self.assertGreaterEqual(r["send_at"], now)

    def test_logs_one_line_per_reminder_without_email(self):
        now = _utc(2026, 10, 10, 12, 0)
        with self.assertLogs("brennan_reminders", level="INFO") as cm:
            out = plan_reminders([_appt(starts_at=_utc(2026, 10, 14, 14, 0),
                                        optout_sms_v2=True)], now)
        self.assertEqual(len(cm.output), len(out))
        self.assertNotIn("mary@example.com", "\n".join(cm.output))
        for r in out:
            self.assertNotIn("mary@example.com", r["text"])

    def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 12, 0))


if __name__ == "__main__":
    unittest.main()