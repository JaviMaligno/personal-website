"""Appointment reminder planner for Brennan Opticians.

Entry point: plan_reminders(appointments, now).

Test results: not executed. This session had no way to run code, so the unit tests in this module are unverified. Run them with: python -m unittest <this module>

Defaults not confirmed by the client (flagged here and in code comments):
1. Date format in texts is "Wed 14 Oct 2026" (client did not specify).
2. Message wording is a draft template and needs client approval.
3. The signature contains accented characters, so SMS may need UCS-2 encoding. GSM-7 versus UCS-2 segment handling is open. The 160-character limit is applied as a plain Unicode character count, as specified.
4. Email has no subject field. Flagged rather than added.
5. Status matching is exact: only "cancelled" is excluded. "canceled" is an open question.
6. If both reminder points are past and the appointment has not started, one reminder is sent at now and labelled as the 2-hour reminder.
7. If only the 2-hour point is past, that reminder is dropped and the 48-hour reminder is sent at its own time.
8. Quiet-hours conflict, now outside quiet hours: if the quiet-hours move lands before now, send at now.
9. Quiet-hours conflict, now inside quiet hours: hold to the next 08:00 Dublin. If now is before 08:00, this is the same day. Otherwise it is the next day. The hold applies to any reminder whose adjusted time lands before now, not only the immediate one. The reminder is dropped if the appointment starts at or before the hold time.
10. If customer_name is empty, the greeting uses "there". For SMS, the first name is used when the full name does not fit.
11. Logging conflict: the house rule asks for the contact in each log line, but the privacy rule forbids logging email addresses and names. Logs record the appointment id, channel, and send time only. Support can trace deliveries by appointment id. Needs client confirmation.
12. An appointment whose start is at or before now produces no reminders.
13. Country "PL" is matched after strip and upper-case.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _present(value):
    return value is not None and str(value).strip() != ""


def _at(day, hour):
    # Build the wall-clock time in Dublin, then convert to a UTC instant.
    return datetime.combine(day, time(hour), tzinfo=DUBLIN).astimezone(UTC)


def _is_quiet(t_utc):
    # Quiet hours are 21:00 to 08:00 Dublin local; 08:00:00 exactly is allowed.
    clock = t_utc.astimezone(DUBLIN).time()
    return clock >= time(21) or clock < time(8)


def _quiet_adjust(t_utc):
    local = t_utc.astimezone(DUBLIN)
    if local.time() >= time(21):
        return _at(local.date(), 20)
    if local.time() < time(8):
        return _at(local.date() - timedelta(days=1), 20)
    return t_utc


def _next_0800(now_utc):
    # Client-unconfirmed: next 08:00 Dublin strictly after now.
    local = now_utc.astimezone(DUBLIN)
    if local.time() < time(8):
        day = local.date()
    else:
        day = local.date() + timedelta(days=1)
    return _at(day, 8)


def _place(target, now_utc, starts_utc):
    # Returns the send instant, or None if the appointment has started by then.
    t = _quiet_adjust(max(target, now_utc))
    if t < now_utc:
        # Client-unconfirmed quiet-hours default.
        t = _next_0800(now_utc) if _is_quiet(now_utc) else now_utc
    if t >= starts_utc:
        return None
    return t


def _pick_channel(appt):
    # Opt-out or no phone routes to email. Missing or null optout is false.
    if _present(appt.get("phone")) and not appt.get("optout_sms_v2"):
        return "sms", appt.get("phone")
    return "email", appt.get("email")


def _body(name, starts_local, sig):
    date = (f"{DAYS[starts_local.weekday()]} {starts_local.day} "
            f"{MONTHS[starts_local.month - 1]} {starts_local.year}")
    # Client-unconfirmed draft wording.
    return (f"Hi {name}, reminder of your Brennan Opticians appointment "
            f"on {date} at {starts_local:%H:%M} (Dublin time). {sig}")


def _text(appt_id, channel, name, starts_local, sig):
    parts = name.split()
    candidates = [name, parts[0]] if channel == "sms" else [name]
    for cand in candidates:
        text = _body(cand, starts_local, sig)
        if channel == "email" or len(text) <= SMS_LIMIT:
            return text
    raise ValueError(
        f"appointment {appt_id}: SMS text exceeds {SMS_LIMIT} characters "
        "even with first name only")


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    now_u = now.astimezone(UTC)
    for appt in appointments:
        if not _aware(appt["starts_at"]):
            raise ValueError(
                f"appointment {appt['id']}: starts_at must be timezone-aware")

    records = []
    for appt in appointments:
        # Client-unconfirmed: exact match only; "canceled" is not excluded.
        if appt.get("status") == "cancelled":
            continue
        starts = appt["starts_at"].astimezone(UTC)
        if starts <= now_u:
            continue
        channel, contact = _pick_channel(appt)
        if not _present(contact):
            continue

        appt_id = appt["id"]
        name = str(appt.get("customer_name") or "").strip() or "there"
        starts_local = starts.astimezone(DUBLIN)
        country = str(appt.get("country") or "").strip().upper()
        sig = SIG_PL if country == "PL" else SIG_DEFAULT

        t48 = starts - timedelta(hours=48)
        t2 = starts - timedelta(hours=2)
        if t2 < now_u:
            # Both past: single reminder at now, typed as the 2-hour one.
            # Client-unconfirmed.
            slots = [(1, now_u)] if t48 < now_u else [(0, t48)]
        else:
            slots = [(0, t48), (1, t2)]

        for idx, target in slots:
            send = _place(target, now_u, starts)
            if send is None:
                continue
            text = _text(appt_id, channel, name, starts_local, sig)
            records.append((send, str(appt_id), idx, appt_id, channel, text))
            # Privacy: appointment id, channel and time only. No name or contact.
            log.info("planned reminder: appointment=%s channel=%s send_at=%s",
                     appt_id, channel, send.isoformat())

    records.sort(key=lambda r: (r[0], r[1], r[2]))
    return [{"appointment_id": r[3], "channel": r[4],
             "send_at": r[0], "text": r[5]} for r in records]


class TestPlanReminders(unittest.TestCase):

    def appt(self, **kw):
        base = {"id": "a1", "customer_name": "Aoife Murphy",
                "email": "aoife@example.com", "phone": "+353860000000",
                "country": "IE", "status": "booked",
                "starts_at": None, "optout_sms_v2": False}
        base.update(kw)
        return base

    def test_2026_10_13_example(self):
        starts = datetime(2026, 10, 14, 7, 0, tzinfo=DUBLIN)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=DUBLIN)
        out = plan_reminders([self.appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [now, datetime(2026, 10, 13, 20, 0, tzinfo=DUBLIN)])
        self.assertEqual([r["channel"] for r in out], ["sms", "sms"])

    def test_2026_10_25_dst(self):
        starts = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)
        now = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
        out = plan_reminders([self.appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [datetime(2026, 10, 23, 11, 0, tzinfo=DUBLIN),
                          datetime(2026, 10, 25, 8, 0, tzinfo=UTC)])

    def test_cancelled_produces_nothing(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        out = plan_reminders([self.appt(starts_at=starts, status="cancelled")],
                             now)
        self.assertEqual(out, [])

    def test_optout_routes_to_email(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        out = plan_reminders([self.appt(starts_at=starts, optout_sms_v2=True)],
                             now)
        self.assertEqual([r["channel"] for r in out], ["email", "email"])

    def test_no_phone_routes_to_email_and_missing_email_skips(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        out = plan_reminders([self.appt(starts_at=starts, phone=None)], now)
        self.assertEqual([r["channel"] for r in out], ["email", "email"])
        out = plan_reminders(
            [self.appt(starts_at=starts, phone=None, email=None)], now)
        self.assertEqual(out, [])

    def test_sms_length_long_name_uses_first_name(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        out = plan_reminders(
            [self.appt(starts_at=starts, customer_name="Ann " + "Z" * 200)], now)
        for r in out:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("Ann", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_sms_length_accented_characters(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        out = plan_reminders(
            [self.appt(starts_at=starts, customer_name="Ní " + "Ó" * 150)], now)
        for r in out:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_sms_too_long_even_without_name_raises(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        with self.assertRaises(ValueError) as ctx:
            plan_reminders(
                [self.appt(id="a1", starts_at=starts, customer_name="Q" * 200)],
                now)
        self.assertIn("a1", str(ctx.exception))
        self.assertNotIn("aoife@example.com", str(ctx.exception))

    def test_naive_datetime_error_names_id_only(self):
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        with self.assertRaises(ValueError) as ctx:
            plan_reminders(
                [self.appt(id="a9", starts_at=datetime(2026, 10, 14, 7, 0))],
                now)
        msg = str(ctx.exception)
        self.assertIn("a9", msg)
        self.assertNotIn("Aoife", msg)
        self.assertNotIn("aoife@example.com", msg)

    def test_empty_list(self):
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        self.assertEqual(plan_reminders([], now), [])

    def test_sort_order_and_output_keys(self):
        starts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
        out = plan_reminders(
            [self.appt(id="b", starts_at=starts),
             self.appt(id="a", starts_at=starts)], now)
        self.assertEqual([r["appointment_id"] for r in out],
                         ["a", "b", "a", "b"])
        sends = [r["send_at"] for r in out]
        self.assertEqual(sends, sorted(sends))
        for r in out:
            self.assertEqual(set(r.keys()),
                             {"appointment_id", "channel", "send_at", "text"})


if __name__ == "__main__":
    unittest.main()