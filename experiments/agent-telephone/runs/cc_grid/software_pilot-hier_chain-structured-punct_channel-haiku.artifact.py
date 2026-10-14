# Brennan Opticians appointment reminders (single module, standard library only).
#
# Notes for review:
# - Not executed. This session had no tool access, so the tests below are unverified.
#   Run with: python -m unittest <this_module_name>
# - Tests use unittest instead of pytest to stay within the standard library.
# - Acceptance test 1 uses a 12:00 start. A 09:00 start puts the 2-hour point at
#   07:00, which is inside the quiet window and contradicts the test's own assertion.
# - The house rule asks for recipient contact in each planned-reminder log line.
#   R10 and R23 forbid logging email, phone or name, so this module logs only the
#   appointment id and channel. The client requirement takes precedence.
# - R1 fixes the output keys to four fields with no contact, so the delivery layer
#   must map appointment_id to a contact itself.
# - A missing key (including optout_sms_v2) skips the appointment per R22. A present
#   but non-bool optout_sms_v2 counts as False per R15.
# - The "Hi, reminder" no-name template and the fixed-part check use a worst-case
#   date of "31 Sep 2026" and time "23:59".

import logging
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_MAX = 160
SIG_IE = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
T_NAME = "Hi {name}, reminder: your Brennan Opticians appointment is on {date} at {time}. {signature}"
T_NONAME = "Hi, reminder: your Brennan Opticians appointment is on {date} at {time}. {signature}"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
REQUIRED = ("id", "customer_name", "email", "phone", "country", "status", "starts_at", "optout_sms_v2")
OFFSETS = (timedelta(hours=48), timedelta(hours=2))


def _str(v):
    return v if isinstance(v, str) else ""


def _sms_intended(appt):
    # Single place defining the channel meaning (R15). Flip here if the client's meaning changes.
    return bool(_str(appt.get("phone")).strip()) and appt.get("optout_sms_v2") is True


def _is_cancelled(appt):
    status = appt.get("status")
    return isinstance(status, str) and status.strip().lower() in ("cancelled", "canceled")


def _already_started(starts_at, now):
    # Architect assumption R17, isolated here.
    return starts_at <= now


def _in_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _local(day, hour):
    # Build a Dublin wall-clock time and return it as a UTC instant (R19 DST handling).
    naive = datetime(day.year, day.month, day.day, hour, 0)
    return naive.replace(tzinfo=DUBLIN).astimezone(UTC)


def _quiet(t, now):
    """Apply R19. t and now are UTC-aware; returns UTC-aware t'."""
    local = t.astimezone(DUBLIN)
    if not _in_quiet(local):
        return t
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    target = _local(day, 20)
    if target >= now:
        return target
    now_local = now.astimezone(DUBLIN)
    if not _in_quiet(now_local):
        return now
    end_day = now_local.date() + timedelta(days=1) if now_local.hour >= 21 else now_local.date()
    return _local(end_day, 8)


def _fmt_date(local):
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}"


def _fmt_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def _signature(country):
    return SIG_PL if _str(country).strip().upper() == "PL" else SIG_IE


def _render(name, date, time, sig):
    if name:
        return T_NAME.format(name=name, date=date, time=time, signature=sig)
    return T_NONAME.format(date=date, time=time, signature=sig)


def _sms_text(full_name, date, time, sig):
    """Name shortening ladder (R20). Returns None if even the no-name text does not fit."""
    parts = full_name.split()
    candidates = []
    if parts:
        candidates.append(" ".join(parts))
    if len(parts) > 1:
        candidates.append(f"{parts[0]} {parts[-1][0]}.")
    if parts:
        candidates.append(parts[0])
    for cand in candidates:
        text = _render(cand, date, time, sig)
        if len(text) <= SMS_MAX:
            return text
    if parts:
        first = parts[0]
        for k in range(len(first) - 1, 0, -1):
            text = _render(first[:k] + "…", date, time, sig)
            if len(text) <= SMS_MAX:
                return text
    text = _render("", date, time, sig)
    return text if len(text) <= SMS_MAX else None


def _label(appt):
    if not isinstance(appt, dict) or "id" not in appt:
        return "<missing id>"
    return appt["id"] if isinstance(appt["id"], str) else "<invalid id>"


def _valid(appt):
    if not isinstance(appt, dict) or any(k not in appt for k in REQUIRED):
        return False
    if not isinstance(appt["id"], str):
        return False
    s = appt["starts_at"]
    return isinstance(s, datetime) and s.utcoffset() is not None


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)

    planned = []  # internal records with UTC send_at, sorted before output
    skipped = {}

    def skip(reason, appt_id, level=logging.INFO):
        skipped[reason] = skipped.get(reason, 0) + 1
        log.log(level, "skip id=%s reason=%s", appt_id, reason)

    for appt in appointments:
        if not _valid(appt):
            skip("invalid_appointment", _label(appt), logging.WARNING)
            continue
        appt_id = appt["id"]
        starts_at = appt["starts_at"].astimezone(UTC)

        if _is_cancelled(appt):
            skip("cancelled", appt_id)
            continue
        if _already_started(starts_at, now):
            skip("already_started", appt_id)
            continue

        if _sms_intended(appt):
            channel = "sms"
        elif _str(appt["email"]).strip():
            channel = "email"
        else:
            skip("no_contact_channel", appt_id, logging.WARNING)
            continue

        local_start = starts_at.astimezone(DUBLIN)
        date = _fmt_date(local_start)
        time = _fmt_time(local_start)
        sig = _signature(appt["country"])
        full = " ".join(_str(appt["customer_name"]).split())

        if channel == "sms":
            text = _sms_text(full, date, time, sig)
            if text is None:
                skip("sms_too_long", appt_id, logging.WARNING)
                continue
        else:
            text = _render(full, date, time, sig)

        sends = []
        for offset in OFFSETS:
            t = _quiet(max(starts_at - offset, now), now)
            if t >= starts_at:
                skip("after_start", appt_id)
                sends.append(None)
            else:
                sends.append(t)
        first, second = sends
        if first is not None and second is not None and first == second:
            first = None  # dedup: keep the 2-hour reminder

        for t in (first, second):
            if t is None:
                continue
            if t < now:
                skip("guard", appt_id, logging.ERROR)
                continue
            planned.append({"appointment_id": appt_id, "channel": channel,
                            "send_at_utc": t, "text": text})

    planned.sort(key=lambda r: (r["send_at_utc"], r["appointment_id"], r["channel"]))
    out = []
    for r in planned:
        log.info("planned channel=%s id=%s", r["channel"], r["appointment_id"])
        out.append({"appointment_id": r["appointment_id"], "channel": r["channel"],
                    "send_at": r["send_at_utc"].astimezone(DUBLIN), "text": r["text"]})

    n_sms = sum(1 for r in out if r["channel"] == "sms")
    log.info("summary planned_sms=%d planned_email=%d skipped=%s",
             n_sms, len(out) - n_sms, dict(sorted(skipped.items())))
    return out


# ---------------------------------------------------------------- tests (stdlib unittest)

PHONE = "+353870000001"
EMAIL = "aoife@example.com"


def D(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def _fixture(**kw):
    base = {"id": "A1", "customer_name": "Aoife Murphy", "email": EMAIL, "phone": PHONE,
            "country": "IE", "status": "booked", "starts_at": D(2026, 10, 18, 12),
            "optout_sms_v2": True}
    base.update(kw)
    return base


class ReminderTests(unittest.TestCase):
    NOW = D(2026, 10, 13, 12)

    def test_normal_offsets(self):
        r = plan_reminders([_fixture()], self.NOW)
        self.assertEqual([x["send_at"] for x in r], [D(2026, 10, 16, 12), D(2026, 10, 18, 10)])

    def test_one_hour_out_single_at_now(self):
        r = plan_reminders([_fixture(starts_at=self.NOW + timedelta(hours=1))], self.NOW)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], self.NOW)

    def test_thirty_minutes_out_single_at_now(self):
        r = plan_reminders([_fixture(starts_at=self.NOW + timedelta(minutes=30))], self.NOW)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], self.NOW)

    def test_started_gives_nothing(self):
        self.assertEqual(plan_reminders([_fixture(starts_at=self.NOW)], self.NOW), [])
        self.assertEqual(plan_reminders([_fixture(starts_at=self.NOW - timedelta(hours=1))], self.NOW), [])

    def test_cancelled_gives_nothing(self):
        for s in ("Cancelled", "canceled", " CANCELLED "):
            self.assertEqual(plan_reminders([_fixture(status=s)], self.NOW), [])

    def test_quiet_window_moves_to_0800(self):
        now = D(2026, 10, 13, 22)
        starts = D(2026, 10, 14, 9)
        r = plan_reminders([_fixture(starts_at=starts)], now)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["send_at"], D(2026, 10, 14, 8))
        self.assertLess(r[0]["send_at"], starts)

    def test_2230_pushed_to_2000(self):
        r = plan_reminders([_fixture(starts_at=D(2026, 10, 14, 0, 30))], D(2026, 10, 12, 12))
        self.assertIn(D(2026, 10, 13, 20), [x["send_at"] for x in r])

    def test_0300_pushed_to_previous_2000(self):
        r = plan_reminders([_fixture(starts_at=D(2026, 10, 14, 5))], D(2026, 10, 12, 12))
        self.assertIn(D(2026, 10, 13, 20), [x["send_at"] for x in r])

    def test_dst_transition(self):
        r = plan_reminders([_fixture(starts_at=D(2026, 10, 25, 9))], D(2026, 10, 20, 12))
        self.assertIn(D(2026, 10, 24, 20), [x["send_at"] for x in r])
        for x in r:
            self.assertEqual(x["send_at"].tzinfo, DUBLIN)

    def test_sms_length_and_signature(self):
        long_name = "Maximiliana Wolfgang-Ferdinanda Ní Mhuirí Kowalczyk-Szymańska"
        for sig in (SIG_IE, SIG_PL):
            text = _sms_text(long_name, "14 Oct 2026", "09:30", sig)
            self.assertIsNotNone(text)
            self.assertLessEqual(len(text), SMS_MAX)
            self.assertIn("14 Oct 2026 at 09:30", text)
            self.assertTrue(text.endswith(sig))
        self.assertEqual(_signature("pl "), SIG_PL)
        self.assertEqual(_signature("IE"), SIG_IE)

    def test_fixed_part_fits_both_signatures(self):
        for sig in (SIG_IE, SIG_PL):
            self.assertLessEqual(len(_render("", "31 Sep 2026", "23:59", sig)), SMS_MAX)

    def test_channels(self):
        starts = D(2026, 10, 18, 12)
        def chans(**kw):
            return [x["channel"] for x in plan_reminders([_fixture(starts_at=starts, **kw)], self.NOW)]
        self.assertEqual(chans(optout_sms_v2=True, email=EMAIL), ["sms", "sms"])
        self.assertEqual(chans(optout_sms_v2=False, email=EMAIL), ["email", "email"])
        self.assertEqual(chans(phone="", optout_sms_v2=True, email=EMAIL), ["email", "email"])
        self.assertEqual(chans(phone="", email=""), [])
        self.assertEqual(chans(opt_out=True, optout_sms_v2=False), ["email", "email"])

    def test_sorted_ascending(self):
        appts = [_fixture(id="B", starts_at=D(2026, 10, 18, 12)),
                 _fixture(id="C", starts_at=D(2026, 10, 17, 12))]
        sends = [x["send_at"] for x in plan_reminders(appts, self.NOW)]
        self.assertEqual(sends, sorted(sends))

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 12))

    def test_no_contact_details_in_logs(self):
        appts = [_fixture(id="X1"), _fixture(id="X2", phone="", email="", optout_sms_v2=False)]
        with self.assertLogs("brennan.reminders", level="DEBUG") as cm:
            plan_reminders(appts, self.NOW)
        text = "\n".join(cm.output)
        self.assertNotIn(EMAIL, text)
        self.assertNotIn(PHONE, text)
        self.assertNotIn("Aoife", text)


if __name__ == "__main__":
    unittest.main()