"""Brennan Opticians reminder planner. Single module, stdlib only, Python 3.12.

Status: not executed. No interpreter was available, so the unittest suite below has not been run.
Run with: python3 -m unittest brennan_reminders -v

Deviations from the brief:
- One file instead of the brennan_reminders/ package and the tests/ directory. The output contract is a single module here.
- INFO logs carry appointment_id and channel only, not the contact address. The brief forbids contact data in logs, which conflicts with the house rule's "contact" wording.
- The brief does not define active statuses. ACTIVE_STATUSES below is an assumption.
- Both reminder kinds for one appointment share identical text.
- Tests are in this file, not in separate test_*.py files.

Open questions for the client (1 is blocking):
1. Polarity of optout_sms_v2. As written, True produces SMS. This has PECR/GDPR consent implications.
2. Phone-only customer with a False or absent flag. Currently no reminder (PHONE_ONLY_FALLBACK = None).
3. Quiet-hour fallback: move to 08:00 or drop? Is there a minimum lead time? 08:00 for an 08:30 appointment is weak.
4. Confirm 21:00 is inclusive and 08:00 is exclusive. Moving 08:00 to 20:00 the prior evening was an error in the architect's example.
5. Are 48h and 2h elapsed time (built) or wall-clock time? Wall-clock would shift reminders by an hour across 25 October.
6. Does the first-before-second dedupe rule generalise the now-only collapse rule (built as general)?
7. Unknown statuses are skipped with a WARNING (built). Should "canceled" count as cancelled (built: yes)? Which statuses are active?
8. One malformed record fails the whole batch (built). Or should it fail only itself?
9. The output has no recipient address. Is a recipient field wanted? Adding one changes the output contract.
10. send_at is returned in UTC (built). Or should it be Dublin?
11. appointment_id may be int or str (built: returned unchanged).
12. SMS segmentation: non-GSM characters such as á and Ó force 70 characters per segment, so the 160 cap is not one segment. Confirm the cap.
13. Email subject: most mail systems require one. None is built.
14. Email greeting: full name (built) or first name?
"""

import logging
import unittest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

log = logging.getLogger("brennan_reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START = time(21, 0)  # inclusive
QUIET_END = time(8, 0)  # exclusive
EVENING_TIME = time(20, 0)
MORNING_TIME = time(8, 0)
SMS_LIMIT = 160
ACTIVE_STATUSES = frozenset({"booked", "confirmed"})  # ASSUMPTION, see open question 7
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})

# PENDING CLIENT CONFIRMATION (blocking): literal client rule is optout_sms_v2 True -> sms.
SMS_WHEN_OPTOUT_FLAG = True
# PENDING CLIENT CONFIRMATION: phone-only customer with False or absent flag. None means no reminder.
PHONE_ONLY_FALLBACK = None

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
SMS_TEMPLATE = "Hi {name}, reminder: Brennan Opticians appointment on {date} at {time}. {signature}"
EMAIL_TEMPLATE = (
    "Dear {name}, this is a reminder of your appointment at Brennan Opticians "
    "on {date} at {time} (Irish time). Kind regards, {signature}"
)
REQUIRED = ("id", "customer_name", "email", "phone", "country", "status", "starts_at", "optout_sms_v2")
STR_FIELDS = ("customer_name", "email", "phone", "country", "status")


# ---------- validation ----------

def _aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _check_now(now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")


def _validate(rec, index):
    if not isinstance(rec, dict):
        raise ValueError(f"record {index}: not a mapping")
    for key in REQUIRED:
        if key not in rec:
            raise ValueError(f"record {index}: missing field '{key}'")
    aid = rec["id"]
    if isinstance(aid, bool) or not isinstance(aid, (str, int)):
        raise ValueError(f"record {index}: field 'id' has invalid type")
    if isinstance(aid, str) and not aid.strip():
        raise ValueError(f"record {index}: field 'id' is empty")
    for key in STR_FIELDS:
        if not isinstance(rec[key], str):
            raise ValueError(f"record {index}: field '{key}' has invalid type")
    if not rec["customer_name"].strip():
        raise ValueError(f"record {index}: field 'customer_name' is empty")
    if not _aware(rec["starts_at"]):
        raise ValueError(f"record {index}: field 'starts_at' must be a timezone-aware datetime")
    opt = rec["optout_sms_v2"]
    if opt is not None and not isinstance(opt, bool):
        raise ValueError(f"record {index}: field 'optout_sms_v2' must be bool or None")


# ---------- channels ----------

def normalise_status(status):
    return status.strip().casefold()


def choose_channel(phone, email, optout):
    phone = phone.strip()
    if phone and optout is SMS_WHEN_OPTOUT_FLAG:
        return "sms"
    if email.strip():
        return "email"
    if phone:
        return PHONE_ONLY_FALLBACK
    return None


# ---------- scheduling ----------

def is_quiet(utc_dt):
    t = utc_dt.astimezone(DUBLIN).time()
    return t >= QUIET_START or t < QUIET_END


def _dublin_at(d, t):
    return datetime.combine(d, t, tzinfo=DUBLIN).astimezone(UTC)


def schedule(nominal, now, starts):
    """Return (send_at_utc, None) or (None, reason). All arithmetic is on UTC instants."""
    candidate = max(nominal, now)
    if candidate >= starts:
        return None, "after_start"
    if not is_quiet(candidate):
        return candidate, None
    local = candidate.astimezone(DUBLIN)
    t = local.time()
    window_date = local.date() if t >= QUIET_START else local.date() - timedelta(days=1)
    evening = _dublin_at(window_date, EVENING_TIME)
    if evening >= now:
        sent = evening
    else:
        morning_date = local.date() if t < QUIET_END else local.date() + timedelta(days=1)
        sent = _dublin_at(morning_date, MORNING_TIME)
    if sent >= starts:
        return None, "dropped_quiet"
    return sent, None


# ---------- messages ----------

def fmt_date(local):
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}"


def fmt_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def signature(country):
    return SIG_PL if country.strip().casefold() == "pl" else SIG_DEFAULT


def _sms_name(name, budget):
    if len(name) <= budget:
        return name
    token = name.split()[0]
    if len(token) <= budget:
        return token
    keep = budget - 3
    return token[:keep] + "..." if keep > 0 else ""


def build_sms(name, date_s, time_s, sig):
    fixed = len(SMS_TEMPLATE.format(name="", date=date_s, time=time_s, signature=sig))
    shown = _sms_name(name, SMS_LIMIT - fixed)
    return SMS_TEMPLATE.format(name=shown, date=date_s, time=time_s, signature=sig)


def build_text(channel, name, country, local_start):
    name = name.strip()
    sig = signature(country)
    date_s = fmt_date(local_start)
    time_s = fmt_time(local_start)
    if channel == "sms":
        return build_sms(name, date_s, time_s, sig)
    return EMAIL_TEMPLATE.format(name=name, date=date_s, time=time_s, signature=sig)


# ---------- orchestration ----------

def _plan_one(rec, now):
    aid = rec["id"]
    status = normalise_status(rec["status"])
    if status in CANCELLED_STATUSES:
        log.debug("appointment_id=%s reason=cancelled", aid)
        return []
    if status not in ACTIVE_STATUSES:
        log.warning("appointment_id=%s unknown status=%s skipped", aid, status)
        return []
    starts = rec["starts_at"].astimezone(UTC)
    if starts <= now:
        log.debug("appointment_id=%s reason=past_start", aid)
        return []
    channel = choose_channel(rec["phone"], rec["email"], rec["optout_sms_v2"])
    if channel is None:
        log.debug("appointment_id=%s reason=no_channel", aid)
        return []

    scheduled = []
    for kind, offset in ((0, FIRST_OFFSET), (1, SECOND_OFFSET)):
        send, reason = schedule(starts - offset, now, starts)
        if send is None:
            log.debug("appointment_id=%s reason=%s kind=%d", aid, reason, kind)
            continue
        if not (now <= send < starts) or is_quiet(send):
            log.error("appointment_id=%s invariant failed", aid)
            continue
        scheduled.append((send, kind))

    if len(scheduled) == 2 and scheduled[0][0] >= scheduled[1][0]:
        log.debug("appointment_id=%s reason=deduped", aid)
        scheduled = scheduled[1:]

    if not scheduled:
        return []
    text = build_text(channel, rec["customer_name"], rec["country"], starts.astimezone(DUBLIN))
    out = []
    for send, kind in scheduled:
        log.info("planned reminder appointment_id=%s channel=%s", aid, channel)
        out.append((send, kind, {"appointment_id": aid, "channel": channel, "send_at": send, "text": text}))
    return out


def plan_reminders(appointments, now):
    _check_now(now)
    records = list(appointments)
    for i, rec in enumerate(records):
        _validate(rec, i)
    now_utc = now.astimezone(UTC)
    planned = []
    appts_with_reminders = 0
    for rec in records:
        items = _plan_one(rec, now_utc)
        if items:
            appts_with_reminders += 1
        planned.extend(items)
    planned.sort(key=lambda p: (p[0], str(p[2]["appointment_id"]), p[1]))
    log.info("planned %d reminders for %d appointments", len(planned), appts_with_reminders)
    return [p[2] for p in planned]


# ---------- tests ----------

def dub(*args):
    return datetime(*args, tzinfo=DUBLIN)


NOW = dub(2026, 10, 13)
MARKS = ("EMAILMARK@x.test", "PHONEMARK0871", "NAMEMARK Smith")


def rec(**kw):
    r = {
        "id": 1, "customer_name": "Aoife Murphy", "email": "a@example.com", "phone": "",
        "country": "IE", "status": "booked", "starts_at": dub(2026, 10, 20, 10), "optout_sms_v2": None,
    }
    r.update(kw)
    return r


class ScheduleTests(unittest.TestCase):
    def test_basic_no_move(self):
        out = plan_reminders([rec()], NOW)
        self.assertEqual([o["send_at"] for o in out],
                         [dub(2026, 10, 18, 10).astimezone(UTC), dub(2026, 10, 20, 8).astimezone(UTC)])

    def test_dst_elapsed_time(self):
        out = plan_reminders([rec(starts_at=dub(2026, 10, 26, 10))], NOW)
        self.assertIn(datetime(2026, 10, 24, 10, tzinfo=UTC), [o["send_at"] for o in out])

    def test_dst_quiet_move(self):
        starts = dub(2026, 10, 30, 10)
        send, _ = schedule(datetime(2026, 10, 25, 7, 30, tzinfo=UTC), NOW.astimezone(UTC), starts)
        self.assertEqual(send, datetime(2026, 10, 24, 19, tzinfo=UTC))

    def test_quiet_boundaries(self):
        cases = [((20, 59, 59), False), ((21, 0, 0), True), ((7, 59, 59), True), ((8, 0, 0), False)]
        for (h, m, s), expected in cases:
            self.assertEqual(is_quiet(dub(2026, 10, 14, h, m, s)), expected)

    def test_clamp_both_sent(self):
        out = plan_reminders([rec(starts_at=dub(2026, 10, 21, 10))], dub(2026, 10, 20, 12))
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["send_at"], dub(2026, 10, 20, 12).astimezone(UTC))

    def test_collapse_one_sent(self):
        out = plan_reminders([rec()], dub(2026, 10, 20, 9, 30))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], dub(2026, 10, 20, 9, 30).astimezone(UTC))

    def test_quiet_fallback_to_morning(self):
        out = plan_reminders([rec(starts_at=dub(2026, 10, 14, 8, 30))], dub(2026, 10, 13, 22))
        self.assertEqual([o["send_at"] for o in out], [dub(2026, 10, 14, 8).astimezone(UTC)])

    def test_quiet_fallback_drop(self):
        self.assertEqual(plan_reminders([rec(starts_at=dub(2026, 10, 14, 7, 30))], dub(2026, 10, 13, 22)), [])

    def test_cancelled_variants(self):
        for status in (" CANCELLED ", "canceled", " Canceled\t"):
            self.assertEqual(plan_reminders([rec(status=status)], NOW), [])

    def test_starts_equal_now(self):
        self.assertEqual(plan_reminders([rec(starts_at=NOW)], NOW), [])

    def test_channels(self):
        cases = [
            ("+353 1", "a@x.test", True, "sms"),
            ("   ", "a@x.test", True, "email"),
            ("+353 1", "a@x.test", False, "email"),
            ("+353 1", "a@x.test", None, "email"),
            ("+353 1", "  ", None, None),
            ("   ", "", True, None),
        ]
        for phone, email, flag, expected in cases:
            out = plan_reminders([rec(phone=phone, email=email, optout_sms_v2=flag)], NOW)
            self.assertEqual(out[0]["channel"] if out else None, expected)

    def test_old_opt_out_ignored(self):
        out = plan_reminders([rec(phone="+353 1", email="a@x.test", optout_sms_v2=None, opt_out=True)], NOW)
        self.assertEqual(out[0]["channel"], "email")

    def test_output_shape_and_sorting(self):
        recs = [rec(id=2), rec(id="10")]
        out = plan_reminders(list(reversed(recs)), NOW)
        self.assertTrue(all(set(o) == {"appointment_id", "channel", "send_at", "text"} for o in out))
        keys = [(o["send_at"], str(o["appointment_id"])) for o in out]
        self.assertEqual(keys, sorted(keys))

    def test_naive_datetimes_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13))
        with self.assertRaises(ValueError):
            plan_reminders([rec(starts_at=datetime(2026, 10, 20, 10))], NOW)


class MessageTests(unittest.TestCase):
    def test_date_format(self):
        self.assertEqual(fmt_date(dub(2026, 10, 5, 9)), "5 Oct 2026")

    def test_polish_signature(self):
        out = plan_reminders([rec(country=" pl ", phone="+48 1", optout_sms_v2=True)], NOW)
        self.assertTrue(out[0]["text"].endswith("Grzegorz Szczepański"))

    def test_sms_length_cases(self):
        names = ["A" * 500, "Zoë Ó Séaghdha Ünïcode", "Nospacesatall" * 20, "First " + "B" * 500]
        for name in names:
            out = plan_reminders([rec(customer_name=name, phone="+353 1", optout_sms_v2=True)], NOW)
            for o in out:
                self.assertLessEqual(len(o["text"]), SMS_LIMIT)
                self.assertIn("20 Oct 2026", o["text"])
                self.assertIn("at 10:00.", o["text"])
                self.assertTrue(o["text"].endswith("Siobhán Ní Dhuibhir"))

    def test_email_full_name_and_signature(self):
        out = plan_reminders([rec(customer_name=" Aoife Murphy ")], NOW)
        self.assertIn("Dear Aoife Murphy,", out[0]["text"])
        self.assertTrue(out[0]["text"].endswith("Siobhán Ní Dhuibhir"))


class RedactionTests(unittest.TestCase):
    def test_malformed_input_message_has_no_values(self):
        bad = rec(email=MARKS[0], phone=MARKS[1], customer_name=MARKS[2], optout_sms_v2=MARKS[1])
        with self.assertRaises(ValueError) as cm:
            plan_reminders([bad], NOW)
        for mark in MARKS:
            self.assertNotIn(mark, str(cm.exception))

    def test_unknown_status_logs_have_no_values(self):
        r = rec(status="weird", email=MARKS[0], phone=MARKS[1], customer_name=MARKS[2], optout_sms_v2=True)
        with self.assertLogs("brennan_reminders", level="DEBUG") as cm:
            out = plan_reminders([r], NOW)
        self.assertEqual(out, [])
        logged = "\n".join(cm.output)
        for mark in MARKS:
            self.assertNotIn(mark, logged)


if __name__ == "__main__":
    unittest.main()