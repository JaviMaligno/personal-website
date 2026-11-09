"""Appointment reminder planner for Brennan Opticians.

Status: this file was written without executing it. Run the tests with:
    python3 -I <path-to-this-file>
Standard library only.

PROVISIONAL DECISIONS (change them in the "Decisions" block below):
1. optout_sms_v2 meaning is unconfirmed. SMS_ENABLED is False, so no SMS is sent
   to anyone until the client confirms. sms_opted_in() is the single predicate
   that decides SMS eligibility. Once confirmed, set SMS_ENABLED and
   OPTOUT_TRUE_MEANS_OPTED_OUT. The legacy opt_out field is never read.
2. Email is never produced (EMAIL_ENABLED is False). The email path exists and is
   gated by email_applies(). A reminder is never sent by both channels.
3. If the 2-hour point has already passed at now, the 2-hour reminder is dropped.
   The 48-hour reminder is sent at now if its point has passed.
4. Quiet hours: a send_at whose Europe/Dublin wall time is in [21:00, 08:00) moves
   to 20:00 on the same local day, as the spec says. For sends between 00:00 and
   07:59 this is a FORWARD move, not a back move. The client must confirm this.
   Any shifted send_at that is earlier than now, or at/after starts_at, is dropped.
   It is never moved to another allowed time.
5. Appointments with starts_at at or before now produce nothing. Statuses
   "cancelled" and "canceled" produce nothing. A missing or blank phone produces
   nothing, even if an email is present.
6. SMS length: len() of the final text (code points) must be <= 160. The signature
   and Polish/Irish names contain non-GSM characters, so the message is sent as UCS-2.
   A single UCS-2 SMS holds 70 characters, so a 160-character message goes out as
   concatenated parts (about 3 parts at 67 characters each). Cost and segment count
   are a consequence the PM should know about.
7. Name shortening order: full name, then first name, then first initial with a dot.
   If none fits, nothing is sent. A WARNING is logged with the appointment id only.
   The message is never truncated mid-text.
8. Logging: one INFO line per planned reminder with appointment_id, channel and
   send_at. The contact itself is NOT logged, because the privacy rule forbids
   logging emails and phone numbers. Support resolves the contact from appointment_id.
   Message bodies are never logged either, because they contain the customer name.
9. Empty customer name: the greeting uses "there".
10. Returned send_at values are UTC-aware. Results are sorted by
    (send_at, appointment_id as text, channel).
"""

from __future__ import annotations

import logging
import sys
import unittest
from datetime import datetime, time, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

LOG = logging.getLogger(__name__)

# ---- Decisions block: every provisional value lives here ----
DUBLIN = ZoneInfo("Europe/Dublin")
FIRST_REMINDER_ENABLED = True
FIRST_REMINDER_LEAD = timedelta(hours=48)
SECOND_REMINDER_ENABLED = True
SECOND_REMINDER_LEAD = timedelta(hours=2)
QUIET_START = time(21, 0)  # inclusive
QUIET_END = time(8, 0)  # exclusive
QUIET_SHIFT_TO = time(20, 0)
SMS_ENABLED = False  # PROVISIONAL: no SMS until opt-out semantics are confirmed
OPTOUT_TRUE_MEANS_OPTED_OUT = True  # PROVISIONAL: unconfirmed
EMAIL_ENABLED = False  # PROVISIONAL: client has not defined when email applies
SMS_MAX_CHARS = 160
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
TEMPLATE = "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {hhmm}. {signature}"
# ---- end decisions ----


def sms_opted_in(appt: dict) -> bool:
    """The single predicate that decides whether an SMS may be sent to this customer."""
    if not SMS_ENABLED:
        return False
    flagged = bool(appt.get("optout_sms_v2"))
    return (not flagged) if OPTOUT_TRUE_MEANS_OPTED_OUT else flagged


def email_applies(appt: dict) -> bool:
    """Placeholder until the client defines when email applies."""
    return EMAIL_ENABLED and bool(_clean(appt.get("email")))


def _clean(value) -> str:
    return " ".join(str(value or "").split())


def _signature(country) -> str:
    return SIGNATURE_PL if _clean(country).upper() == "PL" else SIGNATURE


def _name_candidates(name) -> list[str]:
    full = _clean(name)
    if not full:
        return ["there"]
    first = full.split(" ")[0]
    return [full, first, first[0] + "."]


def _render(name_part: str, starts_at: datetime, country) -> str:
    local = starts_at.astimezone(DUBLIN)
    return TEMPLATE.format(
        name=name_part,
        date=local.strftime("%Y-%m-%d"),
        hhmm=local.strftime("%H:%M"),
        signature=_signature(country),
    )


def _sms_text(name, starts_at: datetime, country) -> str | None:
    for candidate in _name_candidates(name):
        text = _render(candidate, starts_at, country)
        if len(text) <= SMS_MAX_CHARS:
            return text
    return None


def _in_quiet_hours(local_time: time) -> bool:
    return local_time >= QUIET_START or local_time < QUIET_END


def _apply_quiet_hours(send_at: datetime) -> datetime:
    local = send_at.astimezone(DUBLIN)
    if not _in_quiet_hours(local.time()):
        return send_at
    shifted = datetime(
        local.year, local.month, local.day,
        QUIET_SHIFT_TO.hour, QUIET_SHIFT_TO.minute,
        tzinfo=DUBLIN,
    )
    return shifted.astimezone(timezone.utc)


def _plan_one(appt: dict, now: datetime) -> list[dict]:
    appt_id = appt["id"]
    starts_at = appt["starts_at"]
    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise ValueError(f"starts_at of appointment {appt_id!r} must be timezone-aware")
    if _clean(appt.get("status")).lower() in CANCELLED_STATUSES:
        return []
    if starts_at <= now:
        return []
    if not _clean(appt.get("phone")):
        LOG.debug("no phone, no reminder: appointment_id=%s", appt_id)
        return []

    if sms_opted_in(appt):
        channel = "sms"
    elif email_applies(appt):
        channel = "email"
    else:
        LOG.debug("no permitted channel: appointment_id=%s", appt_id)
        return []

    name = appt.get("customer_name")
    country = appt.get("country")
    if channel == "sms":
        text = _sms_text(name, starts_at, country)
        if text is None:
            LOG.warning("SMS still too long after name shortening, not sent: appointment_id=%s", appt_id)
            return []
    else:
        text = _render(_name_candidates(name)[0], starts_at, country)

    send_times: list[datetime] = []
    if FIRST_REMINDER_ENABLED:
        send_times.append(max(starts_at - FIRST_REMINDER_LEAD, now))
    if SECOND_REMINDER_ENABLED:
        second = starts_at - SECOND_REMINDER_LEAD
        if second >= now:
            send_times.append(second)
        else:
            LOG.debug("2-hour point already passed, dropped: appointment_id=%s", appt_id)

    out: list[dict] = []
    for raw in send_times:
        send_at = _apply_quiet_hours(raw)
        if send_at < now or send_at >= starts_at:
            LOG.debug("reminder dropped after quiet-hour shift: appointment_id=%s", appt_id)
            continue
        LOG.info(
            "planned reminder: appointment_id=%s channel=%s send_at=%s "
            "recipient=appointment customer (contact withheld; look up by appointment_id)",
            appt_id, channel, send_at.isoformat(),
        )
        out.append({"appointment_id": appt_id, "channel": channel, "send_at": send_at, "text": text})
    return out


def plan_reminders(appointments: list[dict], now: datetime) -> list[dict]:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(timezone.utc)
    planned: list[dict] = []
    for appt in appointments:
        planned.extend(_plan_one(appt, now))
    planned.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return planned


# ---------------------------------------------------------------- tests

THIS = sys.modules[__name__]
UTC = timezone.utc


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def dub(*args) -> datetime:
    return datetime(*args, tzinfo=DUBLIN)


def make_appt(**overrides) -> dict:
    appt = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": "aoife.murphy@example.com",
        "phone": "+353861234567",
        "country": "IE",
        "status": "booked",
        "starts_at": dub(2026, 10, 20, 14, 0),
        "optout_sms_v2": False,
        "opt_out": True,  # stale legacy field, must be ignored
    }
    appt.update(overrides)
    return appt


class SmsOn(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.multiple(THIS, SMS_ENABLED=True)
        patcher.start()
        self.addCleanup(patcher.stop)


class InputTests(unittest.TestCase):
    def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([make_appt()], datetime(2026, 10, 13, 10, 0))

    def test_naive_starts_at_rejected_without_leaking_email(self):
        appt = make_appt(starts_at=datetime(2026, 10, 20, 14, 0))
        with self.assertRaises(ValueError) as cm:
            plan_reminders([appt], utc(2026, 10, 13, 10))
        self.assertNotIn("example.com", str(cm.exception))


class OptOutDefaultTests(unittest.TestCase):
    def test_provisional_default_sends_no_sms(self):
        self.assertEqual(plan_reminders([make_appt()], utc(2026, 10, 13, 10)), [])


class TimingTests(SmsOn):
    NOW = utc(2026, 10, 13, 10)

    def test_48h_and_2h_reminders(self):
        out = plan_reminders([make_appt()], self.NOW)
        self.assertEqual(
            [r["send_at"] for r in out],
            [utc(2026, 10, 18, 13), utc(2026, 10, 20, 11)],
        )
        self.assertTrue(all(r["channel"] == "sms" for r in out))

    def test_immediate_send_when_48h_passed(self):
        now = utc(2026, 10, 18, 14)  # 48h point was 13:00 UTC
        out = plan_reminders([make_appt()], now)
        self.assertEqual(out[0]["send_at"], now)
        self.assertEqual(out[1]["send_at"], utc(2026, 10, 20, 11))

    def test_2h_point_passed_drops_second_reminder(self):
        now = utc(2026, 10, 20, 12)  # 2h point was 11:00 UTC
        out = plan_reminders([make_appt()], now)
        self.assertEqual([r["send_at"] for r in out], [now])

    def test_scope_cut_drops_48h_first(self):
        with mock.patch.multiple(THIS, FIRST_REMINDER_ENABLED=False):
            out = plan_reminders([make_appt()], self.NOW)
        self.assertEqual([r["send_at"] for r in out], [utc(2026, 10, 20, 11)])

    def test_cancelled_produces_nothing(self):
        for status in ("cancelled", "canceled", "CANCELLED"):
            self.assertEqual(plan_reminders([make_appt(status=status)], self.NOW), [])

    def test_past_or_current_start_produces_nothing(self):
        self.assertEqual(plan_reminders([make_appt()], utc(2026, 10, 20, 13)), [])
        self.assertEqual(plan_reminders([make_appt()], utc(2026, 10, 21, 0)), [])

    def test_no_send_at_in_past(self):
        appts = [
            make_appt(id="A", starts_at=dub(2026, 10, 20, 14, 0)),
            make_appt(id="B", starts_at=dub(2026, 10, 19, 23, 30)),
            make_appt(id="C", starts_at=dub(2026, 10, 21, 8, 30)),
        ]
        for now in (utc(2026, 10, 13, 10), utc(2026, 10, 18, 14), utc(2026, 10, 19, 20, 30),
                    utc(2026, 10, 20, 10), utc(2026, 10, 21, 5, 45)):
            for r in plan_reminders(appts, now):
                self.assertGreaterEqual(r["send_at"], now)


class QuietHoursTests(SmsOn):
    def test_boundary_helper(self):
        self.assertEqual(THIS._apply_quiet_hours(dub(2026, 10, 21, 21, 0)), utc(2026, 10, 21, 19, 0))
        self.assertEqual(THIS._apply_quiet_hours(dub(2026, 10, 21, 20, 59, 59)), dub(2026, 10, 21, 20, 59, 59))
        self.assertEqual(THIS._apply_quiet_hours(dub(2026, 10, 21, 8, 0)), dub(2026, 10, 21, 8, 0))
        # Literal "same local day" rule: 07:59:59 moves forward to 20:00 that day.
        self.assertEqual(THIS._apply_quiet_hours(dub(2026, 10, 21, 7, 59, 59)), dub(2026, 10, 21, 20, 0))

    def test_quiet_shift_in_full_plan(self):
        appt = make_appt(starts_at=dub(2026, 10, 21, 23, 30))
        out = plan_reminders([appt], utc(2026, 10, 19, 12))
        self.assertEqual(
            [r["send_at"] for r in out],
            [dub(2026, 10, 19, 20, 0), dub(2026, 10, 21, 20, 0)],
        )

    def test_shifted_send_before_now_is_dropped_not_moved(self):
        out = plan_reminders([make_appt(starts_at=dub(2026, 10, 21, 23, 30))], utc(2026, 10, 19, 20, 30))
        self.assertEqual([r["send_at"] for r in out], [dub(2026, 10, 21, 20, 0)])


class DublinUtcTests(SmsOn):
    def test_0730_utc_is_0830_dublin_not_quiet(self):
        appt = make_appt(starts_at=dub(2026, 10, 21, 10, 30))
        out = plan_reminders([appt], utc(2026, 10, 20, 12))
        self.assertIn(utc(2026, 10, 21, 7, 30), [r["send_at"] for r in out])

    def test_2030_utc_is_2130_dublin_quiet(self):
        appt = make_appt(starts_at=dub(2026, 10, 21, 21, 30))
        out = plan_reminders([appt], utc(2026, 10, 20, 12))
        self.assertIn(dub(2026, 10, 21, 20, 0), [r["send_at"] for r in out])
        self.assertNotIn(utc(2026, 10, 21, 20, 30), [r["send_at"] for r in out])


class DstTests(SmsOn):
    def test_shift_after_clocks_go_back_uses_gmt(self):
        appt = make_appt(starts_at=dub(2026, 10, 27, 22, 0))
        out = plan_reminders([appt], utc(2026, 10, 25, 8))
        self.assertEqual(
            [r["send_at"] for r in out],
            [utc(2026, 10, 25, 20), utc(2026, 10, 27, 20)],
        )

    def test_shift_before_clocks_go_back_uses_ist(self):
        appt = make_appt(starts_at=dub(2026, 10, 26, 22, 0))
        out = plan_reminders([appt], utc(2026, 10, 23, 0))
        self.assertEqual(
            [r["send_at"] for r in out],
            [utc(2026, 10, 24, 19), utc(2026, 10, 26, 20)],
        )

    def test_ambiguous_hour_on_transition_day(self):
        appt = make_appt(starts_at=utc(2026, 10, 27, 0, 30))
        out = plan_reminders([appt], utc(2026, 10, 24, 12))
        self.assertEqual(
            [r["send_at"] for r in out],
            [utc(2026, 10, 25, 20), utc(2026, 10, 26, 20)],
        )


class TextTests(SmsOn):
    def test_pl_signature(self):
        out = plan_reminders([make_appt(country="PL")], utc(2026, 10, 13, 10))
        text = out[0]["text"]
        self.assertTrue(text.endswith("Grzegorz Szczepański"))
        self.assertIn("2026-10-20", text)
        self.assertIn("14:00", text)
        self.assertNotIn("Siobhán", text)

    def test_ie_signature(self):
        out = plan_reminders([make_appt(country="IE")], utc(2026, 10, 13, 10))
        self.assertTrue(out[0]["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_long_name_shortened_to_first_name(self):
        appt = make_appt(customer_name="Maximiliana " + "Q" * 100)
        out = plan_reminders([appt], utc(2026, 10, 13, 10))
        text = out[0]["text"]
        self.assertTrue(text.startswith("Hi Maximiliana, "))
        self.assertLessEqual(len(text), 160)
        self.assertIn("14:00", text)
        self.assertTrue(text.endswith("Siobhán Ní Dhuibhir"))

    def test_very_long_first_name_falls_back_to_initial(self):
        appt = make_appt(customer_name="Q" * 150 + " Smith")
        out = plan_reminders([appt], utc(2026, 10, 13, 10))
        text = out[0]["text"]
        self.assertTrue(text.startswith("Hi Q., "))
        self.assertLessEqual(len(text), 160)

    def test_unfittable_message_is_dropped_not_truncated(self):
        long_template = "Hi {name}. " + "z" * 160 + " {date} {hhmm} {signature}"
        with mock.patch.multiple(THIS, TEMPLATE=long_template):
            with self.assertLogs(THIS.LOG, level="WARNING"):
                out = plan_reminders([make_appt()], utc(2026, 10, 13, 10))
        self.assertEqual(out, [])


class OptOutAndPhoneTests(SmsOn):
    NOW = utc(2026, 10, 13, 10)

    def test_optout_true_blocks_sms(self):
        self.assertEqual(plan_reminders([make_appt(optout_sms_v2=True)], self.NOW), [])

    def test_optout_false_allows_sms(self):
        self.assertEqual(len(plan_reminders([make_appt(optout_sms_v2=False)], self.NOW)), 2)

    def test_predicate_flip_inverts_meaning(self):
        with mock.patch.multiple(THIS, OPTOUT_TRUE_MEANS_OPTED_OUT=False):
            out = plan_reminders([make_appt(optout_sms_v2=True)], self.NOW)
        self.assertEqual(len(out), 2)

    def test_missing_phone_produces_nothing_even_with_email(self):
        for phone in (None, "", "   "):
            self.assertEqual(plan_reminders([make_appt(phone=phone)], self.NOW), [])


class EmailPathTests(unittest.TestCase):
    def test_email_not_produced_by_default(self):
        self.assertEqual(plan_reminders([make_appt(optout_sms_v2=True)], utc(2026, 10, 13, 10)), [])

    def test_email_path_when_enabled_and_never_both(self):
        with mock.patch.multiple(THIS, EMAIL_ENABLED=True):
            out = plan_reminders([make_appt(optout_sms_v2=True)], utc(2026, 10, 13, 10))
            self.assertEqual(len(out), 2)
            self.assertTrue(all(r["channel"] == "email" for r in out))
        with mock.patch.multiple(THIS, EMAIL_ENABLED=True, SMS_ENABLED=True):
            out = plan_reminders([make_appt()], utc(2026, 10, 13, 10))
            self.assertTrue(all(r["channel"] == "sms" for r in out))


class SortTests(SmsOn):
    def test_sorted_by_send_at_then_id_then_channel(self):
        appts = [make_appt(id="B2"), make_appt(id="A1")]
        out = plan_reminders(appts, utc(2026, 10, 13, 10))
        self.assertEqual(
            [(r["appointment_id"], r["send_at"]) for r in out],
            [
                ("A1", utc(2026, 10, 18, 13)),
                ("B2", utc(2026, 10, 18, 13)),
                ("A1", utc(2026, 10, 20, 11)),
                ("B2", utc(2026, 10, 20, 11)),
            ],
        )


class PrivacyTests(SmsOn):
    def test_no_email_phone_or_name_in_logs(self):
        appts = [
            make_appt(),
            make_appt(id="A2", phone=None),
        ]
        with self.assertLogs(THIS.LOG, level="DEBUG") as cm:
            plan_reminders(appts, utc(2026, 10, 13, 10))
        joined = "\n".join(cm.output)
        self.assertNotIn("@", joined)
        self.assertNotIn("example.com", joined)
        self.assertNotIn("+353861234567", joined)
        self.assertNotIn("Aoife", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)