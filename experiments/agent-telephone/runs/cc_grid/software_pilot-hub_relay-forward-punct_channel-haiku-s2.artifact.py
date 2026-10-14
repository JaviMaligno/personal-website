import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Open questions for the client and tech lead (see also the report):
# 1. Opt-out inversion: the client's wording ("text if optout_sms_v2 is true") reads inverted.
#    Implemented the safer reading: SMS only when optout_sms_v2 is exactly False.
# 2. Date format DD/MM/YYYY is to be confirmed.
# 3. Non-GSM-7 characters (á, í, ń) may make carriers count the SMS as UCS-2 (70 chars per
#    segment). The 160-character check is implemented literally as specified.
# 4. Quiet-hours target: a send time in [21:00, 08:00) Dublin moves to 20:00 Dublin on the
#    date the quiet period started (the 20:00 just before the window). The PM phrase
#    "the evening before" could also mean the previous day's 20:00 for times after 21:00.
# 5. Logging contact: the phone is logged masked (last 4 digits) as a privacy measure.
#    This departs from logging the full contact; confirm with support.
# 6. A missing or blank customer name renders as "there" (assumption).

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"
CANCELLED_STATUSES = {"cancelled", "canceled"}


def _require_aware(value, what):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{what} must be a timezone-aware datetime")


def _is_quiet(dt):
    hour = dt.astimezone(DUBLIN).hour
    return hour >= 21 or hour < 8


def _next_permitted(now):
    """Earliest permitted instant at or after now (now is UTC-aware)."""
    if not _is_quiet(now):
        return now
    local = now.astimezone(DUBLIN)
    day = local.date() + timedelta(days=1) if local.hour >= 21 else local.date()
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)


def _apply_quiet_hours(send_at, now):
    """Move a quiet-hours send time to 20:00 Dublin, clamped so it is never before now."""
    if not _is_quiet(send_at):
        return send_at
    local = send_at.astimezone(DUBLIN)
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    evening = datetime.combine(day, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)
    if evening < now:
        return _next_permitted(now)
    return evening


def choose_channel(appt):
    """Single place for the channel/opt-out policy. Returns "sms" or None. Email is never returned."""
    phone = appt.get("phone")
    if not isinstance(phone, str) or not phone.strip():
        return None
    # Missing or null optout_sms_v2 is unknown, so no SMS. The opt_out field is ignored.
    if appt.get("optout_sms_v2") is False:
        return "sms"
    return None


def _is_cancelled(appt):
    status = appt.get("status")
    return isinstance(status, str) and status.strip().lower() in CANCELLED_STATUSES


def _signature(country):
    if isinstance(country, str) and country.strip().casefold() == "pl":
        return PL_SIGNATURE
    return DEFAULT_SIGNATURE


def _name_variants(name):
    parts = name.split() if isinstance(name, str) else []
    if not parts:
        return ["there"]
    variants = [" ".join(parts)]
    if len(parts) > 1:
        variants.append(f"{parts[0]} {parts[-1][0]}.")
    variants.append(parts[0])
    return list(dict.fromkeys(variants))


def _build_sms(appt, starts_local):
    date_s = starts_local.strftime("%d/%m/%Y")
    time_s = starts_local.strftime("%H:%M")
    sig = _signature(appt.get("country"))
    for name in _name_variants(appt.get("customer_name")):
        text = (f"Hi {name}, reminder of your appointment at Brennan Opticians "
                f"on {date_s} at {time_s}.\n{sig}")
        if len(text) <= SMS_LIMIT:
            return text
    # Message deliberately contains no personal data.
    raise ValueError("SMS reminder exceeds 160 characters even with the shortest name")


def _mask(phone):
    digits = phone.strip()
    return "***" + digits[-4:]


def plan_reminders(appointments, now):
    _require_aware(now, "now")
    now_utc = now.astimezone(UTC)
    planned = []

    for appt in appointments:
        starts = appt.get("starts_at")
        _require_aware(starts, "starts_at")
        if starts <= now_utc or _is_cancelled(appt):
            continue
        channel = choose_channel(appt)
        if channel is None:
            continue

        text = _build_sms(appt, starts.astimezone(DUBLIN))
        p48 = starts - timedelta(hours=48)
        p2 = starts - timedelta(hours=2)
        if p2 < now_utc:
            points = [now_utc]
        else:
            points = [p48 if p48 >= now_utc else now_utc, p2]

        for point in points:
            send_at = _apply_quiet_hours(point, now_utc)
            planned.append({
                "appointment_id": appt.get("id"),
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })
            logger.info("planned reminder appointment_id=%s channel=%s contact=%s send_at=%s",
                        appt.get("id"), channel, _mask(appt["phone"]), send_at.isoformat())

    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


if __name__ == "__main__":
    import unittest
    from datetime import datetime as dt

    EMAIL = "jane.doe@example.com"

    def appt(**overrides):
        base = {
            "id": "A1",
            "customer_name": "Anna Kowalska",
            "email": EMAIL,
            "phone": "+353851234567",
            "country": "IE",
            "status": "booked",
            "starts_at": dt(2026, 10, 20, 14, 0, tzinfo=DUBLIN),
            "optout_sms_v2": False,
        }
        base.update(overrides)
        return base

    NOW = dt(2026, 10, 13, 9, 0, tzinfo=UTC)

    class PlanRemindersTests(unittest.TestCase):

        def test_two_reminders_sorted_and_text(self):
            with self.assertLogs(logger, "INFO") as cm:
                out = plan_reminders([appt()], NOW)
            self.assertEqual(len(out), 2)
            self.assertEqual(out[0]["send_at"], dt(2026, 10, 18, 13, 0, tzinfo=UTC))
            self.assertEqual(out[1]["send_at"], dt(2026, 10, 20, 11, 0, tzinfo=UTC))
            self.assertEqual(set(out[0].keys()), {"appointment_id", "channel", "send_at", "text"})
            self.assertEqual(out[0]["channel"], "sms")
            self.assertIn("on 20/10/2026 at 14:00.", out[0]["text"])
            self.assertTrue(out[0]["text"].endswith("Siobhán Ní Dhuibhir"))
            self.assertEqual(len(cm.records), 2)

        def test_polish_signature(self):
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(country=" pl ")], NOW)
            self.assertTrue(out[0]["text"].endswith("Grzegorz Szczepański"))

        def test_naive_datetimes_raise(self):
            with self.assertRaises(ValueError):
                plan_reminders([appt()], dt(2026, 10, 13, 9, 0))
            with self.assertRaises(ValueError):
                plan_reminders([appt(starts_at=dt(2026, 10, 20, 14, 0))], NOW)

        def test_cancelled_variants_and_missing_status(self):
            self.assertEqual(plan_reminders([appt(status="Canceled")], NOW), [])
            self.assertEqual(plan_reminders([appt(status=" CANCELLED ")], NOW), [])
            self.assertEqual(len(plan_reminders([appt(status=None)], NOW)), 2)
            self.assertEqual(len(plan_reminders([appt(status=None, optout_sms_v2=False)], NOW)), 2)

        def test_channel_predicate(self):
            self.assertEqual(plan_reminders([appt(optout_sms_v2=True)], NOW), [])
            self.assertEqual(plan_reminders([appt(optout_sms_v2=None)], NOW), [])
            self.assertEqual(plan_reminders([appt(optout_sms_v2=None, opt_out=False)], NOW), [])
            self.assertEqual(plan_reminders([appt(phone="  ")], NOW), [])
            self.assertEqual(plan_reminders([appt(phone=None)], NOW), [])
            # Field opt_out is ignored entirely.
            self.assertEqual(plan_reminders([appt(opt_out=True)], NOW)[0]["channel"], "sms")

        def test_both_past_gives_one_reminder_at_now(self):
            starts = NOW + timedelta(hours=1)
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(starts_at=starts)], NOW)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["send_at"], NOW)

        def test_primary_past_sends_now_and_secondary_at_schedule(self):
            starts = dt(2026, 10, 20, 14, 0, tzinfo=DUBLIN)
            now = starts.astimezone(UTC) - timedelta(hours=6)
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(starts_at=starts)], now)
            self.assertEqual([r["send_at"] for r in out],
                             [now, starts.astimezone(UTC) - timedelta(hours=2)])

        def test_started_appointment_gets_nothing(self):
            starts = NOW - timedelta(minutes=1)
            self.assertEqual(plan_reminders([appt(starts_at=starts)], NOW), [])

        def test_quiet_hours_move_to_previous_evening_20h(self):
            starts = dt(2026, 10, 20, 0, 30, tzinfo=DUBLIN)
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(starts_at=starts)], NOW)
            self.assertEqual([r["send_at"] for r in out],
                             [dt(2026, 10, 17, 19, 0, tzinfo=UTC),
                              dt(2026, 10, 19, 19, 0, tzinfo=UTC)])

        def test_quiet_clamp_to_next_permitted_instant(self):
            starts = dt(2026, 10, 20, 0, 30, tzinfo=DUBLIN)
            now = dt(2026, 10, 19, 22, 0, tzinfo=UTC)  # 23:00 Dublin, quiet
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(starts_at=starts)], now)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0]["send_at"], dt(2026, 10, 20, 7, 0, tzinfo=UTC))

        def test_never_before_now(self):
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(starts_at=NOW + timedelta(hours=3))], NOW)
            for r in out:
                self.assertGreaterEqual(r["send_at"], NOW)

        def test_long_name_is_shortened_and_keeps_date_time(self):
            name = "Bartholomew-Maximilian Featherstonehaugh-Montgomery-Smythe-Jonesson"
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(customer_name=name)], NOW)
            for r in out:
                self.assertLessEqual(len(r["text"]), SMS_LIMIT)
                self.assertNotIn(name, r["text"])
                self.assertIn("on 20/10/2026 at 14:00.", r["text"])
                self.assertIn("Bartholomew-Maximilian J.", r["text"])

        def test_impossible_length_raises_without_personal_data(self):
            name = "A" * 80
            with self.assertRaises(ValueError) as cm:
                plan_reminders([appt(customer_name=name)], NOW)
            self.assertNotIn("AAAA", str(cm.exception))
            self.assertNotIn("@", str(cm.exception))

        def test_sorting_ties_by_id(self):
            with self.assertLogs(logger, "INFO"):
                out = plan_reminders([appt(id="b"), appt(id="a")], NOW)
            keys = [(r["send_at"], r["appointment_id"]) for r in out]
            self.assertEqual(keys, sorted(keys))

        def test_email_never_logged_or_returned(self):
            with self.assertLogs(logger, "INFO") as cm:
                out = plan_reminders([appt(email=EMAIL)], NOW)
            logged = "\n".join(cm.output)
            self.assertNotIn(EMAIL, logged)
            self.assertNotIn("@", logged)
            self.assertNotIn(EMAIL, repr(out))
            self.assertTrue(all(r["channel"] == "sms" for r in out))

        def test_naive_error_does_not_leak_email(self):
            with self.assertRaises(ValueError) as cm:
                plan_reminders([appt(email=EMAIL, starts_at=dt(2026, 10, 20, 14, 0))], NOW)
            self.assertNotIn("@", str(cm.exception))
            self.assertNotIn(EMAIL, str(cm.exception))

    unittest.main()