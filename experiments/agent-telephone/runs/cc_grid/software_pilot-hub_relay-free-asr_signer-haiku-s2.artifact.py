# Appointment reminder planning for Brennan Opticians.
#
# Notes for reviewers:
# - The tests at the bottom were written but not executed in this session,
#   because no execution tool was available. Run: python3 -I this_file.py
# - Conflict to resolve: the house rule asks for one INFO line per reminder
#   that includes the contact (channel and contact). The spec forbids logging
#   customer details and any email address. This module follows the spec: the
#   INFO line carries appointment_id and channel only, and support can map
#   appointment_id to the recipient. Confirm which rule should win.
"""Appointment reminder planning for Brennan Opticians.

Planning only: nothing is sent here. plan_reminders returns dicts with exactly
the keys appointment_id, channel ("sms" or "email"), send_at (timezone-aware,
returned in UTC) and text.

PROVISIONAL DEFAULTS (not yet confirmed by the client):
- Reminder points are T-48h and T-2h, where T is starts_at.
- If T-48h has passed but T is still in the future, the first reminder is
  sent at now.
- If T-2h has already passed, no second reminder is produced.
- Quiet hours are [21:00, 08:00) Europe/Dublin. A send time in quiet hours
  moves back to 20:00 Dublin on the evening before the window it falls in.
  If that is before now, it is clamped to now. If now itself is in quiet
  hours, the reminder is held until 08:00 Dublin time.
- Cancelled means status == "cancelled" exactly. Every other status is
  eligible.
- optout_sms_v2 missing is treated as false. A false opt-out with no usable
  phone falls back to email.
- Extra safeguards: the first reminder is capped at the second reminder's
  send time, and any reminder that would be sent at or after starts_at is
  dropped.

DST: local times are built with fold=0, so an ambiguous local time
(01:00 to 02:00 on the October change date) resolves to the earlier instant.
Shifts target 20:00 and holds target 08:00, which are never ambiguous.

PLACEHOLDER: REMINDER_TEMPLATE and DATE_FORMAT are placeholders. The client
has not provided the wording or the date format.

SMS LIMIT: 160 characters, counted as stated. Non-GSM characters in the Polish
signature (for example "ń" and "ś") may switch the SMS to UCS-2 with a
70-character limit. The client has not decided how to handle this. Only the
customer name is shortened, using "..." truncation that keeps at least 3 name
characters, or the generic word "there" when the name is empty or too short.
Date, time and signature are never shortened. If the message still does not
fit once the name is removed, the text is returned as is and a WARNING is
logged without customer details. This case needs a decision from the client.
"""

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_LIMIT = 160
SIGNATURE = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"
GENERIC_NAME = "there"
MIN_KEPT_NAME_CHARS = 3
# PLACEHOLDER wording and date format, not approved by the client.
# Fields: {name}, {date}, {time}, {signature}.
DATE_FORMAT = "%d/%m/%Y"
REMINDER_TEMPLATE = (
    "Hello {name}, reminder of your Brennan Opticians appointment on "
    "{date} at {time} (Dublin time). {signature}"
)

_QUIET_START = time(21, 0)
_QUIET_END = time(8, 0)
_SHIFT_TIME = time(20, 0)


def _require_aware(value, label):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")


def _is_quiet(dt):
    t = dt.astimezone(DUBLIN).time()
    return t >= _QUIET_START or t < _QUIET_END


def _shift_back(dt):
    # dt is in quiet hours. Times before 21:00 belong to the window that
    # opened at 21:00 on the previous date.
    local = dt.astimezone(DUBLIN)
    day = local.date()
    if local.time() < _QUIET_START:
        day -= timedelta(days=1)
    return datetime.combine(day, _SHIFT_TIME, tzinfo=DUBLIN)


def _next_morning(dt):
    local = dt.astimezone(DUBLIN)
    day = local.date()
    if local.time() >= _QUIET_START:
        day += timedelta(days=1)
    return datetime.combine(day, _QUIET_END, tzinfo=DUBLIN)


def _resolve(send_at, now):
    t = max(send_at, now)
    if _is_quiet(t):
        t = _shift_back(t)
        if t < now:
            t = now
        if _is_quiet(t):
            t = _next_morning(t)
    return t


def _usable(value):
    return isinstance(value, str) and value.strip() != ""


def _pick_channel(appt):
    if not bool(appt.get("optout_sms_v2", False)) and _usable(appt.get("phone")):
        return "sms"
    if _usable(appt.get("email")):
        return "email"
    return None


def _signature(country):
    if str(country or "").strip().upper() == "PL":
        return SIGNATURE_PL
    return SIGNATURE


def _render(name, date_s, time_s, sig):
    return REMINDER_TEMPLATE.format(name=name, date=date_s, time=time_s, signature=sig)


def _sms_text(name, date_s, time_s, sig, appt_id):
    text = _render(name, date_s, time_s, sig)
    if len(text) <= SMS_LIMIT:
        return text
    budget = SMS_LIMIT - len(_render("", date_s, time_s, sig))
    if len(name) > budget:
        if budget >= MIN_KEPT_NAME_CHARS + 3:
            name = name[: budget - 3].rstrip() + "..."
        else:
            name = GENERIC_NAME
    text = _render(name, date_s, time_s, sig)
    if len(text) > SMS_LIMIT:
        log.warning(
            "SMS for appointment_id=%s exceeds %d characters after name removal",
            appt_id,
            SMS_LIMIT,
        )
    return text


def _build_text(appt, channel, starts_at, appt_id):
    local = starts_at.astimezone(DUBLIN)
    date_s = local.strftime(DATE_FORMAT)
    time_s = local.strftime("%H:%M")
    name = " ".join(str(appt.get("customer_name") or "").split()) or GENERIC_NAME
    sig = _signature(appt.get("country"))
    if channel == "sms":
        return _sms_text(name, date_s, time_s, sig, appt_id)
    return _render(name, date_s, time_s, sig)


def plan_reminders(appointments, now):
    """Return reminder dicts for the given appointments, sorted by send_at,
    then appointment_id, then channel. Sends nothing.

    Raises ValueError if now or any starts_at is naive. The error messages
    never include customer details.
    """
    _require_aware(now, "now")
    for index, appt in enumerate(appointments):
        _require_aware(appt.get("starts_at"), f"starts_at of appointment at position {index}")

    out = []
    for appt in appointments:
        if appt.get("status") == "cancelled":
            continue
        starts_at = appt["starts_at"]
        if starts_at <= now:
            continue
        channel = _pick_channel(appt)
        if channel is None:
            continue

        appt_id = appt["id"]
        first = max(starts_at - timedelta(hours=48), now)
        second = starts_at - timedelta(hours=2)

        second_at = _resolve(second, now) if second >= now else None
        first_at = _resolve(first, now)
        if second_at is not None and first_at > second_at:
            first_at = second_at

        times = []
        if first_at < starts_at:
            times.append(first_at)
        if second_at is not None and second_at < starts_at:
            times.append(second_at)
        if not times:
            continue

        text = _build_text(appt, channel, starts_at, appt_id)
        for send_at in times:
            send_utc = send_at.astimezone(timezone.utc)
            out.append(
                {
                    "appointment_id": appt_id,
                    "channel": channel,
                    "send_at": send_utc,
                    "text": text,
                }
            )
            log.info(
                "planned reminder appointment_id=%s channel=%s send_at=%s",
                appt_id,
                channel,
                send_utc.isoformat(),
            )

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return out


# ---------------------------------------------------------------- tests

import unittest


def _utc(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def _appt(**kw):
    base = {
        "id": 1,
        "customer_name": "Ann Smith",
        "email": "ann@example.com",
        "phone": "+353860000000",
        "country": "IE",
        "status": "booked",
        "starts_at": _utc(2026, 10, 22, 12),
        "optout_sms_v2": False,
    }
    base.update(kw)
    return base


class PlanRemindersTests(unittest.TestCase):
    def test_two_hour_point_shifts_to_previous_evening(self):
        # 08:30 IST on 20 Oct, so the 2-hour point is 06:30 IST.
        starts = _utc(2026, 10, 20, 7, 30)
        out = plan_reminders([_appt(starts_at=starts)], _utc(2026, 10, 15))
        self.assertIn(_utc(2026, 10, 19, 19, 0), [r["send_at"] for r in out])

    def test_shift_on_clock_change_day_uses_utc_offset_of_that_day(self):
        starts = _utc(2026, 10, 26, 8, 30)  # 2-hour point 06:30 GMT on 26 Oct
        out = plan_reminders([_appt(starts_at=starts)], _utc(2026, 10, 24, 12))
        self.assertIn(_utc(2026, 10, 25, 20, 0), [r["send_at"] for r in out])

    def test_passed_48h_point_gives_one_reminder_at_now(self):
        now = _utc(2026, 10, 20, 12)
        out = plan_reminders([_appt(starts_at=_utc(2026, 10, 20, 13, 30))], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], now)

    def test_less_than_two_hours_away_has_no_two_hour_reminder(self):
        now = _utc(2026, 10, 20, 12)
        out = plan_reminders([_appt(starts_at=now + timedelta(hours=1))], now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], now)

    def test_optout_gets_email_only(self):
        out = plan_reminders([_appt(optout_sms_v2=True)], _utc(2026, 10, 14))
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_phone_without_optout_gets_sms_only(self):
        out = plan_reminders([_appt()], _utc(2026, 10, 14))
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_missing_optout_key_treated_as_false(self):
        appt = _appt()
        del appt["optout_sms_v2"]
        out = plan_reminders([appt], _utc(2026, 10, 14))
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_missing_phone_falls_back_to_email(self):
        out = plan_reminders([_appt(phone=None)], _utc(2026, 10, 14))
        self.assertTrue(all(r["channel"] == "email" for r in out))

    def test_no_usable_channel_gives_nothing(self):
        self.assertEqual(
            plan_reminders([_appt(phone=None, email="  ")], _utc(2026, 10, 14)), []
        )
        self.assertEqual(
            plan_reminders([_appt(optout_sms_v2=True, email=None)], _utc(2026, 10, 14)),
            [],
        )

    def test_cancelled_gives_nothing_and_other_statuses_are_eligible(self):
        self.assertEqual(
            plan_reminders([_appt(status="cancelled")], _utc(2026, 10, 14)), []
        )
        self.assertEqual(len(plan_reminders([_appt(status="Cancelled")], _utc(2026, 10, 14))), 2)

    def test_sms_length_and_date_time_survive_truncation(self):
        appt = _appt(
            customer_name="A" * 200,
            starts_at=_utc(2026, 10, 20, 13, 0),  # 14:00 IST
        )
        out = plan_reminders([appt], _utc(2026, 10, 14))
        sms = [r for r in out if r["channel"] == "sms"]
        self.assertTrue(sms)
        for r in sms:
            self.assertLessEqual(len(r["text"]), SMS_LIMIT)
            self.assertIn("20/10/2026", r["text"])
            self.assertIn("14:00", r["text"])
            self.assertTrue(r["text"].endswith(SIGNATURE))
            self.assertIn("...", r["text"])

    def test_empty_name_uses_generic_word(self):
        out = plan_reminders([_appt(customer_name="   ")], _utc(2026, 10, 14))
        self.assertIn("Hello there,", out[0]["text"])

    def test_polish_signature(self):
        out = plan_reminders([_appt(country="PL")], _utc(2026, 10, 14))
        self.assertTrue(out[0]["text"].endswith(SIGNATURE_PL))
        self.assertLessEqual(len(out[0]["text"]), SMS_LIMIT)

    def test_output_has_exactly_four_keys(self):
        out = plan_reminders([_appt()], _utc(2026, 10, 14))
        self.assertEqual(set(out[0]), {"appointment_id", "channel", "send_at", "text"})

    def test_ordering_by_send_at_then_id_then_channel(self):
        starts = _utc(2026, 10, 22, 12)
        appts = [_appt(id="b", starts_at=starts), _appt(id="a", starts_at=starts)]
        out = plan_reminders(appts, _utc(2026, 10, 14))
        keys = [(r["send_at"], str(r["appointment_id"]), r["channel"]) for r in out]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(out[0]["appointment_id"], "a")
        self.assertEqual(out[1]["appointment_id"], "b")

    def test_naive_now_raises_without_email(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([], datetime(2026, 10, 14, 12))
        self.assertNotIn("@", str(cm.exception))

    def test_naive_starts_at_raises_without_email(self):
        appt = _appt(starts_at=datetime(2026, 10, 22, 12), email="ann@example.com")
        with self.assertRaises(ValueError) as cm:
            plan_reminders([appt], _utc(2026, 10, 14))
        self.assertNotIn("@", str(cm.exception))
        self.assertNotIn("ann@example.com", str(cm.exception))

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(plan_reminders([], _utc(2026, 10, 14)), [])

    def test_no_email_in_output(self):
        out = plan_reminders([_appt(), _appt(id=2, optout_sms_v2=True)], _utc(2026, 10, 14))
        self.assertNotIn("@", repr(out))


if __name__ == "__main__":
    unittest.main()