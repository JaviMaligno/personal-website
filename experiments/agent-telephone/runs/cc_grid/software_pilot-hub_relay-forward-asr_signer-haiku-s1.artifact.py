"""Appointment reminder planner for Brennan Opticians.

Decisions taken where the spec was open (for client confirmation):
- Times use Europe/Dublin via zoneinfo. The 48h and 2h offsets are elapsed time, computed in UTC. Quiet hours and message text use Dublin wall-clock time.
- Appointments with status "cancelled" (case-insensitive) are skipped, as are appointments whose starts_at is not after now.
- First reminder is starts_at minus 48h, or now if that point is at or before now. Second reminder is starts_at minus 2h, omitted if at or before now.
- Quiet hours are 21:00 to 08:00 Dublin time (21:00 inside, 08:00 outside). A send in the window moves to 20:00 the same evening (21:00 to 23:59) or the previous evening (00:00 to 07:59). If the moved time is before now, the reminder is dropped.
- Channel is exactly one per reminder. A truthy optout_sms_v2 gives email. Otherwise a non-empty phone gives SMS. Otherwise email. If the chosen contact is missing, nothing is emitted for that slot. The legacy opt_out field is never read.
- Text is "Appointment on DD/MM/YYYY at HH:MM." in Dublin local time, optionally prefixed with "Hi <name>.", and ends with the signature. The signature is "Grzegorz Szczepański" when country is PL, otherwise "Chevonne Nee Divver".
- SMS is limited to 160 by len(). Name shortening order is full name, then first name, then truncated name, then no name. Date and time are never shortened. Email has no length limit.
- Sort key is (send_at, str(appointment_id), channel). Using str() keeps mixed id types from raising.
- Logging: each planned reminder logs one INFO line with appointment_id, channel and contact_ref. contact_ref is a truncated SHA-256 of the contact value, so support can match a delivery to a CRM record without the address or number appearing in logs. Names, emails and phone numbers are never logged. Confirm with the client that a hashed contact reference is acceptable.
- The legacy folder is not used.
"""

import hashlib
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
EVENING_SEND = time(20, 0)
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
SIG_DEFAULT = "Chevonne Nee Divver"
SIG_PL = "Grzegorz Szczepański"

log = logging.getLogger(__name__)


def _clean(value):
    return "" if value is None else str(value).strip()


def _require_aware_utc(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def _signature(country):
    return SIG_PL if _clean(country).upper() == "PL" else SIG_DEFAULT


def _choose_channel(appt):
    email = _clean(appt.get("email"))
    phone = _clean(appt.get("phone"))
    if bool(appt.get("optout_sms_v2")):
        return ("email", email) if email else (None, "")
    if phone:
        return "sms", phone
    if email:
        return "email", email
    return None, ""


def _apply_quiet_hours(send_utc):
    local = send_utc.astimezone(DUBLIN)
    if QUIET_END_HOUR <= local.hour < QUIET_START_HOUR:
        return send_utc
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    return datetime.combine(day, EVENING_SEND, tzinfo=DUBLIN).astimezone(UTC)


def _compose(name, starts_local, signature, sms):
    core = f"Appointment on {starts_local:%d/%m/%Y} at {starts_local:%H:%M}."

    def make(who):
        return f"Hi {who}. {core} {signature}" if who else f"{core} {signature}"

    text = make(name)
    if not sms or not name or len(text) <= SMS_LIMIT:
        return text
    words = name.split()
    budget = SMS_LIMIT - (len(make("x")) - 1)
    for candidate in (words[0] if words else "", name[:budget].rstrip()):
        if candidate:
            shortened = make(candidate)
            if len(shortened) <= SMS_LIMIT:
                return shortened
    return make("")


def plan_reminders(appointments, now):
    now_utc = _require_aware_utc(now, "now")
    planned = []
    for appt in appointments:
        appt_id = appt["id"]
        if _clean(appt.get("status")).lower() == "cancelled":
            continue
        starts_utc = _require_aware_utc(appt.get("starts_at"), "starts_at")
        if starts_utc <= now_utc:
            continue
        channel, contact = _choose_channel(appt)
        if channel is None:
            continue

        first = starts_utc - FIRST_OFFSET
        slots = [now_utc if first <= now_utc else first]
        second = starts_utc - SECOND_OFFSET
        if second > now_utc:
            slots.append(second)

        name = _clean(appt.get("customer_name"))
        signature = _signature(appt.get("country"))
        starts_local = starts_utc.astimezone(DUBLIN)
        contact_ref = hashlib.sha256(contact.lower().encode("utf-8")).hexdigest()[:12]

        for slot in slots:
            send_at = _apply_quiet_hours(slot)
            if send_at < now_utc:
                continue
            text = _compose(name, starts_local, signature, channel == "sms")
            planned.append(
                {"appointment_id": appt_id, "channel": channel, "send_at": send_at, "text": text}
            )
            log.info(
                "planned reminder appointment_id=%s channel=%s contact_ref=%s send_at=%s",
                appt_id, channel, contact_ref, send_at.isoformat(),
            )

    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


EMAIL = "customer@example.com"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


def _appt(**overrides):
    base = {
        "id": 1,
        "customer_name": "Aoife Byrne",
        "email": EMAIL,
        "phone": "+353 86 000 0000",
        "country": "IE",
        "status": "booked",
        "optout_sms_v2": False,
        "starts_at": datetime(2026, 10, 14, 14, 0, tzinfo=DUBLIN),
    }
    base.update(overrides)
    return base


def _sends(result, appt_id=None):
    return [r["send_at"] for r in result if appt_id is None or r["appointment_id"] == appt_id]


class PlanRemindersTests(unittest.TestCase):

    def test_dst_boundary_2026_10_25(self):
        appt = _appt(starts_at=datetime(2026, 10, 26, 7, 30, tzinfo=DUBLIN))
        result = plan_reminders([appt], datetime(2026, 10, 20, tzinfo=UTC))
        self.assertEqual(
            _sends(result),
            [datetime(2026, 10, 24, 7, 30, tzinfo=UTC), datetime(2026, 10, 25, 20, 0, tzinfo=UTC)],
        )
        self.assertEqual(result[1]["send_at"].astimezone(DUBLIN).hour, 20)
        self.assertTrue(all("26/10/2026 at 07:30" in r["text"] for r in result))

    def test_quiet_hours_before_eight_move_to_previous_evening(self):
        appt = _appt(starts_at=datetime(2026, 10, 15, 9, 0, tzinfo=DUBLIN))
        result = plan_reminders([appt], NOW)
        self.assertEqual(
            _sends(result),
            [datetime(2026, 10, 13, 8, 0, tzinfo=UTC), datetime(2026, 10, 14, 19, 0, tzinfo=UTC)],
        )

    def test_quiet_hours_boundaries_21_inside_and_08_outside(self):
        late = plan_reminders([_appt(id=3, starts_at=datetime(2026, 10, 15, 23, 0, tzinfo=DUBLIN))], NOW)
        self.assertIn(datetime(2026, 10, 15, 19, 0, tzinfo=UTC), _sends(late, 3))
        early = plan_reminders([_appt(id=4, starts_at=datetime(2026, 10, 15, 10, 0, tzinfo=DUBLIN))], NOW)
        self.assertIn(datetime(2026, 10, 15, 7, 0, tzinfo=UTC), _sends(early, 4))

    def test_past_48h_point_sends_first_reminder_at_now(self):
        now = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)
        appt = _appt(starts_at=datetime(2026, 10, 14, 13, 0, tzinfo=UTC))
        result = plan_reminders([appt], now)
        self.assertEqual(
            _sends(result),
            [now, datetime(2026, 10, 14, 11, 0, tzinfo=UTC)],
        )

    def test_quiet_moved_time_in_past_is_dropped(self):
        now = datetime(2026, 10, 13, 21, 30, tzinfo=UTC)
        appt = _appt(starts_at=datetime(2026, 10, 14, 13, 0, tzinfo=UTC))
        result = plan_reminders([appt], now)
        self.assertEqual(_sends(result), [datetime(2026, 10, 14, 11, 0, tzinfo=UTC)])
        self.assertTrue(all(r["send_at"] >= now for r in result))

    def test_optout_uses_email_only(self):
        result = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertTrue(result)
        self.assertTrue(all(r["channel"] == "email" for r in result))

    def test_optout_without_email_emits_nothing(self):
        result = plan_reminders([_appt(optout_sms_v2=True, email="")], NOW)
        self.assertEqual(result, [])

    def test_no_phone_uses_email(self):
        result = plan_reminders([_appt(phone="  ")], NOW)
        self.assertTrue(result)
        self.assertTrue(all(r["channel"] == "email" for r in result))

    def test_cancelled_and_past_appointments_skipped(self):
        self.assertEqual(plan_reminders([_appt(status="Cancelled ")], NOW), [])
        self.assertEqual(
            plan_reminders([_appt(starts_at=NOW - timedelta(hours=1))], NOW), []
        )

    def test_sms_shortening_keeps_date_and_time(self):
        long_name = "Anastasia " + "Z" * 150
        result = plan_reminders([_appt(customer_name=long_name)], NOW)
        sms = [r for r in result if r["channel"] == "sms"]
        self.assertTrue(sms)
        for r in sms:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("14/10/2026 at 14:00", r["text"])
            self.assertIn("Hi Anastasia.", r["text"])
            self.assertTrue(r["text"].endswith(SIG_DEFAULT))
            self.assertNotIn("Z" * 10, r["text"])

    def test_sms_truncation_fills_limit_and_keeps_time(self):
        result = plan_reminders([_appt(customer_name="A" * 300)], NOW)
        sms = [r for r in result if r["channel"] == "sms"]
        self.assertTrue(sms)
        for r in sms:
            self.assertEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("14/10/2026 at 14:00", r["text"])

    def test_full_name_kept_when_it_fits(self):
        result = plan_reminders([_appt()], NOW)
        self.assertTrue(all("Hi Aoife Byrne." in r["text"] for r in result if r["channel"] == "sms"))

    def test_email_has_no_length_limit(self):
        long_name = "Anastasia " + "Z" * 150
        result = plan_reminders([_appt(customer_name=long_name, optout_sms_v2=True)], NOW)
        self.assertTrue(result)
        for r in result:
            self.assertIn(long_name, r["text"])
            self.assertGreater(len(r["text"]), SMS_LIMIT)

    def test_polish_signature_for_pl(self):
        result = plan_reminders([_appt(country="PL")], NOW)
        self.assertTrue(all(r["text"].endswith(SIG_PL) for r in result))

    def test_sorting_by_send_at_then_id_then_channel(self):
        a = _appt(id=2)
        b = _appt(id=1, optout_sms_v2=True)
        result = plan_reminders([a, b], NOW)
        self.assertEqual(
            [(r["appointment_id"], r["channel"]) for r in result[:2]],
            [(1, "email"), (2, "sms")],
        )
        keys = [r["send_at"] for r in result]
        self.assertEqual(keys, sorted(keys))

    def test_logs_one_line_per_reminder_without_contact_data(self):
        with self.assertLogs(log.name, level="INFO") as cm:
            result = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual(len(cm.records), len(result))
        joined = "\n".join(cm.output)
        self.assertNotIn(EMAIL, joined)
        self.assertNotIn("Aoife", joined)
        self.assertNotIn("+353", joined)


if __name__ == "__main__":
    unittest.main()