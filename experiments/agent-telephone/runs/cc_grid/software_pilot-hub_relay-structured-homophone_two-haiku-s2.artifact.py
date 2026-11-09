"""Brennan Opticians appointment reminder planning.

plan_reminders() is pure planning and sends nothing. It logs one INFO line per planned reminder with appointment_id, slot, channel and send_at.

Working assumptions for client confirmation:
A1. A missing or null optout_sms_v2 counts as opted out. Only a literal False allows SMS.
A2. Blank or whitespace-only phone and email strings count as absent.
A3. Email layout: optional "Dear {name}," line, the sentence, a line break, then the signature.
A4. SMS layout: "{name}, Brennan Opticians: appointment {d} {Mon} {yyyy} at HH:MM. {signature}". With the name omitted this is exactly the agreed SMS template.
A5. SMS name shortening order: full name, first name, first initial with a dot (e.g. "J."), then no name.
A6. SMS length is len() on the str, counting code points.
A7. R9 edge case: if the moved reminder 1 time is before now, send at the earliest permitted instant at or after now. If now is in the quiet window, that instant is the 08:00 that ends the window. If now is already permitted, it is now itself. Omit the reminder if that instant is not before starts_at.
A8. Country "PL" after trim and casefold selects the Polish signature.

Conflict for the tech lead: the house rule asks for the contact in each log line, but R11 forbids logging email addresses, phone numbers or names. This module logs appointment_id and channel only.

Not executed: no tool access was available, so the embedded tests have not been run.
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX_LEN = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
OFFSET_1 = timedelta(hours=48)
OFFSET_2 = timedelta(hours=2)
QUIET_FROM = time(21, 0)
QUIET_TO = time(8, 0)
EVENING = time(20, 0)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
MONTHS_SHORT = tuple(m[:3] for m in MONTHS)


def _is_aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _present(value):
    return isinstance(value, str) and value.strip() != ""


def _sms_allowed(optout_value):
    # A1: only a literal False permits SMS; None (missing or null) and True opt out.
    return optout_value is False


def _pick_channel(appt):
    if _present(appt.get("phone")) and _sms_allowed(appt.get("optout_sms_v2")):
        return "sms"
    if _present(appt.get("email")):
        return "email"
    return None


def _is_quiet(local):
    t = local.time()
    return t >= QUIET_FROM or t < QUIET_TO


def _move_back_to_evening(local):
    """R9: 21:00-23:59 goes back to 20:00 the same day; 00:00-07:59 to 20:00 the previous day."""
    day = local.date()
    if local.time() < QUIET_TO:
        day -= timedelta(days=1)
    return datetime.combine(day, EVENING, tzinfo=DUBLIN).astimezone(UTC)


def _earliest_permitted(now_utc):
    """A7: earliest permitted instant at or after now_utc."""
    local = now_utc.astimezone(DUBLIN)
    if not _is_quiet(local):
        return now_utc
    day = local.date()
    if local.time() >= QUIET_FROM:
        day += timedelta(days=1)
    return datetime.combine(day, QUIET_TO, tzinfo=DUBLIN).astimezone(UTC)


def _sms_text(full_name, local, sig):
    first = full_name.split()[0] if full_name else ""
    options = (full_name, first, f"{first[0]}." if first else "", "")
    when = f"{local.day} {MONTHS_SHORT[local.month - 1]} {local.year} at {local:%H:%M}"
    for name in options:
        prefix = f"{name}, " if name else ""
        text = f"{prefix}Brennan Opticians: appointment {when}. {sig}"
        if len(text) <= SMS_MAX_LEN:
            return text
    raise ValueError("SMS with date, time and signature exceeds 160 characters")


def _email_text(full_name, local, sig):
    greeting = f"Dear {full_name},\n" if full_name else ""
    when = (f"{WEEKDAYS[local.weekday()]} {local.day} "
            f"{MONTHS[local.month - 1]} {local.year} at {local:%H:%M}")
    return f"{greeting}Your appointment at Brennan Opticians is on {when}.\n{sig}"


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    entries = []

    for appt in appointments:
        appt_id = appt["id"]
        starts_at = appt["starts_at"]
        if not _is_aware(starts_at):
            raise ValueError(f"appointment {appt_id!r}: starts_at must be timezone-aware")

        status = str(appt.get("status") or "").strip().casefold()
        if status in ("cancelled", "canceled"):
            continue

        start = starts_at.astimezone(UTC)
        if start <= now_utc:
            continue

        channel = _pick_channel(appt)
        if channel is None:
            continue

        local_start = start.astimezone(DUBLIN)
        full_name = str(appt.get("customer_name") or "").strip()
        country = str(appt.get("country") or "").strip().casefold()
        sig = SIG_PL if country == "pl" else SIG_DEFAULT

        # Reminder 1: R4 clamp to now, then R9 with the A7 edge case.
        r1 = max(start - OFFSET_1, now_utc)
        local_r1 = r1.astimezone(DUBLIN)
        if _is_quiet(local_r1):
            moved = _move_back_to_evening(local_r1)
            r1 = moved if moved >= now_utc else _earliest_permitted(now_utc)
        if r1 >= start:
            r1 = None

        # Reminder 2: R9 only. Omitted if it falls before now (R5).
        r2 = start - OFFSET_2
        local_r2 = r2.astimezone(DUBLIN)
        if _is_quiet(local_r2):
            r2 = _move_back_to_evening(local_r2)
        if r2 < now_utc:
            r2 = None

        for slot, when in ((1, r1), (2, r2)):
            if when is None or when < now_utc:
                continue
            if channel == "sms":
                text = _sms_text(full_name, local_start, sig)
            else:
                text = _email_text(full_name, local_start, sig)
            entries.append((when, appt_id, slot, {
                "appointment_id": appt_id,
                "channel": channel,
                "send_at": when,
                "text": text,
            }))

    entries.sort(key=lambda e: (e[0], e[1], e[2]))
    for when, appt_id, slot, _ in entries:
        log.info("planned reminder appointment_id=%s slot=%d channel=%s send_at=%s",
                 appt_id, slot, _[ "channel"], when.isoformat())
    return [e[3] for e in entries]


# ---------------------------------------------------------------- tests

def _utc(*args):
    return datetime(*args, tzinfo=UTC)


def _appt(**overrides):
    base = {
        "id": "A1",
        "customer_name": "Aoife Murphy",
        "email": "patient1@example.com",
        "phone": "+353870000001",
        "country": "IE",
        "status": "booked",
        "starts_at": _utc(2026, 10, 20, 9, 30),
        "optout_sms_v2": False,
    }
    base.update(overrides)
    return base


NOW = _utc(2026, 10, 13, 12, 0)


class PlanRemindersTests(unittest.TestCase):

    def test_two_sms_reminders_and_exact_keys(self):
        r = plan_reminders([_appt()], NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual({x["channel"] for x in r}, {"sms"})
        self.assertEqual(set(r[0].keys()), {"appointment_id", "channel", "send_at", "text"})
        self.assertEqual(r[0]["send_at"], _utc(2026, 10, 18, 9, 30))
        self.assertEqual(r[1]["send_at"], _utc(2026, 10, 20, 7, 30))
        self.assertIn("10:30", r[0]["text"])

    def test_r4_reminder1_clamped_to_now(self):
        now = _utc(2026, 10, 19, 10, 0)
        start = _utc(2026, 10, 19, 16, 0)
        r = plan_reminders([_appt(starts_at=start)], now)
        self.assertEqual([x["send_at"] for x in r], [now, _utc(2026, 10, 19, 14, 0)])

    def test_r5_reminder2_omitted_when_in_past(self):
        now = _utc(2026, 10, 19, 10, 0)
        start = _utc(2026, 10, 19, 11, 0)
        r = plan_reminders([_appt(starts_at=start)], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], now)

    def test_no_reminders_when_start_not_after_now(self):
        self.assertEqual(plan_reminders([_appt(starts_at=NOW)], NOW), [])

    def test_r7_name_shortened_to_first_name(self):
        r = plan_reminders([_appt(customer_name="Jo " + "Z" * 150)], NOW)
        self.assertEqual(r[0]["text"],
                         "Jo, Brennan Opticians: appointment 20 Oct 2026 at 10:30. Siobhán Ní Dhuibhir")

    def test_r7_name_shortened_to_initial(self):
        r = plan_reminders([_appt(customer_name="Q" * 150 + " Smith")], NOW)
        self.assertEqual(r[0]["text"],
                         "Q., Brennan Opticians: appointment 20 Oct 2026 at 10:30. Siobhán Ní Dhuibhir")
        self.assertLessEqual(len(r[0]["text"]), SMS_MAX_LEN)

    def test_r9_dst_end_moves_back_across_transition(self):
        now = _utc(2026, 10, 22, 12, 0)
        start = _utc(2026, 10, 26, 9, 0)
        r = plan_reminders([_appt(starts_at=start)], now)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["send_at"], _utc(2026, 10, 24, 9, 0))
        self.assertEqual(r[1]["send_at"], _utc(2026, 10, 25, 20, 0))

    def test_r9_evening_move_and_edge_case(self):
        now = _utc(2026, 10, 19, 12, 0)
        start = _utc(2026, 10, 20, 22, 30)
        r = plan_reminders([_appt(starts_at=start)], now)
        self.assertEqual([x["send_at"] for x in r], [now, _utc(2026, 10, 20, 19, 0)])

    def test_r9_edge_case_quiet_now_uses_0800(self):
        now = _utc(2026, 10, 19, 22, 0)
        start = _utc(2026, 10, 20, 12, 0)
        r = plan_reminders([_appt(starts_at=start)], now)
        self.assertEqual([x["send_at"] for x in r],
                         [_utc(2026, 10, 20, 7, 0), _utc(2026, 10, 20, 10, 0)])

    def test_r9_edge_case_omitted_when_past_start(self):
        now = _utc(2026, 10, 19, 22, 0)
        start = _utc(2026, 10, 20, 6, 30)
        self.assertEqual(plan_reminders([_appt(starts_at=start)], now), [])

    def test_optout_true_or_missing_uses_email(self):
        r = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})
        self.assertTrue(r[0]["text"].startswith("Dear Aoife Murphy,\n"))
        missing = _appt()
        del missing["optout_sms_v2"]
        self.assertEqual({x["channel"] for x in plan_reminders([missing], NOW)}, {"email"})

    def test_blank_contacts_produce_nothing(self):
        self.assertEqual(plan_reminders([_appt(phone="  ", email="")], NOW), [])

    def test_pl_signature(self):
        r = plan_reminders([_appt(country=" pl ")], NOW)
        self.assertTrue(r[0]["text"].endswith(" Grzegorz Szczepański"))

    def test_cancelled_excluded(self):
        self.assertEqual(plan_reminders([_appt(status=" Canceled ")], NOW), [])

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([_appt()], datetime(2026, 10, 13, 12, 0))

    def test_naive_starts_at_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([_appt(starts_at=datetime(2026, 10, 20, 9, 30))], NOW)

    def test_ordering_and_tie_break(self):
        a = _appt(id="A1")
        b = _appt(id="B2", starts_at=_utc(2026, 10, 19, 15, 0))
        ids = [x["appointment_id"] for x in plan_reminders([a, b], NOW)]
        self.assertEqual(ids, ["B2", "A1", "B2", "A1"])

        x = _appt(id="B")
        y = _appt(id="A")
        ids = [r["appointment_id"] for r in plan_reminders([x, y], NOW)]
        self.assertEqual(ids, ["A", "B", "A", "B"])


if __name__ == "__main__":
    unittest.main()