"""Brennan Opticians appointment reminder planner.

plan_reminders(appointments, now) is a pure planning function. It does not send, store, schedule, or log customer data. The module and its unittest suite are in this one file; split the tests into their own file if preferred. Run with: python3 -m unittest

Implementation notes:
- All datetimes are converted to UTC on entry, so timedelta arithmetic is absolute (DST-safe) and comparisons never use the same-tzinfo naive shortcut.
- Local (Europe/Dublin) time is used only for text formatting and quiet-hours logic.

DEFAULTS (client has not confirmed):
- A missing or null optout_sms_v2 counts as opted out.
- An empty or whitespace-only phone or email counts as absent.
- Text is English. Dates use the form "Tue 14 Oct 2026", times HH:MM Dublin time, and the greeting includes the customer's name.
- Unknown statuses are sendable and are logged by ID. KNOWN_STATUSES is used for that log line only and never gates sending.
- Quiet-hours conflict with now: if the 20:00 move is earlier than now, send at 08:00 Dublin on the next morning, but only if that is before starts_at. Otherwise drop the reminder.

JUDGMENT CALLS:
- Logging conflict: the house rule asks for the contact in each INFO line, but R12 and R18 forbid personal data in logs. Each planned-reminder INFO line therefore records appointment_id and channel only. Support traces deliveries by appointment_id.
- Required fields are id, customer_name, status, and starts_at. email, phone, country, and optout_sms_v2 may be absent.
- starts_at may be a datetime or an ISO 8601 string. Anything else, or any naive value, is malformed and skipped.
- "Next morning" means the first 08:00 Dublin at or after now.
- Name shortening: single-token names skip the initial step and go straight to omitting the name.
- Malformed-row logs use the list index when the id is unusable.
- Sorting key is (send_at, str(appointment_id), channel).

OPEN ISSUE, SMS ENCODING: len() counts characters, not GSM-7 septets or UCS-2 code units. The signature contains characters outside GSM-7 (for example "á", "í", "ó", "ń", "ś"), so the message is UCS-2 on the wire. A UCS-2 message segments at 70 code units, not 160, so a 160-character text may be sent as 3 segments. The 160 limit is a character count per R9; the client should confirm whether segment count matters.
"""

import logging
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
FIRST_LEAD = timedelta(hours=48)
SECOND_LEAD = timedelta(hours=2)
SMS_MAX_LEN = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
QUIET_START_HOUR = 21  # inclusive
QUIET_END_HOUR = 8     # exclusive
EVENING_HOUR = 20
MORNING_HOUR = 8
REQUIRED_FIELDS = ("id", "customer_name", "status", "starts_at")
KNOWN_STATUSES = frozenset({"booked", "confirmed", "scheduled"})  # logging only
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class _Malformed(ValueError):
    """Carries a reason only. Never includes customer values."""


@dataclass(frozen=True)
class _Appt:
    appointment_id: object
    name: str
    email: str | None
    phone: str | None
    opted_out: bool
    signature: str
    status: str
    starts_at: datetime  # UTC


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for index, raw in enumerate(appointments):
        label = _label(raw, index)
        try:
            appt = _parse(raw)
        except _Malformed as exc:
            log.warning("skipped malformed appointment id=%s reason=%s", label, exc)
            continue
        status = appt.status.strip().lower()
        if status == "cancelled":
            log.info("skipped cancelled appointment id=%s", appt.appointment_id)
            continue
        if status not in KNOWN_STATUSES:
            log.info("unknown status for appointment id=%s; treated as sendable",
                     appt.appointment_id)
        if appt.starts_at <= now_utc:
            log.info("skipped appointment not after now id=%s", appt.appointment_id)
            continue
        for raw_send in _slots(appt.starts_at, now_utc):
            reminder = _build(appt, raw_send, now_utc)
            if reminder is None:
                continue
            planned.append(reminder)
            # Contact is deliberately not logged (R12, R18); see module docstring.
            log.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                     appt.appointment_id, reminder["channel"],
                     reminder["send_at"].isoformat())
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


def _label(raw, index):
    if isinstance(raw, dict):
        value = raw.get("id")
        if (isinstance(value, (str, int)) and not isinstance(value, bool)
                and str(value).strip()):
            return str(value)
    return f"index {index}"


def _parse(raw):
    if not isinstance(raw, dict):
        raise _Malformed("not a mapping")
    for field in REQUIRED_FIELDS:
        if raw.get(field) is None:
            raise _Malformed(f"missing field {field}")
    appt_id = raw["id"]
    if (isinstance(appt_id, bool) or not isinstance(appt_id, (str, int))
            or not str(appt_id).strip()):
        raise _Malformed("invalid id")
    name = raw["customer_name"]
    if not isinstance(name, str) or not name.strip():
        raise _Malformed("invalid customer_name")
    status = raw["status"]
    if not isinstance(status, str):
        raise _Malformed("invalid status")
    email = _optional_str(raw, "email")
    phone = _optional_str(raw, "phone")
    country = _optional_str(raw, "country")
    optout = raw.get("optout_sms_v2")
    if optout is None:
        opted_out = True
    elif isinstance(optout, bool):
        opted_out = optout
    else:
        raise _Malformed("invalid optout_sms_v2")
    return _Appt(
        appointment_id=appt_id,
        name=" ".join(name.split()),
        email=email,
        phone=phone,
        opted_out=opted_out,
        signature=_signature(country),
        status=status,
        starts_at=_parse_dt(raw["starts_at"]),
    )


def _optional_str(raw, field):
    value = raw.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _Malformed(f"invalid {field}")
    return value.strip() or None


def _parse_dt(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            raise _Malformed("unparseable starts_at") from None
    if not isinstance(value, datetime):
        raise _Malformed("invalid starts_at type")
    if value.utcoffset() is None:
        raise _Malformed("naive starts_at")
    return value.astimezone(UTC)


def _signature(country):
    if country is not None and country.casefold() == "pl":
        return SIG_PL
    return SIG_DEFAULT


def _slots(starts_at, now_utc):
    # The 48h reminder is moved to now if its point is already past.
    # The 2h reminder is computed independently and dropped if its point is past.
    slots = [max(starts_at - FIRST_LEAD, now_utc)]
    second = starts_at - SECOND_LEAD
    if second >= now_utc:
        slots.append(second)
    return slots


def _build(appt, raw_send, now_utc):
    send_at = _quiet_adjust(raw_send, now_utc, appt.starts_at)
    if send_at is None:
        log.info("dropped reminder appointment_id=%s reason=no allowed send time before start",
                 appt.appointment_id)
        return None
    if send_at < now_utc:
        log.info("dropped reminder appointment_id=%s reason=send time before now",
                 appt.appointment_id)
        return None
    channel, text = None, None
    if appt.phone and not appt.opted_out:
        text = _sms_text(appt)
        if text is not None:
            channel = "sms"
    if channel is None and appt.email:
        channel, text = "email", _email_text(appt)
    if channel is None:
        log.info("dropped reminder appointment_id=%s reason=no usable channel",
                 appt.appointment_id)
        return None
    return {"appointment_id": appt.appointment_id, "channel": channel,
            "send_at": send_at, "text": text}


def _is_quiet(hour):
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _dublin_at(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(now_utc):
    day = now_utc.astimezone(DUBLIN).date()
    candidate = _dublin_at(day, MORNING_HOUR)
    if candidate < now_utc:
        candidate = _dublin_at(day + timedelta(days=1), MORNING_HOUR)
    return candidate


def _quiet_adjust(send_at, now_utc, starts_at):
    local = send_at.astimezone(DUBLIN)
    if not _is_quiet(local.hour):
        return send_at
    day = local.date()
    if local.hour < QUIET_END_HOUR:
        day -= timedelta(days=1)
    evening = _dublin_at(day, EVENING_HOUR)
    if evening >= now_utc:
        return evening
    morning = _next_morning(now_utc)
    return morning if morning < starts_at else None


def _when(starts_at):
    local = starts_at.astimezone(DUBLIN)
    return (f"{_WEEKDAYS[local.weekday()]} {local.day} "
            f"{_MONTHS[local.month - 1]} {local.year} "
            f"at {local.hour:02d}:{local.minute:02d}")


def _greetings(name):
    parts = name.split()
    options = [f"Hi {' '.join(parts)}, "]
    if len(parts) > 1:
        options.append(f"Hi {parts[0][0]}. {parts[-1]}, ")
    options.append("")
    return options


def _sms_text(appt):
    when = _when(appt.starts_at)
    for greeting in _greetings(appt.name):
        text = (f"{greeting}Brennan Opticians appointment: {when} "
                f"(Dublin time). {appt.signature}")
        if len(text) <= SMS_MAX_LEN:
            return text
    return None


def _email_text(appt):
    return (f"Hi {appt.name},\n\n"
            f"This is a reminder of your appointment at Brennan Opticians on "
            f"{_when(appt.starts_at)} (Dublin time).\n\n"
            f"{appt.signature}")


# ---------------------------------------------------------------- tests

def _dub(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


START = _dub(2026, 10, 20, 14)
NOW = _dub(2026, 10, 15, 9)


def _appt(**overrides):
    base = {"id": "A1", "customer_name": "Aoife Murphy",
            "email": "aoife.murphy@example.com", "phone": "+353871234567",
            "country": "IE", "status": "booked", "starts_at": START,
            "optout_sms_v2": False}
    base.update(overrides)
    return base


class ReminderTests(unittest.TestCase):

    def test_48h_and_2h_timing(self):
        start_utc = START.astimezone(UTC)
        res = plan_reminders([_appt()], NOW)
        self.assertEqual([r["send_at"] for r in res],
                         [start_utc - FIRST_LEAD, start_utc - SECOND_LEAD])
        self.assertEqual({r["channel"] for r in res}, {"sms"})

    def test_immediate_when_48h_passed(self):
        now = _dub(2026, 10, 19, 9)
        res = plan_reminders([_appt()], now)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["send_at"], now.astimezone(UTC))
        self.assertEqual(res[1]["send_at"], START.astimezone(UTC) - SECOND_LEAD)

    def test_no_second_when_2h_passed(self):
        now = _dub(2026, 10, 20, 12, 30)
        res = plan_reminders([_appt()], now)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["send_at"], now.astimezone(UTC))

    def test_quiet_2200_moves_to_2000_same_day(self):
        starts = _dub(2026, 10, 21, 0, 0)  # 2h point is 22:00 on 20 Oct
        res = plan_reminders([_appt(starts_at=starts)], _dub(2026, 10, 19, 9))
        self.assertIn(_dub(2026, 10, 20, 20), [r["send_at"] for r in res])

    def test_quiet_0200_moves_to_2000_previous_day(self):
        starts = _dub(2026, 10, 21, 4, 0)  # 2h point is 02:00 on 21 Oct
        res = plan_reminders([_appt(starts_at=starts)], _dub(2026, 10, 19, 9))
        self.assertIn(_dub(2026, 10, 20, 20), [r["send_at"] for r in res])

    def test_0800_is_allowed(self):
        starts = _dub(2026, 10, 20, 10, 0)  # 2h point is 08:00 on 20 Oct
        res = plan_reminders([_appt(starts_at=starts)], _dub(2026, 10, 19, 9))
        self.assertIn(_dub(2026, 10, 20, 8), [r["send_at"] for r in res])

    def test_quiet_fallback_to_next_morning(self):
        now = _dub(2026, 10, 20, 21)
        starts = _dub(2026, 10, 21, 12)
        res = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual([r["send_at"] for r in res],
                         [_dub(2026, 10, 21, 8), _dub(2026, 10, 21, 10)])

    def test_quiet_fallback_dropped_when_morning_after_start(self):
        now = _dub(2026, 10, 20, 21)
        starts = _dub(2026, 10, 20, 23, 30)
        self.assertEqual(plan_reminders([_appt(starts_at=starts)], now), [])

    def test_cancelled_excluded(self):
        self.assertEqual(plan_reminders([_appt(status="  CanCelled ")], NOW), [])

    def test_unknown_status_still_sendable(self):
        res = plan_reminders([_appt(status="pending")], NOW)
        self.assertEqual(len(res), 2)

    def test_channel_selection(self):
        cases = [
            ({}, "sms"),
            ({"optout_sms_v2": True}, "email"),
            ({"optout_sms_v2": None}, "email"),
            ({"phone": "   "}, "email"),
            ({"phone": None, "email": None}, None),
            ({"optout_sms_v2": True, "email": ""}, None),
            ({"phone": " ", "email": "  "}, None),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                res = plan_reminders([_appt(**overrides)], NOW)
                if expected is None:
                    self.assertEqual(res, [])
                else:
                    self.assertEqual(len(res), 2)
                    self.assertEqual({r["channel"] for r in res}, {expected})

    def test_sms_shortens_name_keeps_date_time_and_signature(self):
        name = "Seán " + "Q" * 120 + " Súilleabháin"
        res = plan_reminders([_appt(customer_name=name)], NOW)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertEqual(r["channel"], "sms")
            self.assertLessEqual(len(r["text"]), SMS_MAX_LEN)
            self.assertIn("S. Súilleabháin", r["text"])
            self.assertNotIn("Seán", r["text"])
            self.assertIn("20 Oct 2026", r["text"])
            self.assertIn("14:00", r["text"])
            self.assertTrue(r["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_sms_omits_name_when_nothing_else_fits(self):
        res = plan_reminders([_appt(customer_name="Q" * 200)], NOW)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertEqual(r["channel"], "sms")
            self.assertLessEqual(len(r["text"]), SMS_MAX_LEN)
            self.assertNotIn("QQQ", r["text"])
            self.assertIn("20 Oct 2026", r["text"])

    def test_short_name_kept_in_full(self):
        res = plan_reminders([_appt()], NOW)
        self.assertIn("Hi Aoife Murphy, ", res[0]["text"])

    def test_polish_signature(self):
        res = plan_reminders([_appt(country=" pl ")], NOW)
        for r in res:
            self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))
        res = plan_reminders([_appt(id="p", country="Pl", optout_sms_v2=True)], NOW)
        self.assertEqual(res[0]["channel"], "email")
        self.assertTrue(res[0]["text"].endswith("Grzegorz Szczepański"))

    def test_default_signature_when_country_missing(self):
        res = plan_reminders([_appt(country=None)], NOW)
        self.assertTrue(res[0]["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_no_past_send_at(self):
        scenarios = [
            (NOW, START),
            (_dub(2026, 10, 19, 9), START),
            (_dub(2026, 10, 20, 12, 30), START),
            (_dub(2026, 10, 20, 21), _dub(2026, 10, 21, 12)),
            (_dub(2026, 10, 20, 21), _dub(2026, 10, 20, 23, 30)),
        ]
        for now, starts in scenarios:
            with self.subTest(now=now, starts=starts):
                res = plan_reminders([_appt(starts_at=starts)], now)
                for r in res:
                    self.assertGreaterEqual(r["send_at"], now.astimezone(UTC))
                    self.assertIsInstance(r["send_at"].tzinfo, type(UTC))

    def test_sorting_and_tie_break(self):
        res = plan_reminders([_appt(id="b"), _appt(id="a")], NOW)
        self.assertEqual([r["appointment_id"] for r in res], ["a", "b", "a", "b"])
        times = [r["send_at"] for r in res]
        self.assertEqual(times, sorted(times))

    def test_dst_dublin(self):
        starts = datetime(2026, 3, 30, 11, 0, tzinfo=DUBLIN)  # IST after 29 Mar
        now = _dub(2026, 3, 27, 9)                            # GMT before 29 Mar
        res = plan_reminders([_appt(starts_at=starts)], now)
        self.assertEqual(res[0]["send_at"], datetime(2026, 3, 28, 10, 0, tzinfo=UTC))
        self.assertEqual(res[1]["send_at"], datetime(2026, 3, 30, 8, 0, tzinfo=UTC))
        self.assertIn("30 Mar 2026 at 11:00", res[1]["text"])

    def test_malformed_rows_skipped(self):
        rows = [
            _appt(id="ok1"),
            {"customer_name": "No Id", "email": "x@example.com",
             "status": "booked", "starts_at": START},
            _appt(id="naive", starts_at=datetime(2026, 10, 20, 14, 0)),
            _appt(id="badstr", starts_at="2026-13-45"),
            _appt(id="badopt", optout_sms_v2="yes"),
            "not a dict",
            _appt(id="ok2", phone=None),
        ]
        with self.assertLogs(level=logging.DEBUG) as cm:
            res = plan_reminders(rows, NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"ok1", "ok2"})
        out = "\n".join(cm.output)
        self.assertIn("badopt", out)
        self.assertIn("index 1", out)
        self.assertIn("index 5", out)

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([_appt()], datetime(2026, 10, 15, 9))

    def test_no_email_in_logs(self):
        rows = [_appt(), _appt(id="B", phone=None), _appt(id="C", optout_sms_v2=True),
                _appt(id="D", starts_at="bad")]
        with self.assertLogs(level=logging.DEBUG) as cm:
            plan_reminders(rows, NOW)
        out = "\n".join(cm.output)
        self.assertNotIn("@", out)
        self.assertNotIn("aoife", out.lower())
        self.assertNotIn("+353", out)
        self.assertNotIn("Aoife", out)


if __name__ == "__main__":
    unittest.main()