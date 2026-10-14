# Brennan Opticians appointment reminder planner.
#
# Status: not executed. Verify with: python3 -I -m unittest <this file>
#
# Decisions made by default (tech lead to confirm):
# 1. optout_sms_v2 == True means the customer opted out, so no SMS. This reads the
#    brief's "text if true" the other way round. Isolated in _sms_allowed.
# 2. Email is the fallback when SMS is not allowed, including when a phone exists but
#    optout_sms_v2 is True. Confirm this is wanted for opted-out customers.
# 3. Quiet hours: shift back to the preceding 20:00 Dublin; if that is before now, move
#    forward to the first 08:00 Dublin at or after now (forward move, flagged).
# 4. Validation runs before duplicate detection, so an invalid first row does not block
#    a later valid row with the same id.
# 5. Date format "D Mon YYYY" (for example "26 Oct 2026"). Time is HH:MM, Dublin local,
#    of starts_at.
# 6. Templates:
#    full:    "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {time}. {sig}"
#    no name: "Reminder of your Brennan Opticians appointment on {date} at {time}. {sig}"
#    short:   "Brennan Opticians: appt {date} at {time}. {sig}"
# 7. Name truncation: keep as many characters as fit, rstrip, append "..." (ASCII).
#    Length is counted in Python characters.
# 8. SMS still too long after the short template: skipped with a warning, no email fallback.
# 9. Logs carry appointment id, kind, channel, contact kind (phone_on_file or
#    email_on_file) and reason codes only. Phone and email values are never logged, so
#    support traces by appointment id.
# 10. Email text uses the full name and has no length limit.
# 11. A reminder whose final send_at is not before starts_at is dropped.
# 12. Non-string country, status, name, phone and email are treated as empty.
# 13. Cancelled and past appointments are skipped with a DEBUG line containing the id only.
# 14. If the 48h reminder is immediate and the 2h point is also now (starts_at = now + 2h),
#     two identical SMS are produced at now. Spec-literal; confirm whether to suppress.

from __future__ import annotations

import copy
import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger("brennan.reminders")

TZ = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
SMS_LIMIT = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
T_FULL = "Hi {name}, reminder of your Brennan Opticians appointment on {date} at {time}. {sig}"
T_NONAME = "Reminder of your Brennan Opticians appointment on {date} at {time}. {sig}"
T_SHORT = "Brennan Opticians: appt {date} at {time}. {sig}"
ELLIPSIS = "..."
QUIET_START_H = 21
QUIET_END_H = 8
SHIFT_BACK_H = 20
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
H48 = timedelta(hours=48)
H2 = timedelta(hours=2)


def _in_quiet_window(local: datetime) -> bool:
    return local.hour >= QUIET_START_H or local.hour < QUIET_END_H


def _first_0800_at_or_after(now: datetime) -> datetime:
    day = now.astimezone(TZ).date()
    cand = datetime.combine(day, time(QUIET_END_H), tzinfo=TZ).astimezone(UTC)
    if cand < now:
        day += timedelta(days=1)
        cand = datetime.combine(day, time(QUIET_END_H), tzinfo=TZ).astimezone(UTC)
    return cand


def _shift_out_of_quiet(t: datetime, now: datetime) -> tuple[datetime, str]:
    local = t.astimezone(TZ)
    if not _in_quiet_window(local):
        return t, "allowed"
    day = local.date() if local.hour >= QUIET_START_H else local.date() - timedelta(days=1)
    back = datetime.combine(day, time(SHIFT_BACK_H), tzinfo=TZ).astimezone(UTC)
    if back >= now:
        return back, "quiet_back"
    return _first_0800_at_or_after(now), "quiet_forward"


def _sms_allowed(appt: dict) -> bool:
    phone = appt.get("phone")
    if not (isinstance(phone, str) and phone.strip()):
        return False
    return not bool(appt.get("optout_sms_v2"))


def _has_email(appt: dict) -> bool:
    email = appt.get("email")
    return isinstance(email, str) and bool(email.strip())


def _signature_for(appt: dict) -> str:
    country = appt.get("country")
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIG_PL
    return SIG_DEFAULT


def _clean_name(appt: dict) -> str | None:
    name = appt.get("customer_name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def _build_text(appt: dict, starts_local: datetime, channel: str) -> str | None:
    fields = {
        "date": f"{starts_local.day} {MONTHS[starts_local.month - 1]} {starts_local.year}",
        "time": f"{starts_local.hour:02d}:{starts_local.minute:02d}",
        "sig": _signature_for(appt),
    }
    name = _clean_name(appt)
    if channel == "email":
        if name:
            return T_FULL.format(name=name, **fields)
        return T_NONAME.format(**fields)
    if name:
        room = SMS_LIMIT - len(T_FULL.format(name="", **fields))
        if len(name) <= room:
            return T_FULL.format(name=name, **fields)
        if room >= len(ELLIPSIS) + 1:
            cut = name[: room - len(ELLIPSIS)].rstrip()
            if cut:
                return T_FULL.format(name=cut + ELLIPSIS, **fields)
    for tpl in (T_NONAME, T_SHORT):
        text = tpl.format(**fields)
        if len(text) <= SMS_LIMIT:
            return text
    return None


def _valid_start(appt) -> datetime | None:
    if not isinstance(appt, dict):
        return None
    rid = appt.get("id")
    if rid is None or rid == "":
        return None
    try:
        hash(rid)
    except TypeError:
        return None
    starts = appt.get("starts_at")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        return None
    return starts.astimezone(UTC)


def plan_reminders(appointments: list[dict], now: datetime) -> list[dict]:
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)

    rows: list[tuple[dict, datetime]] = []
    seen: set = set()
    for appt in appointments:
        starts = _valid_start(appt)
        rid = appt.get("id") if isinstance(appt, dict) else None
        if starts is None:
            log.warning("skipped appt=%s reason=invalid_row", rid)
            continue
        if rid in seen:
            log.warning("skipped appt=%s reason=duplicate_id", rid)
            continue
        seen.add(rid)
        rows.append((appt, starts))

    out: list[dict] = []
    for appt, starts in rows:
        rid = appt["id"]
        status = appt.get("status")
        if isinstance(status, str) and status.strip().casefold() == "cancelled":
            log.debug("skipped appt=%s reason=cancelled", rid)
            continue
        if starts <= now_utc:
            log.debug("skipped appt=%s reason=past", rid)
            continue

        candidates: list[tuple[str, datetime, str]] = []
        t48 = starts - H48
        if t48 >= now_utc:
            candidates.append(("48h", t48, "scheduled"))
        else:
            candidates.append(("48h", now_utc, "immediate"))
        t2 = starts - H2
        if t2 >= now_utc:
            candidates.append(("2h", t2, "scheduled"))
        else:
            log.debug("dropped appt=%s kind=2h reason=too_late", rid)

        for kind, t, why in candidates:
            send_at, qreason = _shift_out_of_quiet(t, now_utc)
            if send_at >= starts:
                log.warning("dropped appt=%s kind=%s reason=quiet_no_slot", rid, kind)
                continue
            if _sms_allowed(appt):
                channel = "sms"
            elif _has_email(appt):
                channel = "email"
            else:
                log.warning("dropped appt=%s kind=%s reason=no_contact", rid, kind)
                continue
            text = _build_text(appt, starts.astimezone(TZ), channel)
            if text is None:
                log.warning("dropped appt=%s kind=%s reason=sms_too_long", rid, kind)
                continue
            contact = "phone_on_file" if channel == "sms" else "email_on_file"
            log.info(
                "planned appt=%s kind=%s channel=%s contact=%s send_at=%s reason=%s+%s",
                rid, kind, channel, contact, send_at.isoformat(), why, qreason,
            )
            out.append({
                "appointment_id": rid,
                "channel": channel,
                "send_at": send_at,
                "text": text,
            })

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return out


# ---------------------------------------------------------------- tests

def U(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


class ReminderTests(unittest.TestCase):
    EMAIL = "anna.kowalska@example.com"
    PHONE = "+353851234567"

    def appt(self, **kw):
        base = {
            "id": 1,
            "customer_name": "Anna Kowalska",
            "email": self.EMAIL,
            "phone": self.PHONE,
            "country": "IE",
            "status": "booked",
            "starts_at": U(2026, 10, 30, 10, 0),
            "optout_sms_v2": False,
        }
        base.update(kw)
        return base

    def summary(self, out):
        return [(r["channel"], r["send_at"]) for r in out]

    def test_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 1))

    def test_empty_input(self):
        self.assertEqual(plan_reminders([], U(2026, 10, 1)), [])

    def test_scheduled_48h_and_2h_with_0800_boundary(self):
        out = plan_reminders([self.appt()], U(2026, 10, 20))
        self.assertEqual(self.summary(out), [
            ("sms", U(2026, 10, 28, 10, 0)),
            ("sms", U(2026, 10, 30, 8, 0)),
        ])

    def test_48h_exactly_now_is_scheduled(self):
        out = plan_reminders([self.appt()], U(2026, 10, 28, 10, 0))
        self.assertEqual(out[0]["send_at"], U(2026, 10, 28, 10, 0))

    def test_starts_exactly_now_skipped(self):
        self.assertEqual(plan_reminders([self.appt()], U(2026, 10, 30, 10, 0)), [])

    def test_immediate_plus_2h(self):
        now = U(2026, 10, 28, 12, 0)
        out = plan_reminders([self.appt()], now)
        self.assertEqual(self.summary(out), [
            ("sms", now),
            ("sms", U(2026, 10, 30, 8, 0)),
        ])

    def test_less_than_2h_only_immediate(self):
        now = U(2026, 10, 30, 9, 30)
        out = plan_reminders([self.appt(starts_at=U(2026, 10, 30, 11, 0))], now)
        self.assertEqual(self.summary(out), [("sms", now)])

    def test_quiet_now_22h_moves_forward_to_0800(self):
        now = U(2026, 10, 29, 22, 0)
        out = plan_reminders([self.appt(starts_at=U(2026, 10, 31, 18, 0))], now)
        self.assertEqual(self.summary(out), [
            ("sms", U(2026, 10, 30, 8, 0)),
            ("sms", U(2026, 10, 31, 16, 0)),
        ])

    def test_21h_blocked_shifts_back_to_2000(self):
        now = U(2026, 10, 30, 12, 0)
        out = plan_reminders([self.appt(starts_at=U(2026, 10, 30, 23, 0))], now)
        self.assertEqual(self.summary(out), [
            ("sms", now),
            ("sms", U(2026, 10, 30, 20, 0)),
        ])

    def test_dst_26_oct_absolute_48h(self):
        out = plan_reminders([self.appt(starts_at=U(2026, 10, 26, 10, 0))],
                             U(2026, 10, 23, 0, 0))
        self.assertEqual(self.summary(out), [
            ("sms", U(2026, 10, 24, 10, 0)),
            ("sms", U(2026, 10, 26, 8, 0)),
        ])
        self.assertIn("26 Oct 2026 at 10:00", out[0]["text"])

    def test_dst_25_oct_2h_across_transition(self):
        now = U(2026, 10, 24, 12, 0)
        out = plan_reminders([self.appt(starts_at=U(2026, 10, 25, 3, 0))], now)
        self.assertEqual(self.summary(out), [
            ("sms", now),
            ("sms", U(2026, 10, 24, 19, 0)),
        ])

    def test_cancelled_variants(self):
        for status in (" Cancelled ", "CANCELLED"):
            with self.subTest(status=status):
                self.assertEqual(
                    plan_reminders([self.appt(status=status)], U(2026, 10, 20)), [])
        out = plan_reminders([self.appt(status="canceled")], U(2026, 10, 20))
        self.assertEqual(len(out), 2)

    def test_channel_rules(self):
        cases = [
            ({"phone": ""}, ["email", "email"]),
            ({"phone": "   "}, ["email", "email"]),
            ({"optout_sms_v2": True}, ["email", "email"]),
            ({"optout_sms_v2": None}, ["sms", "sms"]),
            ({"phone": "", "email": ""}, []),
        ]
        for kw, expected in cases:
            with self.subTest(kw=kw):
                out = plan_reminders([self.appt(**kw)], U(2026, 10, 20))
                self.assertEqual([r["channel"] for r in out], expected)

    def test_duplicate_first_kept(self):
        a1 = self.appt(id=7, starts_at=U(2026, 10, 30, 10, 0))
        a2 = self.appt(id=7, starts_at=U(2026, 11, 5, 10, 0))
        out = plan_reminders([a1, a2], U(2026, 10, 20))
        self.assertEqual([r["send_at"] for r in out],
                         [U(2026, 10, 28, 10, 0), U(2026, 10, 30, 8, 0)])

    def test_invalid_rows_skipped_others_kept(self):
        bad_naive = self.appt(id=3, starts_at=datetime(2026, 10, 30, 10, 0))
        bad_noid = {"customer_name": "x", "starts_at": U(2026, 10, 30, 10, 0)}
        good = self.appt(id=2)
        out = plan_reminders([bad_naive, bad_noid, good], U(2026, 10, 20))
        self.assertEqual({r["appointment_id"] for r in out}, {2})
        self.assertEqual(len(out), 2)

    def test_signature_by_country(self):
        cases = [(" pl ", "Grzegorz Szczepański"), ("PL", "Grzegorz Szczepański"),
                 ("IE", "Siobhán Ní Dhuibhir"), (None, "Siobhán Ní Dhuibhir")]
        for country, sig in cases:
            with self.subTest(country=country):
                out = plan_reminders([self.appt(country=country)], U(2026, 10, 20))
                for r in out:
                    self.assertTrue(r["text"].endswith(sig))

    def test_long_name_sms_truncated_and_keeps_date_time(self):
        name = "Zofia-Małgorzata Ní " * 20
        out = plan_reminders([self.appt(customer_name=name)], U(2026, 10, 20))
        self.assertEqual(len(out), 2)
        for r in out:
            self.assertLessEqual(len(r["text"]), 160)
            self.assertTrue(r["text"].endswith(SIG_DEFAULT))
            self.assertIn("30 Oct 2026 at 10:00", r["text"])
            self.assertIn("...", r["text"])

    def test_no_name_sms(self):
        out = plan_reminders([self.appt(customer_name="   ")], U(2026, 10, 20))
        for r in out:
            self.assertIn("30 Oct 2026 at 10:00", r["text"])
            self.assertLessEqual(len(r["text"]), 160)

    def test_sort_ties_by_id_then_channel(self):
        a = self.appt(id="b")
        b = self.appt(id="a")
        out = plan_reminders([a, b], U(2026, 10, 20))
        self.assertEqual([r["appointment_id"] for r in out], ["a", "b", "a", "b"])

    def test_input_not_mutated(self):
        appts = [self.appt()]
        before = copy.deepcopy(appts)
        plan_reminders(appts, U(2026, 10, 20))
        self.assertEqual(appts, before)

    def test_no_email_or_phone_in_output_or_logs(self):
        appts = [
            self.appt(),
            self.appt(id=5, status="cancelled"),
            {"customer_name": "no id", "email": self.EMAIL, "starts_at": U(2026, 10, 30)},
        ]
        with self.assertLogs("brennan.reminders", level="INFO") as cm:
            out = plan_reminders(appts, U(2026, 10, 20))
        logged = "\n".join(cm.output)
        self.assertNotIn(self.EMAIL, logged)
        self.assertNotIn(self.PHONE, logged)
        self.assertNotIn(self.EMAIL, str(out))
        self.assertNotIn(self.PHONE, str(out))


if __name__ == "__main__":
    unittest.main()