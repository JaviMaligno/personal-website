# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-4i2m3810/reminders_planner.py
"""Appointment reminder planner for Brennan Opticians (standard library only).

Open questions and choices for client confirmation:
1. 48h slot, quiet-adjusted candidate before now while now is outside quiet
   hours: ASSUMPTION, the candidate becomes now (see plan_48h_send_time).
2. An empty or whitespace-only customer_name raises ValueError.
3. A country that is neither None nor a str raises ValueError.
4. Mixed int and str ids sort with all ints before all strs, ints by value
   and strs by value (see id_sort_key).
5. The no-name SMS wording is a proposal. With the fixed template and a
   160-character limit the no-name branch is unreachable for real names;
   tests reach it through the limit parameter of render_sms_with_name.
6. optout_sms_v2 missing or None counts as opted out, so email is used.
7. The house rule asks for an INFO line per reminder with channel and contact.
   The spec forbids logging customer contact data, so the INFO line carries
   the appointment id and channel only. This departs from the house rule and
   needs sign-off.
"""

import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

SMS_LIMIT = 160
ELLIPSIS = "\u2026"
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
EVENING_SEND_HOUR = 20
MORNING_SEND_HOUR = 8
OFFSET_48H = timedelta(hours=48)
OFFSET_2H = timedelta(hours=2)
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

SIGNATURE_IE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
TEMPLATE_NAMED = (
    "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {time}. {signature}"
)
TEMPLATE_NO_NAME = (
    "Reminder of your Brennan Opticians appointment on {date} at {time}. {signature}"
)


def is_nonblank_str(value):
    return isinstance(value, str) and value.strip() != ""


def is_aware_datetime(value):
    return isinstance(value, datetime) and value.utcoffset() is not None


def validate_now(now):
    if not is_aware_datetime(now):
        raise ValueError("now must be a timezone-aware datetime")


def validate_appointment(appt):
    if not isinstance(appt, dict):
        raise ValueError("each appointment must be a dict")
    for key in ("id", "customer_name", "status", "starts_at"):
        if appt.get(key) is None:
            raise ValueError(f"field {key} is required and must not be None")
    if isinstance(appt["id"], bool) or not isinstance(appt["id"], (str, int)):
        raise ValueError("field id must be a str or int")
    if not is_nonblank_str(appt["customer_name"]):
        raise ValueError("field customer_name must be a non-empty string")
    if not isinstance(appt["status"], str):
        raise ValueError("field status must be a string")
    if not is_aware_datetime(appt["starts_at"]):
        raise ValueError("field starts_at must be a timezone-aware datetime")
    for key in ("email", "phone", "country"):
        value = appt.get(key)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"field {key} must be a string or None")
    opt_out = appt.get("optout_sms_v2")
    if opt_out is not None and not isinstance(opt_out, bool):
        raise ValueError("field optout_sms_v2 must be a bool or None")


def is_excluded_status(status):
    return status.strip().lower() == "cancelled"


def select_channel(appt):
    if is_nonblank_str(appt.get("phone")) and appt.get("optout_sms_v2") is False:
        return "sms"
    if is_nonblank_str(appt.get("email")):
        return "email"
    return None


def is_quiet(instant):
    hour = instant.astimezone(DUBLIN).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def quiet_adjust(instant):
    """Move a quiet-hours instant to 20:00 Dublin; other instants are unchanged."""
    local = instant.astimezone(DUBLIN)
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    elif local.hour < QUIET_END_HOUR:
        day = local.date() - timedelta(days=1)
    else:
        return instant
    evening = datetime(day.year, day.month, day.day, EVENING_SEND_HOUR, tzinfo=DUBLIN)
    return evening.astimezone(UTC)


def next_morning_send(now):
    """First 08:00 Dublin local instant strictly after now, as UTC."""
    day = now.astimezone(DUBLIN).date()
    while True:
        candidate = datetime(
            day.year, day.month, day.day, MORNING_SEND_HOUR, tzinfo=DUBLIN
        ).astimezone(UTC)
        if candidate > now:
            return candidate
        day += timedelta(days=1)


def plan_48h_send_time(starts_at, now):
    target = starts_at - OFFSET_48H
    if target < now:
        candidate = next_morning_send(now) if is_quiet(now) else now
    else:
        candidate = quiet_adjust(target)
    if candidate < now:
        # ASSUMPTION (to confirm with client): the quiet-adjusted 20:00 point has
        # already passed while now is outside quiet hours, so send at now.
        candidate = next_morning_send(now) if is_quiet(now) else now
    return candidate


def plan_2h_send_time(starts_at, now):
    target = starts_at - OFFSET_2H
    if target < now:
        return None
    candidate = quiet_adjust(target)
    if candidate < now:
        return None
    return candidate


def keep_if_before_start(send_at, starts_at):
    return send_at is not None and send_at < starts_at


def format_local_date_time(starts_at_utc):
    local = starts_at_utc.astimezone(DUBLIN)
    date_s = f"{local.day:02d}/{local.month:02d}/{local.year:04d}"
    time_s = f"{local.hour:02d}:{local.minute:02d}"
    return date_s, time_s


def signature_for(country):
    if isinstance(country, str) and country.strip().lower() == "pl":
        return SIGNATURE_PL
    return SIGNATURE_IE


def normalise_name(name):
    return unicodedata.normalize("NFC", name.strip())


def render_sms_with_name(name, date_s, time_s, signature, limit=SMS_LIMIT):
    full = TEMPLATE_NAMED.format(name=name, date=date_s, time=time_s, signature=signature)
    if len(full) <= limit:
        return full
    for k in range(len(name) - 1, 0, -1):
        shortened = name[:k].rstrip() + ELLIPSIS
        text = TEMPLATE_NAMED.format(
            name=shortened, date=date_s, time=time_s, signature=signature
        )
        if len(text) <= limit:
            return text
    no_name = TEMPLATE_NO_NAME.format(date=date_s, time=time_s, signature=signature)
    if len(no_name) > limit:
        raise ValueError("reminder text cannot fit within the SMS limit")
    return no_name


def build_text(name, country, starts_at_utc, channel):
    date_s, time_s = format_local_date_time(starts_at_utc)
    signature = signature_for(country)
    clean_name = normalise_name(name)
    if channel == "sms":
        return render_sms_with_name(clean_name, date_s, time_s, signature)
    return TEMPLATE_NAMED.format(name=clean_name, date=date_s, time=time_s, signature=signature)


def plan_for_appointment(appt, now):
    if is_excluded_status(appt["status"]):
        return []
    starts_at = appt["starts_at"].astimezone(UTC)
    if starts_at <= now:
        return []
    channel = select_channel(appt)
    if channel is None:
        return []
    text = build_text(appt["customer_name"], appt.get("country"), starts_at, channel)
    slots = (plan_48h_send_time(starts_at, now), plan_2h_send_time(starts_at, now))
    return [
        {"appointment_id": appt["id"], "channel": channel, "send_at": send_at, "text": text}
        for send_at in slots
        if keep_if_before_start(send_at, starts_at)
    ]


def id_sort_key(value):
    if isinstance(value, int):
        return (0, value, "")
    return (1, 0, value)


def sort_key(reminder):
    return (
        reminder["send_at"],
        id_sort_key(reminder["appointment_id"]),
        reminder["channel"],
    )


def log_reminder(reminder):
    logger.info(
        "planned reminder appointment_id=%s channel=%s send_at=%s",
        reminder["appointment_id"],
        reminder["channel"],
        reminder["send_at"].isoformat(),
    )


def plan_reminders(appointments, now):
    validate_now(now)
    if not isinstance(appointments, (list, tuple)):
        raise ValueError("appointments must be a list or tuple")
    for appt in appointments:
        validate_appointment(appt)
    now_utc = now.astimezone(UTC)
    reminders = []
    for appt in appointments:
        reminders.extend(plan_for_appointment(appt, now_utc))
    reminders.sort(key=sort_key)
    for reminder in reminders:
        log_reminder(reminder)
    logger.debug("planned %d reminders from %d appointments", len(reminders), len(appointments))
    return reminders

# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-4i2m3810/test_reminders_planner.py
"""Unit tests for reminders_planner (stdlib unittest only).

Authored in a session without file-system or interpreter access, so these
tests have not been executed. Run with:
    python3 -I -m unittest discover -s <absolute dir> -p test_reminders_planner.py
"""

import copy
import os
import sys
import time
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import reminders_planner as rp  # noqa: E402

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")
EMAIL = "secret.person@example.test"
PHONE = "+353851234567"
NOW = datetime(2026, 6, 8, 9, 0, tzinfo=UTC)
D = "10/06/2026"
T = "14:00"
SIG = rp.SIGNATURE_IE


def dublin(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=DUBLIN).astimezone(UTC)


def utc(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=UTC)


def make_appt(**overrides):
    appt = {
        "id": 1,
        "customer_name": "Anna Murphy",
        "email": EMAIL,
        "phone": PHONE,
        "country": "IE",
        "status": "booked",
        "starts_at": dublin(2026, 6, 10, 14, 0),
        "optout_sms_v2": False,
    }
    appt.update(overrides)
    return appt


def run(appts, now=NOW):
    return rp.plan_reminders(appts, now)


def sends(result):
    return [r["send_at"] for r in result]


def channels(result):
    return {r["channel"] for r in result}


def _base_len():
    return len(rp.TEMPLATE_NAMED.format(name="", date=D, time=T, signature=SIG))


class QuietAdjustTests(unittest.TestCase):
    def test_21_00_moves_to_20_00_same_date(self):
        x = dublin(2026, 6, 10, 21, 0)
        self.assertTrue(rp.is_quiet(x))
        self.assertEqual(rp.quiet_adjust(x), dublin(2026, 6, 10, 20, 0))

    def test_20_59_not_moved(self):
        x = dublin(2026, 6, 10, 20, 59)
        self.assertFalse(rp.is_quiet(x))
        self.assertEqual(rp.quiet_adjust(x), x)

    def test_08_00_allowed(self):
        x = dublin(2026, 6, 10, 8, 0)
        self.assertFalse(rp.is_quiet(x))
        self.assertEqual(rp.quiet_adjust(x), x)

    def test_07_59_moves_to_20_00_previous_date(self):
        x = dublin(2026, 6, 10, 7, 59)
        self.assertTrue(rp.is_quiet(x))
        self.assertEqual(rp.quiet_adjust(x), dublin(2026, 6, 9, 20, 0))


class DstTests(unittest.TestCase):
    def test_spring_forward_48h_is_absolute(self):
        starts = datetime(2026, 3, 30, 9, 0, tzinfo=DUBLIN)
        self.assertEqual(starts.astimezone(UTC) - rp.OFFSET_48H, utc(2026, 3, 28, 8, 0))
        result = run([make_appt(starts_at=starts)], now=utc(2026, 3, 27, 12, 0))
        self.assertEqual(sends(result), [utc(2026, 3, 28, 8, 0), utc(2026, 3, 30, 6, 0)])

    def test_fall_back_ambiguous_instants_move_to_previous_evening(self):
        for instant in (utc(2026, 10, 25, 0, 30), utc(2026, 10, 25, 1, 30)):
            with self.subTest(instant=instant):
                self.assertTrue(rp.is_quiet(instant))
                self.assertEqual(rp.quiet_adjust(instant), utc(2026, 10, 24, 19, 0))

    def test_results_independent_of_process_timezone(self):
        if not hasattr(time, "tzset"):
            self.skipTest("time.tzset not available")
        appts = [
            make_appt(id=1, starts_at=datetime(2026, 3, 30, 9, 0, tzinfo=DUBLIN)),
            make_appt(
                id=2,
                starts_at=datetime(2026, 10, 26, 7, 30, tzinfo=DUBLIN),
                phone=None,
            ),
        ]
        now = utc(2026, 3, 27, 12, 0)
        original = os.environ.get("TZ")
        outputs = {}
        try:
            for zone in ("UTC", "America/New_York", "Europe/Dublin"):
                os.environ["TZ"] = zone
                time.tzset()
                outputs[zone] = run(appts, now)
        finally:
            if original is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original
            time.tzset()
        self.assertTrue(outputs["UTC"])
        self.assertEqual(outputs["UTC"], outputs["America/New_York"])
        self.assertEqual(outputs["UTC"], outputs["Europe/Dublin"])


class FortyEightHourTests(unittest.TestCase):
    def test_passed_target_outside_quiet_sends_now(self):
        now = dublin(2026, 6, 9, 13, 0)
        result = run([make_appt()], now=now)
        self.assertEqual(sends(result), [now, utc(2026, 6, 10, 10, 0)])

    def test_passed_target_in_quiet_hours_sends_next_morning(self):
        now = dublin(2026, 6, 9, 23, 30)
        result = run([make_appt()], now=now)
        self.assertEqual(sends(result), [dublin(2026, 6, 10, 8, 0), utc(2026, 6, 10, 10, 0)])

    def test_passed_target_in_quiet_hours_drops_when_morning_is_after_start(self):
        now = dublin(2026, 6, 9, 23, 30)
        appt = make_appt(starts_at=dublin(2026, 6, 10, 7, 30))
        self.assertEqual(run([appt], now=now), [])

    def test_assumption_candidate_before_now_outside_quiet_sends_now(self):
        # ASSUMPTION under test: the quiet-adjusted 20:00 point has already
        # passed while now is outside quiet hours, so the 48h send is now.
        now = dublin(2026, 6, 9, 20, 30)
        target = dublin(2026, 6, 9, 21, 15)
        starts = target + rp.OFFSET_48H
        result = run([make_appt(starts_at=starts)], now=now)
        self.assertEqual(sends(result)[0], now)

    def test_two_hour_passed_drops_only_two_hour_reminder(self):
        now = utc(2026, 6, 10, 10, 0)
        starts = utc(2026, 6, 10, 11, 0)
        result = run([make_appt(starts_at=starts)], now=now)
        self.assertEqual(sends(result), [now])


class EdgeTests(unittest.TestCase):
    def test_starts_at_or_before_now_gives_nothing(self):
        self.assertEqual(run([make_appt(starts_at=NOW)]), [])
        self.assertEqual(run([make_appt(starts_at=NOW - timedelta(hours=1))]), [])

    def test_now_equal_to_48h_send_is_allowed(self):
        now = dublin(2026, 6, 9, 13, 0)
        self.assertIn(now, sends(run([make_appt()], now=now)))

    def test_now_equal_to_2h_send_is_allowed(self):
        now = utc(2026, 6, 10, 9, 0)
        starts = now + timedelta(hours=2)
        self.assertIn(now, sends(run([make_appt(starts_at=starts)], now=now)))

    def test_reminder_at_or_after_start_is_dropped(self):
        now = dublin(2026, 6, 9, 23, 30)
        starts = dublin(2026, 6, 10, 8, 0)
        self.assertEqual(run([make_appt(starts_at=starts)], now=now), [])

    def test_empty_list_returns_empty(self):
        self.assertEqual(run([]), [])


class ChannelTests(unittest.TestCase):
    def test_phone_and_optout_false_uses_sms(self):
        self.assertEqual(channels(run([make_appt()])), {"sms"})

    def test_optout_true_uses_email(self):
        self.assertEqual(channels(run([make_appt(optout_sms_v2=True)])), {"email"})

    def test_optout_none_uses_email(self):
        self.assertEqual(channels(run([make_appt(optout_sms_v2=None)])), {"email"})

    def test_optout_missing_uses_email(self):
        appt = make_appt()
        del appt["optout_sms_v2"]
        self.assertEqual(channels(run([appt])), {"email"})

    def test_no_phone_uses_email(self):
        self.assertEqual(channels(run([make_appt(phone=None)])), {"email"})

    def test_whitespace_phone_uses_email(self):
        self.assertEqual(channels(run([make_appt(phone="   ")])), {"email"})

    def test_no_phone_and_no_email_gives_nothing(self):
        self.assertEqual(run([make_appt(phone=None, email=None)]), [])

    def test_legacy_opt_out_field_is_ignored(self):
        appt = make_appt(optout_sms_v2=None, opt_out=False)
        self.assertEqual(channels(run([appt])), {"email"})
        appt = make_appt(optout_sms_v2=False, opt_out="not a bool")
        self.assertEqual(channels(run([appt])), {"sms"})

    def test_empty_email_with_optout_gives_nothing(self):
        self.assertEqual(run([make_appt(optout_sms_v2=True, email="   ")]), [])


class CancelledTests(unittest.TestCase):
    def test_cancelled_statuses_produce_nothing(self):
        for status in ("cancelled", " CANCELLED ", "Cancelled"):
            with self.subTest(status=status):
                self.assertEqual(run([make_appt(status=status)]), [])

    def test_other_statuses_proceed(self):
        for status in ("booked", "Confirmed", "no-show"):
            with self.subTest(status=status):
                self.assertTrue(run([make_appt(status=status)]))

    def test_cancelled_appointments_are_still_validated(self):
        with self.assertRaises(ValueError):
            run([make_appt(status="cancelled", starts_at="2026-06-10")])


class TextTests(unittest.TestCase):
    def test_exactly_160_is_not_shortened(self):
        name = "A" * (160 - _base_len())
        text = rp.render_sms_with_name(name, D, T, SIG)
        self.assertEqual(len(text), 160)
        self.assertEqual(text, rp.TEMPLATE_NAMED.format(name=name, date=D, time=T, signature=SIG))
        self.assertNotIn(rp.ELLIPSIS, text)

    def test_161_is_shortened_to_at_most_160_ending_with_ellipsis(self):
        length = 161 - _base_len()
        text = rp.render_sms_with_name("A" * length, D, T, SIG)
        expected_name = "A" * (length - 2) + rp.ELLIPSIS
        self.assertEqual(
            text, rp.TEMPLATE_NAMED.format(name=expected_name, date=D, time=T, signature=SIG)
        )
        self.assertLessEqual(len(text), 160)
        self.assertIn(rp.ELLIPSIS + ", reminder", text)

    def test_name_that_cannot_fit_uses_no_name_variant(self):
        no_name = rp.TEMPLATE_NO_NAME.format(date=D, time=T, signature=SIG)
        text = rp.render_sms_with_name("Anna", D, T, SIG, limit=len(no_name))
        self.assertEqual(text, no_name)

    def test_no_name_variant_over_limit_raises_without_customer_data(self):
        with self.assertRaises(ValueError) as ctx:
            rp.render_sms_with_name("Anna", D, T, SIG, limit=10)
        self.assertNotIn("Anna", str(ctx.exception))

    def test_accented_characters_count_as_one_each(self):
        name = "é" * (160 - _base_len())
        text = rp.render_sms_with_name(name, D, T, SIG)
        self.assertEqual(len(text), 160)
        self.assertNotIn(rp.ELLIPSIS, text)

    def test_nfd_name_counts_like_nfc(self):
        nfc = unicodedata.normalize("NFC", "é" * (160 - _base_len()))
        nfd = unicodedata.normalize("NFD", nfc)
        self.assertNotEqual(nfc, nfd)
        starts = utc(2026, 6, 10, 12, 0)
        for channel in ("sms", "email"):
            with self.subTest(channel=channel):
                self.assertEqual(
                    rp.build_text(nfd, "IE", starts, channel),
                    rp.build_text(nfc, "IE", starts, channel),
                )
        self.assertEqual(len(rp.build_text(nfd, "IE", starts, "sms")), 160)

    def test_text_uses_starts_at_local_time(self):
        for r in run([make_appt()]):
            self.assertIn("on 10/06/2026 at 14:00.", r["text"])


class SignatureTests(unittest.TestCase):
    def _text(self, appt):
        result = run([appt])
        self.assertTrue(result)
        return result[0]["text"]

    def test_pl_with_padding_gets_polish_signature(self):
        self.assertTrue(self._text(make_appt(phone=None, country=" pl ")).endswith(rp.SIGNATURE_PL))

    def test_ie_gets_irish_signature(self):
        self.assertTrue(self._text(make_appt(phone=None, country="IE")).endswith(rp.SIGNATURE_IE))

    def test_missing_country_gets_irish_signature(self):
        appt = make_appt(phone=None)
        del appt["country"]
        self.assertTrue(self._text(appt).endswith(rp.SIGNATURE_IE))


class SortTests(unittest.TestCase):
    def test_mixed_ids_sorted_deterministically(self):
        starts = dublin(2026, 6, 10, 14, 0)
        appts = [
            make_appt(id="b", starts_at=starts),
            make_appt(id=2, starts_at=starts, phone=None),
            make_appt(id="a", starts_at=starts),
            make_appt(id=1, starts_at=starts),
        ]
        result = run(appts)
        ids = [r["appointment_id"] for r in result]
        self.assertEqual(ids, [1, 2, "a", "b", 1, 2, "a", "b"])
        self.assertEqual(result, run(list(reversed(appts))))

    def test_ties_on_send_at_broken_by_channel(self):
        starts = dublin(2026, 6, 10, 14, 0)
        appts = [
            make_appt(id=7, starts_at=starts),
            make_appt(id=7, starts_at=starts, phone=None),
        ]
        result = run(appts)
        self.assertEqual([r["channel"] for r in result[:2]], ["email", "sms"])
        self.assertEqual(sends(result)[0], sends(result)[1])


class ValidationTests(unittest.TestCase):
    def assertRejects(self, appt, now=NOW):
        with self.assertRaises(ValueError):
            run([appt], now=now)

    def test_missing_id(self):
        appt = make_appt()
        del appt["id"]
        self.assertRejects(appt)

    def test_bool_id(self):
        self.assertRejects(make_appt(id=True))

    def test_naive_starts_at(self):
        self.assertRejects(make_appt(starts_at=datetime(2026, 6, 10, 14, 0)))

    def test_naive_now(self):
        self.assertRejects(make_appt(), now=datetime(2026, 6, 8, 9, 0))

    def test_wrong_type_starts_at(self):
        self.assertRejects(make_appt(starts_at="2026-06-10T14:00:00"))

    def test_non_bool_optout(self):
        self.assertRejects(make_appt(optout_sms_v2="no"))

    def test_empty_customer_name(self):
        self.assertRejects(make_appt(customer_name="   "))

    def test_non_str_country(self):
        self.assertRejects(make_appt(country=44))

    def test_non_list_input(self):
        with self.assertRaises(ValueError):
            rp.plan_reminders({"id": 1}, NOW)

    def test_error_text_omits_email(self):
        appt = make_appt(optout_sms_v2="no", email=EMAIL)
        with self.assertRaises(ValueError) as ctx:
            run([appt])
        self.assertNotIn(EMAIL, str(ctx.exception))
        self.assertNotIn(EMAIL, repr(ctx.exception))


class LoggingTests(unittest.TestCase):
    def test_logs_contain_no_customer_data(self):
        with self.assertLogs(level="DEBUG") as captured:
            result = run([make_appt()])
        self.assertTrue(result)
        joined = "\n".join(captured.output)
        for secret in (EMAIL, PHONE, "Anna", "Murphy", "Siobhán"):
            self.assertNotIn(secret, joined)


class ImmutabilityTests(unittest.TestCase):
    def test_input_list_and_dicts_unchanged(self):
        appts = [make_appt(id=1), make_appt(id=2, optout_sms_v2=None, phone=None)]
        snapshot = copy.deepcopy(appts)
        run(appts)
        self.assertEqual(appts, snapshot)

    def test_tuple_input_accepted(self):
        appts = [make_appt()]
        self.assertEqual(run(tuple(appts)), run(appts))

    def test_no_email_in_any_returned_value(self):
        result = run([make_appt(id=1), make_appt(id=2, phone=None)])
        self.assertTrue(result)
        for reminder in result:
            for value in reminder.values():
                self.assertNotIn(EMAIL, str(value))
            self.assertEqual(reminder["send_at"].utcoffset(), timedelta(0))


if __name__ == "__main__":
    unittest.main()