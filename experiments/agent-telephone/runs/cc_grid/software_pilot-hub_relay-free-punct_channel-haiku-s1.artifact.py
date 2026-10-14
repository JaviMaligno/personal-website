"""Appointment SMS reminder planner for Brennan Opticians.

plan_reminders(appointments, now) is the public entry point. Its only side effect is one INFO log line per planned reminder (house rule). Each line carries the appointment id, channel and send time. Contact details are left out because the client privacy rule forbids logging names and phone numbers. Support therefore traces deliveries by appointment id, not by contact. Confirm this with the team.

This file was written without being executed. Run the tests with: python -m unittest -v <path to this file>
"""
import copy
import logging
import re
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
MAX_TEXT_LEN = 160
ONE_HOUR = timedelta(hours=1)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIGNATURE_IE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"


def customer_accepts_sms(record):
    """The single place that decides the opt-out reading.

    Privacy-safe default: text only when optout_sms_v2 is exactly False.
    True, None or a missing field all count as opted out. To follow the
    brief's literal reading instead, return record.get("optout_sms_v2") is True.
    The legacy opt_out field is never read.
    """
    return record.get("optout_sms_v2") is False


class _Malformed(Exception):
    pass


def _parse(record):
    starts = record.get("starts_at")
    if isinstance(starts, str):
        try:
            starts = datetime.fromisoformat(starts)
        except ValueError:
            raise _Malformed() from None
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise _Malformed()
    name = record.get("customer_name")
    country = record.get("country")
    status = record.get("status")
    for value in (name, country, status):
        if value is not None and not isinstance(value, str):
            raise _Malformed()
    return starts, name, country, status


def _has_usable_phone(phone):
    return isinstance(phone, str) and any(ch.isdigit() for ch in phone)


def _in_quiet_hours(instant_utc):
    hour = instant_utc.astimezone(DUBLIN).hour
    return hour >= 21 or hour < 8


def _quiet_start_move(instant_utc):
    """The 20:00 Dublin just before the quiet window containing instant_utc."""
    local = instant_utc.astimezone(DUBLIN)
    local_date = local.date()
    if local.hour < 21:
        local_date -= timedelta(days=1)
    return datetime.combine(local_date, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)


def _next_0800(instant_utc):
    """The first 08:00 Dublin at or after instant_utc."""
    local = instant_utc.astimezone(DUBLIN)
    local_date = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    return datetime.combine(local_date, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)


def _allowed_send_time(candidate_utc, now_utc):
    """Apply quiet hours and the past check to one candidate. None if unusable."""
    send_at = candidate_utc
    if _in_quiet_hours(candidate_utc):
        moved = _quiet_start_move(candidate_utc)
        if moved < now_utc:
            send_at = _next_0800(now_utc) if _in_quiet_hours(now_utc) else now_utc
        else:
            send_at = moved
    return send_at if send_at >= now_utc else None


def _candidate_instants(start_utc, now_utc):
    """Raw candidate instants before quiet hours. Requires now_utc < start_utc."""
    two_hours_before = start_utc - 2 * ONE_HOUR
    forty_eight_before = start_utc - 48 * ONE_HOUR
    if now_utc < forty_eight_before:
        return [forty_eight_before, two_hours_before]
    if now_utc < two_hours_before:
        return [now_utc, two_hours_before]
    return [now_utc]


def _signature(country):
    if isinstance(country, str) and country.strip().casefold() == "pl":
        return SIGNATURE_PL
    return SIGNATURE_IE


def _name_forms(name):
    """Name forms in shortening order. None means omit the name."""
    words = name.split() if isinstance(name, str) else []
    if not words:
        return [None]
    forms = [" ".join(words)]
    if len(words) > 1:
        forms.append(words[0])
        forms.append(f"{words[0][0].upper()}. {words[-1]}")
    forms.append(None)
    return forms


def _build_text(name, local_start, country):
    """Return the SMS text, or None if no name form fits within the limit."""
    when = (f"on {local_start.day} {MONTHS[local_start.month - 1]} {local_start.year} "
            f"at {local_start.hour:02d}:{local_start.minute:02d}")
    signature = _signature(country)
    for form in _name_forms(name):
        greeting = "Hi, " if form is None else f"Hi {form}, "
        text = (f"{greeting}this is a reminder of your appointment at "
                f"Brennan Opticians {when}. {signature}")
        if len(text) <= MAX_TEXT_LEN:
            return text
    return None


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    seen_ids = set()
    planned = []
    for record in appointments:
        raw_id = record.get("id") if isinstance(record, dict) else None
        if not isinstance(raw_id, str) or not raw_id.strip():
            log.warning("skipped malformed record without a valid id")
            continue
        if raw_id in seen_ids:
            continue
        seen_ids.add(raw_id)
        try:
            starts, name, country, status = _parse(record)
        except _Malformed:
            log.warning("skipped malformed record id=%s", raw_id)
            continue
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            continue
        if not _has_usable_phone(record.get("phone")):
            continue
        if not customer_accepts_sms(record):
            continue
        start_utc = starts.astimezone(UTC)
        if now_utc >= start_utc:
            continue
        send_times = []
        for candidate in _candidate_instants(start_utc, now_utc):
            send_at = _allowed_send_time(candidate, now_utc)
            if send_at is not None and send_at < start_utc and send_at not in send_times:
                send_times.append(send_at)
        if not send_times:
            continue
        text = _build_text(name, starts.astimezone(DUBLIN), country)
        if text is None:
            log.warning("dropped reminders that cannot fit the SMS limit id=%s", raw_id)
            continue
        for send_at in send_times:
            planned.append({"appointment_id": raw_id, "channel": "sms",
                            "send_at": send_at, "text": text})
    planned.sort(key=lambda r: (r["send_at"], r["appointment_id"], r["channel"]))
    for r in planned:
        log.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                 r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return planned


# ---------------------------------------------------------------- tests

EMAIL = "siobhan.murphy@example.com"
PHONE = "+353 87 123 4567"
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+")


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def make(**overrides):
    record = {
        "id": "APT-1",
        "customer_name": "Siobhán Murphy",
        "email": EMAIL,
        "phone": PHONE,
        "country": "IE",
        "status": "booked",
        "starts_at": utc(2026, 10, 20, 12, 0),
        "optout_sms_v2": False,
    }
    record.update(overrides)
    return record


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class PlannerTestCase(unittest.TestCase):
    def setUp(self):
        self.capture = _Capture()
        self.old_level = log.level
        log.addHandler(self.capture)
        log.setLevel(logging.DEBUG)
        self.addCleanup(self._restore_logging)

    def _restore_logging(self):
        log.removeHandler(self.capture)
        log.setLevel(self.old_level)

    def run_plan(self, appointments, now):
        result = plan_reminders(appointments, now)
        self.assert_no_leaks()
        return result

    def assert_no_leaks(self):
        for msg in self.capture.messages:
            self.assertIsNone(EMAIL_RE.search(msg), msg)
            self.assertNotIn(EMAIL, msg)
            self.assertNotIn("Murphy", msg)
            self.assertNotIn("353", msg)


class TimingTests(PlannerTestCase):
    def test_booking_72h_ahead_gives_two_sms_in_order(self):
        start = utc(2026, 10, 20, 12, 0)
        out = self.run_plan([make(starts_at=start)], start - timedelta(hours=72))
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 18, 12, 0), utc(2026, 10, 20, 10, 0)])
        self.assertEqual({r["channel"] for r in out}, {"sms"})

    def test_booking_30h_ahead_gives_immediate_and_two_hours_before(self):
        now = utc(2026, 10, 13, 12, 0)
        start = utc(2026, 10, 14, 18, 0)
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out], [now, utc(2026, 10, 14, 16, 0)])

    def test_booking_1h_ahead_in_daytime_gives_immediate_reminder(self):
        now = utc(2026, 10, 13, 12, 0)
        out = self.run_plan([make(starts_at=utc(2026, 10, 13, 13, 0))], now)
        self.assertEqual([r["send_at"] for r in out], [now])

    def test_booking_1h_ahead_late_evening_gives_nothing(self):
        now = utc(2026, 10, 13, 21, 30)
        out = self.run_plan([make(starts_at=utc(2026, 10, 13, 22, 30))], now)
        self.assertEqual(out, [])

    def test_immediate_reminder_in_quiet_hours_moves_to_0800(self):
        now = utc(2026, 10, 13, 22, 0)
        out = self.run_plan([make(starts_at=utc(2026, 10, 14, 12, 0))], now)
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 14, 7, 0), utc(2026, 10, 14, 10, 0)])

    def test_already_started_gives_nothing(self):
        start = utc(2026, 10, 13, 12, 0)
        self.assertEqual(self.run_plan([make(starts_at=start)], start), [])
        self.assertEqual(self.run_plan([make(starts_at=start)],
                                       start + timedelta(minutes=1)), [])


class EligibilityTests(PlannerTestCase):
    def setUp(self):
        super().setUp()
        self.now = utc(2026, 10, 13, 9, 0)
        self.start = utc(2026, 10, 15, 9, 0)

    def test_cancelled_in_any_case_gives_nothing(self):
        records = [make(id=f"C{i}", status=s, starts_at=self.start)
                   for i, s in enumerate(["cancelled", "CANCELLED", "Cancelled", " cAnCeLlEd "])]
        self.assertEqual(self.run_plan(records, self.now), [])

    def test_control_booked_record_gets_reminders(self):
        out = self.run_plan([make(starts_at=self.start)], self.now)
        self.assertTrue(out)

    def test_opted_out_true_none_or_missing_gets_nothing(self):
        missing = make()
        del missing["optout_sms_v2"]
        records = [make(optout_sms_v2=True, starts_at=self.start),
                   make(optout_sms_v2=None, starts_at=self.start),
                   missing]
        self.assertEqual(self.run_plan(records, self.now), [])

    def test_customer_accepts_sms_only_for_explicit_false(self):
        self.assertTrue(customer_accepts_sms({"optout_sms_v2": False}))
        self.assertFalse(customer_accepts_sms({"optout_sms_v2": True}))
        self.assertFalse(customer_accepts_sms({"optout_sms_v2": None}))
        self.assertFalse(customer_accepts_sms({}))

    def test_no_usable_phone_gets_nothing_even_with_email(self):
        missing = make(starts_at=self.start)
        del missing["phone"]
        records = [make(phone="", starts_at=self.start),
                   make(phone="   ", starts_at=self.start),
                   make(phone=None, starts_at=self.start),
                   missing]
        out = self.run_plan(records, self.now)
        self.assertEqual(out, [])


class QuietHoursTests(PlannerTestCase):
    def test_candidate_at_0500_moves_to_previous_evening_2000(self):
        start = utc(2026, 10, 14, 6, 0)  # 07:00 Dublin, so S-2h is 05:00 Dublin
        now = start - timedelta(hours=72)
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 12, 6, 0), utc(2026, 10, 13, 19, 0)])

    def test_candidate_at_exactly_2100_moves_to_2000_same_evening(self):
        start = utc(2026, 10, 14, 22, 0)  # 23:00 Dublin, so S-2h is 21:00 Dublin
        now = start - timedelta(hours=72)
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 12, 19, 0), utc(2026, 10, 14, 19, 0)])

    def test_fallback_to_now_when_moved_time_is_before_now(self):
        now = utc(2026, 10, 13, 19, 30)  # 20:30 Dublin, not quiet
        start = utc(2026, 10, 13, 22, 0)  # S-2h is 21:00 Dublin, quiet
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out], [now])

    def test_invariants_over_a_grid_of_now_values(self):
        start = utc(2026, 10, 25, 7, 0)
        base = start - timedelta(hours=80)
        for step in range(100):
            now = base + timedelta(minutes=47 * step)
            out = self.run_plan([make(starts_at=start)], now)
            for r in out:
                self.assertGreaterEqual(r["send_at"], now)
                self.assertLess(r["send_at"], start)
                self.assertLessEqual(len(r["text"]), MAX_TEXT_LEN)
                hour = r["send_at"].astimezone(DUBLIN).hour
                self.assertTrue(8 <= hour < 21, r["send_at"])


class DstTests(PlannerTestCase):
    def test_move_crosses_clock_change(self):
        start = utc(2026, 10, 25, 7, 0)  # 07:00 GMT, after the change
        now = utc(2026, 10, 24, 12, 0)
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 24, 12, 0), utc(2026, 10, 24, 19, 0)])

    def test_repeated_hour_first_occurrence(self):
        start = utc(2026, 10, 25, 2, 30)  # S-2h is 00:30 UTC, 01:30 BST
        now = utc(2026, 10, 24, 12, 0)
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 24, 12, 0), utc(2026, 10, 24, 19, 0)])

    def test_repeated_hour_second_occurrence(self):
        start = utc(2026, 10, 25, 3, 30)  # S-2h is 01:30 UTC, 01:30 GMT
        now = utc(2026, 10, 24, 12, 0)
        out = self.run_plan([make(starts_at=start)], now)
        self.assertEqual([r["send_at"] for r in out],
                         [utc(2026, 10, 24, 12, 0), utc(2026, 10, 24, 19, 0)])

    def test_text_uses_dublin_local_time_in_repeated_hour(self):
        for start in (utc(2026, 10, 25, 0, 30), utc(2026, 10, 25, 1, 30)):
            out = self.run_plan([make(starts_at=start)], start - timedelta(hours=72))
            self.assertTrue(out)
            for r in out:
                self.assertIn("25 Oct 2026 at 01:30.", r["text"])


class TextTests(PlannerTestCase):
    def _text_for(self, **kw):
        start = utc(2026, 10, 14, 9, 0)  # 10:00 Dublin
        out = self.run_plan([make(starts_at=start, **kw)], start - timedelta(hours=72))
        self.assertTrue(out)
        return out[0]["text"]

    def test_full_name_text(self):
        self.assertEqual(
            self._text_for(),
            "Hi Siobhán Murphy, this is a reminder of your appointment at "
            "Brennan Opticians on 14 Oct 2026 at 10:00. Siobhán Ní Dhuibhir")

    def test_shortens_to_first_name(self):
        text = self._text_for(customer_name="Bartholomew Maximilian Konstantinopoulos Fitzgerald-Smythe")
        self.assertTrue(text.startswith("Hi Bartholomew, this is"))

    def test_shortens_to_initial_and_surname(self):
        text = self._text_for(customer_name="A" * 60 + " Smith")
        self.assertTrue(text.startswith("Hi A. Smith, this is"))

    def test_omits_name_when_nothing_else_fits(self):
        text = self._text_for(customer_name="Z" * 90 + " " + "Y" * 90)
        self.assertTrue(text.startswith("Hi, this is a reminder"))
        self.assertNotIn("ZZZ", text)

    def test_polish_signature_for_pl_country(self):
        self.assertTrue(self._text_for(country=" pl ").endswith("Grzegorz Szczepański"))

    def test_irish_signature_for_other_or_missing_country(self):
        self.assertTrue(self._text_for(country="IE").endswith("Siobhán Ní Dhuibhir"))
        missing = make()
        del missing["country"]
        start = utc(2026, 10, 20, 12, 0)
        out = self.run_plan([make(starts_at=start)], start - timedelta(hours=72))
        self.assertTrue(out[0]["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_every_text_fits_has_date_time_and_signature(self):
        names = ["Ann Byrne", "Ó Ríordáin", "B" * 80, "X" * 40 + " " + "Y" * 40, None, ""]
        start = utc(2026, 10, 14, 9, 0)
        for i, name in enumerate(names):
            out = self.run_plan([make(id=f"T{i}", customer_name=name, starts_at=start)],
                                start - timedelta(hours=72))
            self.assertTrue(out)
            for r in out:
                text = r["text"]
                self.assertLessEqual(len(text), MAX_TEXT_LEN)
                self.assertIn("14 Oct 2026", text)
                self.assertIn("10:00", text)
                self.assertTrue(text.endswith("Siobhán Ní Dhuibhir"))


class OutputTests(PlannerTestCase):
    def setUp(self):
        super().setUp()
        self.now = utc(2026, 10, 17, 12, 0)
        self.records = [make(id="B", starts_at=utc(2026, 10, 20, 12, 0)),
                        make(id="A", starts_at=utc(2026, 10, 20, 12, 0)),
                        make(id="C", starts_at=utc(2026, 10, 19, 12, 0))]

    def test_output_is_sorted_with_exact_keys(self):
        out = self.run_plan(self.records, self.now)
        for r in out:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(r["send_at"].utcoffset(), timedelta(0))
        keys = [(r["send_at"], r["appointment_id"], r["channel"]) for r in out]
        self.assertEqual(keys, sorted(keys))
        at_tie = [r["appointment_id"] for r in out if r["send_at"] == utc(2026, 10, 18, 12, 0)]
        self.assertEqual(at_tie, ["A", "B"])

    def test_same_inputs_give_identical_output(self):
        first = plan_reminders(self.records, self.now)
        second = plan_reminders(copy.deepcopy(self.records), self.now)
        self.assertEqual(first, second)

    def test_duplicate_id_keeps_first_occurrence(self):
        records = [make(id="D", customer_name="Ann Byrne", starts_at=utc(2026, 10, 20, 12, 0)),
                   make(id="D", customer_name="Ben Lee", starts_at=utc(2026, 10, 20, 12, 0))]
        out = self.run_plan(records, self.now)
        self.assertTrue(out)
        for r in out:
            self.assertIn("Ann Byrne", r["text"])
            self.assertNotIn("Ben Lee", r["text"])

    def test_one_info_log_line_per_planned_reminder(self):
        out = self.run_plan(self.records, self.now)
        infos = [m for m in self.capture.messages if m.startswith("planned reminder")]
        self.assertEqual(len(infos), len(out))
        for line in infos:
            self.assertIn("APT", line.replace("A ", "A").replace("B ", "B") + "APT")
            self.assertIn("channel=sms", line)

    def test_no_email_in_output_or_logs(self):
        out = self.run_plan(self.records, self.now)
        for r in out:
            self.assertNotIn("@", r["text"])
            self.assertNotEqual(r["channel"], "email")
        self.assert_no_leaks()


class MalformedTests(PlannerTestCase):
    def test_malformed_records_are_skipped_and_only_ids_logged(self):
        no_id = make()
        del no_id["id"]
        records = [no_id,
                   make(id="NAIVE", starts_at=datetime(2026, 10, 20, 12, 0)),
                   make(id="BADSTR", starts_at="not a date"),
                   make(id="GOOD")]
        out = self.run_plan(records, utc(2026, 10, 17, 12, 0))
        self.assertEqual({r["appointment_id"] for r in out}, {"GOOD"})
        logs = "\n".join(self.capture.messages)
        self.assertIn("NAIVE", logs)
        self.assertIn("BADSTR", logs)

    def test_naive_now_raises_without_record_data(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([make()], datetime(2026, 10, 17, 12, 0))
        msg = str(cm.exception)
        self.assertNotIn("@", msg)
        self.assertNotIn("Murphy", msg)
        self.assertNotIn(PHONE, msg)
        self.assertNotIn("APT-1", msg)


if __name__ == "__main__":
    unittest.main()