# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-4vqmmw4z/brennan_reminders/reminders.py
# NOTE: No file-write or shell tools were available in this session. Nothing below has been written to disk or executed.
# Save both modules to the paths above, then run:
#   python3 -I -m unittest discover -s /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-4vqmmw4z/brennan_reminders -p "test_*.py"
#
# DECISIONS BEYOND THE SPEC
# - Logging: one INFO line per planned reminder logs appointment id and channel only. The house rule asks for contact details in the log, but the spec forbids logging email or phone values. The stricter spec was followed and contact is omitted. Needs sign-off.
# - Required keys: id, customer_name, email, phone, status, starts_at. optout_sms_v2 and country are optional, because the spec says missing opt-out means "not opted out" and missing country means the Siobhan signature.
# - Non-list appointments (including tuples and None for None) raise TypeError.
# - Status None is treated as "" (scheduled). Unknown statuses are logged at DEBUG with id only.
# - optout_sms_v2: only the bool False and None mean not opted out. Integer 0 and any other unrecognised value are treated as opted out with a WARNING. Strings "false", "no", "0" and "" fall into the fail-safe branch. This is the literal spec reading and probably not intended.
# - An invalid (non-None) email logs INFO with id only.
# - A dropped reminder yields its own skip record (after_start or duplicate_slot). An appointment can therefore produce one reminder and one skip record.
# - Invalid records produce Skipped(appointment_id=None, reason="invalid_record"). The list index is logged.
# - Tests use unittest.assertLogs in place of pytest caplog, since no third-party packages are allowed.
#
# OPEN ISSUES FOR THE CLIENT AND TECH LEAD
# 1. Second reminder offset defaults to 2 hours before start. Client must confirm.
# 2. No-contact appointments get no send and a WARNING per appointment with id only. Confirm whether another channel is wanted.
# 3. Early-morning quiet hours move forward to 08:00, with the 20:00 previous-evening fallback only where needed. The brief says "back to 20:00". Confirm.
# 4. SMS encoding: code points are counted against 160 as instructed. The "a" with acute accent in Siobhan is not in GSM 03.38, so the gateway may use UCS-2 with 70 characters per segment. Client must confirm the gateway encoding. No UCS-2 limit is implemented.
# 5. Message language is English.
# 6. Opt-out suppresses SMS only, and email is still sent. Confirm this is legally correct.
# 7. Only cancelled and canceled are suppressed. pending and no_show are scheduled. Confirm.
# 8. Email subject is not in the output. The sending layer should set "Appointment reminder".
# 9. send_at is always UTC.
# 10. The function is stateless. Re-running it re-sets overdue reminders to now, so the caller must record what was sent or duplicates will occur. A rescheduled appointment produces new reminders. Tech lead to note.

import logging
import unicodedata
from collections import Counter, namedtuple
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger("brennan_reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
OFFSET_48H = timedelta(hours=48)
OFFSET_2H = timedelta(hours=2)
SMS_MAX_LENGTH = 160
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED_KEYS = frozenset({"id", "customer_name", "email", "phone", "status", "starts_at"})
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
KNOWN_STATUSES = frozenset({"", "confirmed", "pending", "no_show"})
TRUE_OPTOUT_STRINGS = frozenset({"true", "1", "yes", "y"})
SMS_TEMPLATE = ("Hi {name}, your Brennan Opticians appointment is on {date} "
                "at {time} (Dublin time). {signature}")
SMS_GENERIC = ("Hello, your Brennan Opticians appointment is on {date} "
               "at {time} (Dublin time). {signature}")

Skipped = namedtuple("Skipped", ["appointment_id", "reason"])


class _InternalError(Exception):
    pass


def _is_aware(value):
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() is not None)


def _dublin_to_utc(day, hour):
    local = datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN)
    return local.astimezone(UTC)


def _in_quiet_window(moment):
    hour = moment.astimezone(DUBLIN).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _quiet_adjust(due):
    """Step 2. Returns (send, moved_to_morning)."""
    local = due.astimezone(DUBLIN)
    if local.hour >= QUIET_START_HOUR:
        return _dublin_to_utc(local.date(), 20), False
    if local.hour < QUIET_END_HOUR:
        return _dublin_to_utc(local.date(), QUIET_END_HOUR), True
    return due, False


def _next_morning(now):
    local = now.astimezone(DUBLIN)
    day = local.date()
    if local.hour >= QUIET_START_HOUR:
        day = day + timedelta(days=1)
    return _dublin_to_utc(day, QUIET_END_HOUR)


def _schedule(due, now, starts_at):
    """Steps 2 to 5. Returns the send time, or None if the reminder is dropped as after_start."""
    send, morning = _quiet_adjust(due)
    if morning and send >= starts_at:
        previous_day = due.astimezone(DUBLIN).date() - timedelta(days=1)
        send = _dublin_to_utc(previous_day, 20)
    if send < now:
        if _in_quiet_window(now):
            send = _next_morning(now)
        else:
            send = now
    if send >= starts_at:
        return None
    return send


def _format_start(starts_at):
    local = starts_at.astimezone(DUBLIN)
    date_text = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    time_text = f"{local.hour:02d}:{local.minute:02d}"
    return date_text, time_text


def _sms_text(name, date_text, time_text, signature):
    candidates = []
    if name:
        candidates.append(name)
        candidates.append(name.split()[0])
    for candidate in candidates:
        text = SMS_TEMPLATE.format(name=candidate, date=date_text,
                                   time=time_text, signature=signature)
        if len(text) <= SMS_MAX_LENGTH:
            return text
    text = SMS_GENERIC.format(date=date_text, time=time_text, signature=signature)
    if len(text) > SMS_MAX_LENGTH:
        raise _InternalError("sms text exceeds limit")
    return text


def _email_text(name, date_text, time_text, signature):
    greeting = f"Dear {name}," if name else "Hello,"
    return "\n".join([
        greeting,
        "",
        f"This is a reminder of your Brennan Opticians appointment on {date_text} at {time_text} (Dublin time).",
        "",
        "If you need to change or cancel your appointment, please contact us.",
        "",
        signature,
    ])


def _normalise_name(value):
    if not isinstance(value, str):
        return None
    collapsed = " ".join(unicodedata.normalize("NFC", value).split())
    return collapsed or None


def _phone_present(value):
    return isinstance(value, str) and value.strip() != ""


def _normalise_email(value):
    if not isinstance(value, str):
        return None
    email = value.strip()
    if email.count("@") != 1 or any(ch.isspace() for ch in email):
        return None
    local_part, domain = email.split("@")
    if not local_part or not domain:
        return None
    return email


def _opted_out(value, appointment_id):
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in TRUE_OPTOUT_STRINGS:
        return True
    logger.warning("unrecognised optout_sms_v2 value for appointment_id=%s; treated as opted out",
                   appointment_id)
    return True


def _signature(country):
    text = "" if country is None else str(country)
    if text.strip().upper() == "PL":
        return "Grzegorz Szczepański"
    return "Siobhán Ní Dhuibhir"


def _plan_one(record, now):
    """Returns (results, reasons). results is a list of (kind_order, reminder_dict)."""
    appointment_id = record["id"]
    status = record["status"]
    status_norm = "" if status is None else str(status).strip().casefold()
    if status_norm in CANCELLED_STATUSES:
        return [], ["cancelled"]
    if status_norm not in KNOWN_STATUSES:
        logger.debug("unrecognised status for appointment_id=%s", appointment_id)

    starts_at = record["starts_at"]
    if not _is_aware(starts_at):
        logger.warning("invalid starts_at for appointment_id=%s", appointment_id)
        return [], ["invalid_datetime"]
    if starts_at <= now:
        logger.info("already started, appointment_id=%s", appointment_id)
        return [], ["already_started"]

    phone_present = _phone_present(record["phone"])
    email = _normalise_email(record["email"])
    if record["email"] is not None and email is None:
        logger.info("invalid email for appointment_id=%s", appointment_id)
    opted_out = _opted_out(record.get("optout_sms_v2"), appointment_id)

    if phone_present and not opted_out:
        channel = "sms"
    elif email is not None:
        channel = "email"
    elif phone_present:
        logger.warning("opted out with no email, appointment_id=%s", appointment_id)
        return [], ["opted_out_no_email"]
    else:
        logger.warning("no usable contact, appointment_id=%s", appointment_id)
        return [], ["no_contact"]

    name = _normalise_name(record["customer_name"])
    signature = _signature(record.get("country"))
    date_text, time_text = _format_start(starts_at)
    if channel == "sms":
        text = _sms_text(name, date_text, time_text, signature)
    else:
        text = _email_text(name, date_text, time_text, signature)

    reasons = []
    scheduled = []
    for kind, raw_due in ((0, starts_at - OFFSET_48H), (1, starts_at - OFFSET_2H)):
        send = _schedule(max(raw_due, now), now, starts_at)
        if send is None:
            logger.info("reminder dropped after start, appointment_id=%s", appointment_id)
            reasons.append("after_start")
        else:
            scheduled.append((kind, send))
    if len(scheduled) == 2 and scheduled[0][1] == scheduled[1][1]:
        logger.info("duplicate slot, appointment_id=%s", appointment_id)
        reasons.append("duplicate_slot")
        scheduled = scheduled[1:]

    results = [(kind, {"appointment_id": appointment_id, "channel": channel,
                       "send_at": send, "text": text})
               for kind, send in scheduled]
    return results, reasons


def _safe_id(record):
    return record.get("id") if isinstance(record, dict) else None


def _plan_with_report(appointments, now):
    if appointments is None:
        raise TypeError("appointments must be a list")
    if not isinstance(now, datetime):
        raise TypeError("now must be a datetime")
    if not _is_aware(now):
        raise ValueError("now must be timezone-aware")

    planned = []
    skipped = []
    for index, record in enumerate(appointments):
        try:
            if not isinstance(record, dict) or not REQUIRED_KEYS.issubset(record.keys()):
                logger.warning("invalid record at index %d skipped", index)
                skipped.append(Skipped(None, "invalid_record"))
                continue
            results, reasons = _plan_one(record, now)
        except Exception as exc:
            appointment_id = _safe_id(record)
            logger.error("internal_error appointment_id=%s exception=%s",
                         appointment_id, type(exc).__name__)
            skipped.append(Skipped(appointment_id, "internal_error"))
            continue
        appointment_id = record["id"]
        for kind, reminder in results:
            planned.append((kind, reminder))
            logger.info("reminder planned appointment_id=%s channel=%s",
                        appointment_id, reminder["channel"])
        for reason in reasons:
            skipped.append(Skipped(appointment_id, reason))

    planned.sort(key=lambda item: (item[1]["send_at"],
                                   str(item[1]["appointment_id"]),
                                   item[0]))
    counts = Counter(item.reason for item in skipped)
    logger.info("summary planned=%d skipped=%d reasons=%s",
                len(planned), len(skipped), dict(sorted(counts.items())))
    return [reminder for _, reminder in planned], skipped


def plan_reminders(appointments, now):
    reminders, _ = _plan_with_report(appointments, now)
    return reminders

# ---- END OF reminders.py ----
# ---- NEXT FILE: save the following as test_reminders.py at its absolute path ----

import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import reminders
from reminders import plan_reminders, _plan_with_report

UTC = timezone.utc
NOW = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)
STD_START = datetime(2026, 10, 23, 13, 30, tzinfo=UTC)
EMAIL_PII = "zz.tester@example.com"
PHONE_PII = "+353 85 000 9999"
NAME_PII = "Quinlan Xyzzy"


def make(starts_at, **overrides):
    record = {
        "id": "A1",
        "customer_name": "Ciara Byrne",
        "email": None,
        "phone": "+353851234567",
        "country": "IE",
        "status": "confirmed",
        "starts_at": starts_at,
        "optout_sms_v2": False,
    }
    record.update(overrides)
    return record


def sends(records):
    return [r["send_at"] for r in records]


class TestPlanning(unittest.TestCase):

    def test_empty_list_returns_empty(self):
        self.assertEqual(plan_reminders([], NOW), [])

    def test_none_appointments_raises_type_error(self):
        with self.assertRaises(TypeError):
            plan_reminders(None, NOW)

    def test_naive_now_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([make(STD_START)], datetime(2026, 10, 13, 9, 0))
        self.assertNotIn(EMAIL_PII, str(cm.exception))

    def test_output_sorted_by_send_time_then_id(self):
        appts = [make(STD_START, id="b"),
                 make(STD_START + timedelta(days=1), id="a"),
                 make(STD_START, id="a")]
        out = plan_reminders(appts, NOW)
        keys = [(r["send_at"], str(r["appointment_id"])) for r in out]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(out), 6)

    def test_standard_appointment_two_sms_at_offsets(self):
        out = plan_reminders([make(STD_START)], NOW)
        self.assertEqual(sends(out), [STD_START - timedelta(hours=48),
                                      STD_START - timedelta(hours=2)])
        self.assertEqual({r["channel"] for r in out}, {"sms"})

    def test_thirty_hours_ahead_48h_slot_moves_to_now(self):
        start = NOW + timedelta(hours=30)
        out = plan_reminders([make(start)], NOW)
        self.assertEqual(sends(out), [NOW, start - timedelta(hours=2)])

    def test_one_hour_ahead_gives_single_reminder_at_now(self):
        start = NOW + timedelta(hours=1)
        out, skipped = _plan_with_report([make(start)], NOW)
        self.assertEqual(sends(out), [NOW])
        self.assertEqual([s.reason for s in skipped], ["duplicate_slot"])

    def test_start_at_or_before_now_gives_nothing(self):
        for start in (NOW, NOW - timedelta(minutes=5)):
            out, skipped = _plan_with_report([make(start)], NOW)
            self.assertEqual(out, [])
            self.assertEqual([s.reason for s in skipped], ["already_started"])

    def test_cancelled_statuses_are_suppressed(self):
        for status in ("cancelled", " CANCELLED ", "canceled"):
            out, skipped = _plan_with_report([make(STD_START, status=status)], NOW)
            self.assertEqual(out, [])
            self.assertEqual([s.reason for s in skipped], ["cancelled"])

    def test_other_statuses_are_scheduled(self):
        for status in ("confirmed", "pending", "no_show", None, ""):
            self.assertEqual(len(plan_reminders([make(STD_START, status=status)], NOW)), 2)

    def test_due_at_2230_local_moves_to_2000_same_date(self):
        start = datetime(2026, 10, 17, 21, 30, tzinfo=UTC)
        out = plan_reminders([make(start)], NOW)
        self.assertIn(datetime(2026, 10, 15, 19, 0, tzinfo=UTC), sends(out))

    def test_due_at_0730_local_with_now_at_1900_gives_now(self):
        now = datetime(2026, 10, 14, 18, 0, tzinfo=UTC)
        start = datetime(2026, 10, 16, 6, 30, tzinfo=UTC)
        out = plan_reminders([make(start)], now)
        self.assertIn(now, sends(out))

    def test_due_at_0300_local_moves_to_0800_same_morning(self):
        start = datetime(2026, 10, 17, 2, 0, tzinfo=UTC)
        out = plan_reminders([make(start)], NOW)
        self.assertEqual(sends(out), [datetime(2026, 10, 15, 7, 0, tzinfo=UTC),
                                      datetime(2026, 10, 16, 19, 0, tzinfo=UTC)])

    def test_morning_move_falls_back_to_previous_evening_when_0800_too_late(self):
        start = datetime(2026, 10, 17, 6, 0, tzinfo=UTC)
        out = plan_reminders([make(start)], NOW)
        self.assertEqual(sends(out)[1], datetime(2026, 10, 16, 19, 0, tzinfo=UTC))

    def test_morning_move_kept_when_0800_before_start(self):
        start = datetime(2026, 10, 17, 8, 0, tzinfo=UTC)
        out = plan_reminders([make(start)], NOW)
        self.assertIn(datetime(2026, 10, 17, 7, 0, tzinfo=UTC), sends(out))

    def test_overdue_reminder_during_quiet_hours_goes_to_next_0800(self):
        now = datetime(2026, 10, 14, 21, 0, tzinfo=UTC)
        start = datetime(2026, 10, 15, 17, 0, tzinfo=UTC)
        out = plan_reminders([make(start)], now)
        self.assertIn(datetime(2026, 10, 15, 7, 0, tzinfo=UTC), sends(out))

    def test_email_used_when_no_phone(self):
        out = plan_reminders([make(STD_START, phone=None, email="pat@example.com")], NOW)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_email_used_when_phone_is_blank(self):
        out = plan_reminders([make(STD_START, phone="   ", email="pat@example.com")], NOW)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_opted_out_with_email_gives_email_only(self):
        out = plan_reminders([make(STD_START, optout_sms_v2=True, email="pat@example.com")], NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual({r["channel"] for r in out}, {"email"})

    def test_opted_out_without_email_gives_nothing_and_warns(self):
        with self.assertLogs("brennan_reminders", level="WARNING"):
            out, skipped = _plan_with_report([make(STD_START, optout_sms_v2=True)], NOW)
        self.assertEqual(out, [])
        self.assertEqual([s.reason for s in skipped], ["opted_out_no_email"])

    def test_no_phone_no_email_gives_nothing_and_warns(self):
        with self.assertLogs("brennan_reminders", level="WARNING"):
            out, skipped = _plan_with_report([make(STD_START, phone=None)], NOW)
        self.assertEqual(out, [])
        self.assertEqual([s.reason for s in skipped], ["no_contact"])

    def test_legacy_opt_out_key_is_ignored(self):
        out = plan_reminders([make(STD_START, opt_out=True)], NOW)
        self.assertEqual({r["channel"] for r in out}, {"sms"})

    def test_missing_or_false_optout_gives_sms(self):
        missing = make(STD_START)
        del missing["optout_sms_v2"]
        for record in (missing, make(STD_START, optout_sms_v2=False)):
            out = plan_reminders([record], NOW)
            self.assertEqual({r["channel"] for r in out}, {"sms"})

    def test_sms_name_shortens_but_date_and_time_stay(self):
        long_name = " ".join(["Maximilian"] * 20)
        out = plan_reminders([make(STD_START, customer_name=long_name)], NOW)
        text = out[0]["text"]
        self.assertLessEqual(len(text), 160)
        self.assertTrue(text.startswith("Hi Maximilian, "))
        self.assertIn("on 23 Oct 2026 at 14:30 (Dublin time)", text)

    def test_sms_generic_when_nothing_fits(self):
        out = plan_reminders([make(STD_START, customer_name="X" * 170)], NOW)
        text = out[0]["text"]
        self.assertLessEqual(len(text), 160)
        self.assertTrue(text.startswith("Hello, your Brennan Opticians"))
        self.assertIn("23 Oct 2026 at 14:30", text)

    def test_accented_name_counted_and_normalised(self):
        decomposed = "Siobha\u0301n  Ni   Dhuibhir"
        out = plan_reminders([make(STD_START, customer_name=decomposed)], NOW)
        expected = ("Hi Siobhán Ní Dhuibhir, your Brennan Opticians appointment "
                    "is on 23 Oct 2026 at 14:30 (Dublin time). Siobhán Ní Dhuibhir")
        self.assertEqual(out[0]["text"], expected)
        self.assertEqual(len(out[0]["text"]), len(expected))

    def test_country_selects_signature(self):
        pl = plan_reminders([make(STD_START, country=" pl ")], NOW)[0]["text"]
        self.assertTrue(pl.endswith("Grzegorz Szczepański"))
        for country in ("IE", None, "   "):
            text = plan_reminders([make(STD_START, country=country)], NOW)[0]["text"]
            self.assertTrue(text.endswith("Siobhán Ní Dhuibhir"))
        missing = make(STD_START)
        del missing["country"]
        text = plan_reminders([missing], NOW)[0]["text"]
        self.assertTrue(text.endswith("Siobhán Ní Dhuibhir"))

    def test_email_text_has_date_time_signature_and_no_address(self):
        start = datetime(2026, 10, 20, 13, 30, tzinfo=UTC)
        out = plan_reminders([make(start, phone=None, email=EMAIL_PII)], NOW)
        text = out[0]["text"]
        self.assertIn("20 Oct 2026", text)
        self.assertIn("14:30", text)
        self.assertIn("Siobhán Ní Dhuibhir", text)
        self.assertTrue(text.startswith("Dear Ciara Byrne,"))
        self.assertNotIn(EMAIL_PII, text)

    def test_email_greeting_without_name(self):
        start = datetime(2026, 10, 20, 13, 30, tzinfo=UTC)
        out = plan_reminders([make(start, phone=None, email="pat@example.com",
                                   customer_name="   ")], NOW)
        self.assertTrue(out[0]["text"].startswith("Hello,"))

    def test_dst_spring_forward_local_time(self):
        start = datetime(2027, 3, 28, 12, 0, tzinfo=UTC)
        out = plan_reminders([make(start)], NOW)
        self.assertTrue(out)
        for r in out:
            self.assertIn("28 Mar 2027", r["text"])
            self.assertIn("13:00", r["text"])

    def test_dst_fall_back_local_time(self):
        start = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
        out = plan_reminders([make(start)], NOW)
        self.assertTrue(out)
        for r in out:
            self.assertIn("25 Oct 2026", r["text"])
            self.assertIn("12:00", r["text"])

    def test_naive_starts_at_is_skipped(self):
        with self.assertLogs("brennan_reminders", level="WARNING"):
            out, skipped = _plan_with_report([make(datetime(2026, 10, 23, 13, 30))], NOW)
        self.assertEqual(out, [])
        self.assertEqual([s.reason for s in skipped], ["invalid_datetime"])

    def test_output_has_exactly_four_keys_utc_and_original_id(self):
        out = plan_reminders([make(STD_START, id=7)], NOW)
        self.assertTrue(out)
        for r in out:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertIsNotNone(r["send_at"].tzinfo)
            self.assertEqual(r["send_at"].utcoffset(), timedelta(0))
            self.assertIs(type(r["appointment_id"]), int)
            self.assertEqual(r["appointment_id"], 7)

    def test_input_not_mutated(self):
        appts = [make(STD_START, email=" pat@example.com ", optout_sms_v2="maybe")]
        snapshot = copy.deepcopy(appts)
        with self.assertLogs("brennan_reminders", level="WARNING"):
            plan_reminders(appts, NOW)
        self.assertEqual(appts, snapshot)

    def test_malformed_records_are_skipped_without_raising(self):
        records = [42, "text", None, {"id": "x"}, make(STD_START)]
        with self.assertLogs("brennan_reminders", level="WARNING"):
            out, skipped = _plan_with_report(records, NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual([s.reason for s in skipped], ["invalid_record"] * 3)

    def test_internal_error_skips_only_that_appointment(self):
        records = [make(STD_START, id="E1"),
                   make(STD_START, id="E2", phone=None, email="pat@example.com")]
        with mock.patch.object(reminders, "_sms_text", side_effect=RuntimeError("boom")):
            with self.assertLogs("brennan_reminders", level="ERROR") as cm:
                out, skipped = _plan_with_report(records, NOW)
        self.assertEqual([(s.appointment_id, s.reason) for s in skipped],
                         [("E1", "internal_error")])
        self.assertEqual({r["appointment_id"] for r in out}, {"E2"})
        self.assertTrue(any("RuntimeError" in r.getMessage() for r in cm.records))

    def test_logs_never_contain_contact_details_or_name(self):
        records = [
            make(STD_START, id="P1", customer_name=NAME_PII, email=EMAIL_PII,
                 phone=PHONE_PII, optout_sms_v2="maybe"),
            make(STD_START, id="P2", customer_name=NAME_PII,
                 email="not-an-email " + EMAIL_PII, phone=None),
            make(STD_START, id="P3", customer_name=NAME_PII, email=None,
                 phone=PHONE_PII, optout_sms_v2=True),
            make(STD_START, id="P4", customer_name=NAME_PII, phone=None, email=None),
            make(STD_START, id="P5", customer_name=NAME_PII, starts_at=PHONE_PII),
        ]
        with mock.patch.object(reminders, "_sms_text",
                               side_effect=RuntimeError(EMAIL_PII + PHONE_PII)):
            with self.assertLogs("brennan_reminders", level="DEBUG") as cm:
                plan_reminders(records, NOW)
        self.assertTrue(cm.records)
        for record in cm.records:
            message = record.getMessage()
            for needle in (EMAIL_PII, PHONE_PII, NAME_PII):
                self.assertNotIn(needle, message)
            self.assertIsNone(record.exc_info)

    def test_unknown_status_is_scheduled(self):
        out = plan_reminders([make(STD_START, status="rescheduled")], NOW)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()