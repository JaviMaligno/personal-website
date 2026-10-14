# reminders.py
"""Appointment reminder planning for Brennan Opticians (pure planning; logs one INFO line per planned reminder).

Not executed in the authoring session. Suggested layout: <new dir>/reminders.py and <new dir>/test_reminders.py, with the tests below saved as the second file.

Unconfirmed defaults (client sign-off pending), all named constants below:
  - DEFAULT_OPTOUT_SMS = True: missing or null optout_sms_v2 is treated as opted out of SMS.
  - DATE_FORMAT = "%d %b %Y" and TIME_FORMAT = "%H:%M".
  - QUIET_NOW_SEND_TIME = 08:00: when now is inside quiet hours and the shifted target is in the past, send at the next 08:00 Dublin (only if before starts_at).
  - MIN_REMINDER_GAP = 24h: added to satisfy spec case 14 (08:30 on 20 Oct, now 19 Oct 15:00 must give one SMS at 15:00, not a second at 19 Oct 20:00). Only clamped reminders can fall closer than 34h, so this only affects clamped cases. The later reminder is dropped.
  - The 2-hour reminder is sent immediately (at now) when its point has passed and now is outside quiet hours, unless it is within MIN_REMINDER_GAP of an earlier kept reminder.
  - Any optout_sms_v2 value other than False (e.g. "false", 0) is treated as opted out (fail closed).
  - Logging records appointment_id and channel only. The house rule asks for the contact too, but the privacy rule forbids logging contact details beyond the appointment ID, so the contact is omitted. Confirm with the client.

Flags for the report:
  - Polish characters (ń, ą, ę, etc.) are not GSM-7. The 160-character limit is measured as len(str), as the spec requires. Real GSM delivery will use UCS-2 and cut the effective limit to 70 characters, so messages with these characters may be split or billed as multi-part.
  - The 08:00 forward move for past targets in quiet hours is a default and needs sign-off.
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
CHANNEL_SMS = "sms"
CHANNEL_EMAIL = "email"
REMINDER_OFFSETS = (timedelta(hours=48), timedelta(hours=2))
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
QUIET_SHIFT_TIME = time(20, 0)
SMS_MAX_LENGTH = 160
PL_COUNTRY = "PL"

# Unconfirmed defaults.
DEFAULT_OPTOUT_SMS = True
DATE_FORMAT = "%d %b %Y"
TIME_FORMAT = "%H:%M"
QUIET_NOW_SEND_TIME = time(8, 0)
SIGNATURE = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szczepański"
MIN_REMINDER_GAP = timedelta(hours=24)


def _is_aware(value) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None


def _clean(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _opted_out_sms(value) -> bool:
    if value is None:
        return DEFAULT_OPTOUT_SMS
    return value is not False


def _pick_channel(appt: dict) -> str | None:
    if _clean(appt.get("phone")) and not _opted_out_sms(appt.get("optout_sms_v2")):
        return CHANNEL_SMS
    email = _clean(appt.get("email"))
    if email and "@" in email:
        return CHANNEL_EMAIL
    return None


def _is_quiet(local: datetime) -> bool:
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _shift_quiet(target_utc: datetime) -> datetime:
    local = target_utc.astimezone(DUBLIN)
    if not _is_quiet(local):
        return target_utc
    day = local.date() if local.time() >= QUIET_START else local.date() - timedelta(days=1)
    return datetime.combine(day, QUIET_SHIFT_TIME, tzinfo=DUBLIN).astimezone(UTC)


def _next_morning(now_utc: datetime) -> datetime:
    local = now_utc.astimezone(DUBLIN)
    day = local.date() if local.time() < QUIET_END else local.date() + timedelta(days=1)
    return datetime.combine(day, QUIET_NOW_SEND_TIME, tzinfo=DUBLIN).astimezone(UTC)


def _send_time(target_utc: datetime, now_utc: datetime) -> datetime:
    send = _shift_quiet(target_utc)
    if send >= now_utc:
        return send
    if not _is_quiet(now_utc.astimezone(DUBLIN)):
        return now_utc
    return _next_morning(now_utc)


def _kept_send_times(starts_utc: datetime, now_utc: datetime) -> list[datetime]:
    candidates = []
    for offset in REMINDER_OFFSETS:
        send = _send_time(starts_utc - offset, now_utc)
        if send < starts_utc:
            candidates.append(send)
    kept: list[datetime] = []
    for send in sorted(candidates):
        if kept and send - kept[-1] < MIN_REMINDER_GAP:
            continue
        kept.append(send)
    return kept


def _body(name: str, signature: str, starts: datetime) -> str:
    local = starts.astimezone(DUBLIN)
    greeting = f"Hi {name}. " if name else ""
    return (
        f"{greeting}Your appointment at Brennan Opticians is on "
        f"{local.strftime(DATE_FORMAT)} at {local.strftime(TIME_FORMAT)}. {signature}"
    )


def _sms_text(aid, name_parts: list[str], signature: str, starts: datetime) -> str:
    for name in (" ".join(name_parts), name_parts[0] if name_parts else "", ""):
        text = _body(name, signature, starts)
        if len(text) <= SMS_MAX_LENGTH:
            return text
    raise ValueError(
        f"SMS for appointment {aid!r} exceeds {SMS_MAX_LENGTH} characters even without a name"
    )


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    seen = set()
    planned = []
    for appt in appointments:
        aid = appt["id"]
        if aid in seen:
            raise ValueError(f"duplicate appointment id: {aid!r}")
        seen.add(aid)
        starts = appt["starts_at"]
        if not _is_aware(starts):
            raise ValueError(
                f"starts_at for appointment {aid!r} must be a timezone-aware datetime"
            )
        if _clean(appt.get("status")).lower() in CANCELLED_STATUSES:
            continue
        starts_utc = starts.astimezone(UTC)
        if starts_utc <= now_utc:
            continue
        channel = _pick_channel(appt)
        if channel is None:
            continue
        name_parts = _clean(appt.get("customer_name")).split()
        country = _clean(appt.get("country")).upper()
        signature = SIGNATURE_PL if country == PL_COUNTRY else SIGNATURE
        for send in _kept_send_times(starts_utc, now_utc):
            if channel == CHANNEL_SMS:
                text = _sms_text(aid, name_parts, signature, starts)
            else:
                text = _body(" ".join(name_parts), signature, starts)
            planned.append(
                {"appointment_id": aid, "channel": channel, "send_at": send, "text": text}
            )
            log.info(
                "planned reminder appointment_id=%s channel=%s send_at=%s",
                aid, channel, send.isoformat(),
            )
    planned.sort(key=lambda r: (r["send_at"], r["appointment_id"], r["channel"]))
    return planned


# ==== tests/test_reminders.py (save as a separate file; not executed) ====
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import reminders as r

D = ZoneInfo("Europe/Dublin")
U = timezone.utc
EMAIL = "ann.smith@example.com"
NOW = datetime(2026, 10, 13, 10, 0, tzinfo=D)


def dt(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=D)


def appt(**kw):
    a = {
        "id": "A1", "customer_name": "Ann Smith", "email": EMAIL, "phone": "0871234567",
        "country": "IE", "status": "booked", "starts_at": dt(2026, 10, 20, 14, 30),
        "optout_sms_v2": False,
    }
    a.update(kw)
    return a


class PlanTests(unittest.TestCase):
    def sends(self, out):
        return [x["send_at"] for x in out]

    def channels(self, out):
        return {x["channel"] for x in out}

    def test_standard(self):
        out = r.plan_reminders([appt()], NOW)
        self.assertEqual(self.sends(out), [dt(2026, 10, 18, 14, 30), dt(2026, 10, 20, 12, 30)])
        self.assertEqual(self.channels(out), {"sms"})

    def test_first_reminder_passed(self):
        out = r.plan_reminders([appt()], dt(2026, 10, 19, 10, 0))
        self.assertEqual(self.sends(out), [dt(2026, 10, 19, 10, 0), dt(2026, 10, 20, 12, 30)])

    def test_both_passed(self):
        out = r.plan_reminders([appt()], dt(2026, 10, 20, 12, 45))
        self.assertEqual(self.sends(out), [dt(2026, 10, 20, 12, 45)])

    def test_at_or_before_now(self):
        self.assertEqual(r.plan_reminders([appt(starts_at=NOW)], NOW), [])
        self.assertEqual(r.plan_reminders([appt(starts_at=dt(2026, 10, 12, 9))], NOW), [])

    def test_cancelled(self):
        for s in ("Cancelled", "canceled", " CANCELED "):
            self.assertEqual(r.plan_reminders([appt(status=s)], NOW), [])

    def test_optout_true_uses_email(self):
        out = r.plan_reminders([appt(optout_sms_v2=True)], NOW)
        self.assertEqual(self.channels(out), {"email"})
        self.assertEqual(len(out), 2)

    def test_legacy_opt_out_ignored(self):
        out = r.plan_reminders([appt(opt_out=True, optout_sms_v2=False)], NOW)
        self.assertEqual(self.channels(out), {"sms"})

    def test_missing_or_null_optout_defaults_to_opted_out(self):
        a = appt()
        del a["optout_sms_v2"]
        self.assertEqual(self.channels(r.plan_reminders([a], NOW)), {"email"})
        self.assertEqual(r.plan_reminders([appt(optout_sms_v2=None, email="")], NOW), [])

    def test_opted_out_no_email(self):
        self.assertEqual(r.plan_reminders([appt(optout_sms_v2=True, email="")], NOW), [])

    def test_no_phone_uses_email(self):
        out = r.plan_reminders([appt(phone="   ")], NOW)
        self.assertEqual(self.channels(out), {"email"})

    def test_no_usable_contact(self):
        self.assertEqual(r.plan_reminders([appt(phone=" ", email="no-at-sign")], NOW), [])

    def test_quiet_shift_both_reminders(self):
        out = r.plan_reminders([appt(starts_at=dt(2026, 10, 20, 23, 30))], NOW)
        self.assertEqual(self.sends(out), [dt(2026, 10, 18, 20, 0), dt(2026, 10, 20, 20, 0)])

    def test_early_morning_two_hour_shift(self):
        out = r.plan_reminders([appt(starts_at=dt(2026, 10, 20, 8, 30))], NOW)
        self.assertEqual(self.sends(out), [dt(2026, 10, 18, 8, 30), dt(2026, 10, 19, 20, 0)])

    def test_now_quiet_past_target_moves_to_0800(self):
        out = r.plan_reminders([appt(starts_at=dt(2026, 10, 20, 8, 30))], dt(2026, 10, 19, 22, 0))
        self.assertEqual(self.sends(out), [dt(2026, 10, 20, 8, 0)])

    def test_now_daytime_past_shifted_target_sends_now(self):
        out = r.plan_reminders([appt(starts_at=dt(2026, 10, 20, 8, 30))], dt(2026, 10, 19, 15, 0))
        self.assertEqual(self.sends(out), [dt(2026, 10, 19, 15, 0)])

    def test_quiet_boundaries(self):
        def local_shift(day, h, mi):
            t = r._shift_quiet(datetime(2026, 10, day, h, mi, tzinfo=D).astimezone(U))
            return t.astimezone(D)
        self.assertEqual(local_shift(20, 20, 59), dt(2026, 10, 20, 20, 59))
        self.assertEqual(local_shift(20, 21, 0), dt(2026, 10, 20, 20, 0))
        self.assertEqual(local_shift(20, 7, 59), dt(2026, 10, 19, 20, 0))
        self.assertEqual(local_shift(20, 8, 0), dt(2026, 10, 20, 8, 0))

    def test_dst_change(self):
        out = r.plan_reminders([appt(starts_at=dt(2026, 10, 26, 9, 0))], NOW)
        self.assertEqual(
            self.sends(out),
            [datetime(2026, 10, 24, 9, 0, tzinfo=U), datetime(2026, 10, 25, 20, 0, tzinfo=U)],
        )

    def test_sms_name_shortened_to_first_name(self):
        out = r.plan_reminders([appt(customer_name="Bartholomew " + "X" * 100)], NOW)
        t = out[0]["text"]
        self.assertIn("Bartholomew", t)
        self.assertNotIn("XXX", t)
        self.assertIn("20 Oct 2026 at 14:30", t)
        self.assertTrue(t.endswith("Chevonne Nee Divver"))
        self.assertLessEqual(len(t), 160)

    def test_sms_name_removed(self):
        out = r.plan_reminders([appt(customer_name="Q" * 200)], NOW)
        t = out[0]["text"]
        self.assertNotIn("QQQ", t)
        self.assertIn("20 Oct 2026 at 14:30", t)
        self.assertTrue(t.endswith("Chevonne Nee Divver"))
        self.assertLessEqual(len(t), 160)

    def test_pl_signature_sms_and_email(self):
        sms = r.plan_reminders([appt(country=" pl ")], NOW)[0]["text"]
        em_out = r.plan_reminders([appt(country="PL", phone="")], NOW)
        self.assertEqual(self.channels(em_out), {"email"})
        for t in (sms, em_out[0]["text"]):
            self.assertTrue(t.endswith("Grzegorz Szczepański"))

    def test_email_not_truncated(self):
        name = "Z" * 300
        out = r.plan_reminders([appt(phone="", customer_name=name)], NOW)
        t = out[0]["text"]
        self.assertIn(name, t)
        self.assertTrue(t.endswith("Chevonne Nee Divver"))

    def test_sorting_with_tie_breakers(self):
        apps = [appt(id="B", phone=""), appt(id="A", phone="")]
        out = r.plan_reminders(apps, NOW)
        self.assertEqual(out, sorted(out, key=lambda x: (x["send_at"], x["appointment_id"], x["channel"])))
        self.assertEqual([x["appointment_id"] for x in out], ["A", "B", "A", "B"])

    def test_output_shape(self):
        out = r.plan_reminders([appt()], NOW)
        self.assertTrue(out)
        for x in out:
            self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})
            self.assertIn(x["channel"], {"sms", "email"})
            self.assertEqual(x["send_at"].utcoffset().total_seconds(), 0)
            self.assertGreaterEqual(x["send_at"], NOW)
            self.assertIn("20 Oct 2026", x["text"])
            self.assertIn("14:30", x["text"])

    def test_naive_now_rejected_without_email(self):
        with self.assertRaises(ValueError) as cm:
            r.plan_reminders([appt()], datetime(2026, 10, 13, 10, 0))
        self.assertNotIn(EMAIL, str(cm.exception))

    def test_naive_starts_rejected_without_email(self):
        with self.assertRaises(ValueError) as cm:
            r.plan_reminders([appt(starts_at=datetime(2026, 10, 20, 14, 30))], NOW)
        self.assertNotIn(EMAIL, str(cm.exception))
        self.assertIn("A1", str(cm.exception))

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            r.plan_reminders([appt(), appt()], NOW)

    def test_no_email_in_text_or_errors(self):
        apps = [appt(), appt(id="A2", phone="", customer_name="Q" * 200, country="PL")]
        out = r.plan_reminders(apps, NOW)
        for x in out:
            self.assertNotIn(EMAIL, x["text"])
            self.assertNotIn("@", x["text"])
        with self.assertRaises(ValueError) as cm:
            r.plan_reminders([appt(starts_at=datetime(2026, 10, 20))], NOW)
        self.assertNotIn(EMAIL, str(cm.exception))

    def test_one_info_log_per_reminder_without_email(self):
        with self.assertLogs("reminders", level="INFO") as cm:
            out = r.plan_reminders([appt()], NOW)
        self.assertEqual(len(cm.records), len(out))
        self.assertNotIn(EMAIL, "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()