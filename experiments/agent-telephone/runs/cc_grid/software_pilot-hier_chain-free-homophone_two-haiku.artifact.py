# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-10yeqqi4/brennan_reminders/reminders.py
#
# STATUS: No file-writing or execution tools were available in this session.
# This module has NOT been written to disk and the tests have NOT been run.
# To verify, save both files into the brennan_reminders directory and run:
#     python3 -m unittest
#
# DECISION LOG (points the design did not fully cover)
# 1. Contact values are never logged. The house rule asks for "channel and
#    contact" on each planned-reminder INFO line, but the specification forbids
#    logging phone numbers and email addresses. The INFO line carries
#    appointment_id and channel; support traces deliveries by appointment_id.
# 2. The spec's example "07:00 local on 26 Oct goes to 19:00 UTC on 25 Oct" is
#    inconsistent with Europe/Dublin rules. Dublin returns to GMT at 01:00 UTC
#    on 25 Oct 2026, so 20:00 Dublin on 25 Oct is 20:00 UTC. ZoneInfo is used,
#    so this module returns 20:00 UTC and the test asserts that.
# 3. The generic SMS fallback reads "Hello, reminder of your ..." as specified,
#    so it uses its own template instead of substituting into "Hi {name},".
# 4. Duplicate ids: the first entry that passes validation is kept. Entries
#    that fail validation do not claim the id.
# 5. Past appointments (starts_at <= now) use reason "starts_passed".
# 6. Intake warnings carry only a list index (when no usable id exists) or the
#    id plus a reason code.
# 7. Skips and dropped slots are logged at DEBUG with id and reason; the INFO
#    summary holds counts per reason.
# 8. Sort key is (send_at, str(id), sequence) over tuples, so dicts are never
#    compared.
# 9. A non-string status is treated as no status and sent normally.
# 10. A missing, blank, or non-string customer_name uses the generic greeting.
# 11. A missing or non-string country uses the default signature.
# 12. An SMS that cannot fit even in generic form is skipped with a WARNING
#     carrying the id only (reason sms_too_long). Expected to be unreachable.
# 13. Email uses the full collapsed name and has no length limit.
# 14. An unhashable id is rejected at intake with reason bad_id.
#
# OPEN QUESTIONS (all pending client confirmation; defaults shown)
# - SECOND_OFFSET = 2 hours.
# - Date format "14 Oct 2026" and time format "16:00" (Dublin local).
# - Neither phone nor email: no reminder, reason no_contact.
# - SMS template with first-name fallback, then "Hello" fallback.
# - Other statuses (anything not cancelled) are sent normally.
# - Past appointments (starts_at <= now) produce no reminders.
# - Missing or non-bool optout_sms_v2 is treated as opted out.
# - Opted out with no email: no reminder, reason opted_out_no_email.
# - Forward move for an immediate send in quiet hours: next 08:00 Dublin.
# - Superseded rule: slot 1 dropped when its adjusted time is >= slot 2.
# - second_passed rule: slot 2 dropped when its nominal time is <= now.
# - Duplicate id rule: keep the first valid occurrence.
# - send_at is output in UTC.
# - Output has no recipient field; the sender must look up contact details by
#   appointment_id.
# - Email has no subject line.
# - SMS opt-out wording and sender ID for compliance (PECR, ComReg).
# - UCS-2 segment count and cost impact of diacritic names under the 160 cap.

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOG = logging.getLogger("brennan.reminders")

UTC = timezone.utc
DUBLIN = ZoneInfo("Europe/Dublin")

FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)  # PENDING client confirmation
QUIET_START_HOUR = 21  # 21:00 inclusive
QUIET_END_HOUR = 8  # 08:00 exclusive
BACK_CANDIDATE_HOUR = 20
SMS_LIMIT = 160
DEFAULT_SIGNATURE = "Siobhán Ní Dhuibhir"
PL_SIGNATURE = "Grzegorz Szczepański"
GENERIC_NAME = "Hello"
CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

SMS_TEMPLATE = ("Hi {name}, reminder of your Brennan Opticians appointment "
                "on {date} at {time}. {signature}")
SMS_TEMPLATE_GENERIC = ("{name}, reminder of your Brennan Opticians appointment "
                        "on {date} at {time}. {signature}")
EMAIL_TEMPLATE = ("Dear {name},\n\nThis is a reminder of your Brennan Opticians "
                  "appointment on {date} at {time}.\n\nKind regards,\n{signature}")
EMAIL_TEMPLATE_GENERIC = ("Hello,\n\nThis is a reminder of your Brennan Opticians "
                          "appointment on {date} at {time}.\n\nKind regards,\n{signature}")

GSM7_BASIC = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./"
              "0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
              "abcdefghijklmnopqrstuvwxyzäöñüà")
GSM7_EXTENSION = "\f^{}\\[~]|€"


def sms_encoding(text):
    ok = all(c in GSM7_BASIC or c in GSM7_EXTENSION for c in text)
    return "GSM-7" if ok else "UCS-2"


def _fmt_date(local):
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}"


def _fmt_time(local):
    return f"{local.hour:02d}:{local.minute:02d}"


def _is_quiet(utc_dt):
    hour = utc_dt.astimezone(DUBLIN).hour
    return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR


def _quiet_adjust(candidate, now):
    if not _is_quiet(candidate):
        return candidate
    local = candidate.astimezone(DUBLIN)
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    back = datetime(day.year, day.month, day.day, BACK_CANDIDATE_HOUR,
                    tzinfo=DUBLIN).astimezone(UTC)
    if back >= now:
        return back
    if not _is_quiet(now):
        return now
    local_now = now.astimezone(DUBLIN)
    if local_now.hour < QUIET_END_HOUR:
        day = local_now.date()
    else:
        day = local_now.date() + timedelta(days=1)
    return datetime(day.year, day.month, day.day, QUIET_END_HOUR,
                    tzinfo=DUBLIN).astimezone(UTC)


def _clean_name(raw):
    return " ".join(raw.split()) if isinstance(raw, str) else ""


def _signature(country):
    if isinstance(country, str) and country.strip().casefold() == "pl":
        return PL_SIGNATURE
    return DEFAULT_SIGNATURE


def _sms_text(full, first, date, time, sig):
    options = []
    if full:
        options.append(SMS_TEMPLATE.format(name=full, date=date, time=time, signature=sig))
    if first and first != full:
        options.append(SMS_TEMPLATE.format(name=first, date=date, time=time, signature=sig))
    options.append(SMS_TEMPLATE_GENERIC.format(name=GENERIC_NAME, date=date,
                                               time=time, signature=sig))
    for text in options:
        if len(text) <= SMS_LIMIT:
            return text
    return None


def _email_text(name, date, time, sig):
    if name:
        return EMAIL_TEMPLATE.format(name=name, date=date, time=time, signature=sig)
    return EMAIL_TEMPLATE_GENERIC.format(date=date, time=time, signature=sig)


def _warn_index(skipped, index, reason):
    skipped[reason] += 1
    LOG.warning("skipped entry index=%s reason=%s", index, reason)


def _warn_id(skipped, appt_id, reason):
    skipped[reason] += 1
    LOG.warning("skipped appointment_id=%s reason=%s", appt_id, reason)


def _intake(appointments, skipped):
    valid = []
    seen = set()
    for index, appt in enumerate(appointments):
        if not isinstance(appt, dict):
            _warn_index(skipped, index, "not_dict")
            continue
        appt_id = appt.get("id")
        if appt_id is None:
            _warn_index(skipped, index, "missing_id")
            continue
        try:
            hash(appt_id)
        except TypeError:
            _warn_index(skipped, index, "bad_id")
            continue
        starts = appt.get("starts_at")
        if starts is None:
            _warn_id(skipped, appt_id, "missing_starts_at")
            continue
        if not isinstance(starts, datetime):
            _warn_id(skipped, appt_id, "bad_starts_at")
            continue
        if starts.utcoffset() is None:
            _warn_id(skipped, appt_id, "naive_starts_at")
            continue
        if appt_id in seen:
            _warn_id(skipped, appt_id, "duplicate_id")
            continue
        seen.add(appt_id)
        valid.append((appt, appt_id, starts.astimezone(UTC)))
    return valid


def _skip_appt(skipped, appt_id, reason):
    skipped[reason] += 1
    LOG.debug("skipped appointment_id=%s reason=%s", appt_id, reason)
    return []


def _drop_slot(skipped, appt_id, seq, reason):
    skipped[reason] += 1
    LOG.debug("dropped reminder appointment_id=%s slot=%d reason=%s",
              appt_id, seq, reason)


def _resolve_channel(appt):
    phone = appt.get("phone")
    email = appt.get("email")
    has_phone = isinstance(phone, str) and phone.strip() != ""
    has_email = isinstance(email, str) and email.strip() != ""
    sms_allowed = appt.get("optout_sms_v2") is False
    if has_phone and sms_allowed:
        return "sms", None
    if has_email:
        return "email", None
    if has_phone:
        return None, "opted_out_no_email"
    return None, "no_contact"


def _slot_candidates(starts, now, appt_id, skipped):
    nominal1 = starts - FIRST_OFFSET
    nominal2 = starts - SECOND_OFFSET
    candidates = {1: now if nominal1 <= now else nominal1}
    if nominal2 <= now:
        _drop_slot(skipped, appt_id, 2, "second_passed")
    else:
        candidates[2] = nominal2
    kept = []
    for seq in (1, 2):
        if seq not in candidates:
            continue
        send_at = _quiet_adjust(candidates[seq], now)
        if send_at >= starts:
            _drop_slot(skipped, appt_id, seq, "reminder_after_start")
            continue
        kept.append((seq, send_at))
    if len(kept) == 2 and kept[0][1] >= kept[1][1]:
        _drop_slot(skipped, appt_id, 1, "superseded")
        kept = kept[1:]
    return kept


def _plan_appointment(appt, appt_id, starts, now, skipped):
    status = appt.get("status")
    if isinstance(status, str) and status.strip().casefold() in CANCELLED_STATUSES:
        return _skip_appt(skipped, appt_id, "cancelled")
    if starts <= now:
        return _skip_appt(skipped, appt_id, "starts_passed")
    channel, reason = _resolve_channel(appt)
    if channel is None:
        return _skip_appt(skipped, appt_id, reason)

    slots = _slot_candidates(starts, now, appt_id, skipped)
    name = _clean_name(appt.get("customer_name"))
    first = name.split(" ")[0] if name else ""
    sig = _signature(appt.get("country"))
    local = starts.astimezone(DUBLIN)
    date, time = _fmt_date(local), _fmt_time(local)

    out = []
    for seq, send_at in slots:
        if channel == "sms":
            text = _sms_text(name, first, date, time, sig)
            if text is None:
                _warn_id(skipped, appt_id, "sms_too_long")
                continue
            LOG.debug("sms encoding appointment_id=%s slot=%d encoding=%s",
                      appt_id, seq, sms_encoding(text))
        else:
            text = _email_text(name, date, time, sig)
        LOG.info("planned reminder appointment_id=%s channel=%s slot=%d",
                 appt_id, channel, seq)
        record = {"appointment_id": appt_id, "channel": channel,
                  "send_at": send_at, "text": text}
        out.append((send_at, appt_id, seq, record))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(UTC)
    skipped = Counter()
    planned = []
    for appt, appt_id, starts in _intake(appointments, skipped):
        planned.extend(_plan_appointment(appt, appt_id, starts, now, skipped))
    planned.sort(key=lambda item: (item[0], str(item[1]), item[2]))
    LOG.info("plan summary reminders=%d skipped=%s",
             len(planned), dict(sorted(skipped.items())))
    return [item[3] for item in planned]
```

```
# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-10yeqqi4/brennan_reminders/test_reminders.py
import logging
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import reminders as R

UTC = timezone.utc
DUB = ZoneInfo("Europe/Dublin")
LOGGER = "brennan.reminders"
KEYS = {"appointment_id", "channel", "send_at", "text"}
NOW = None  # set per test where needed

FIXED = len(R.SMS_TEMPLATE.format(name="", date="14 Oct 2026", time="16:00",
                                  signature=R.DEFAULT_SIGNATURE))
MAX_NAME = R.SMS_LIMIT - FIXED


def dub(*parts):
    return datetime(*parts, tzinfo=DUB).astimezone(UTC)


def utc(*parts):
    return datetime(*parts, tzinfo=UTC)


def appt(aid="A1", starts=None, **overrides):
    rec = {
        "id": aid,
        "starts_at": starts if starts is not None else dub(2026, 10, 14, 16),
        "status": "booked",
        "customer_name": "Aoife Murphy",
        "phone": "+353870000001",
        "email": "aoife@example.com",
        "optout_sms_v2": False,
        "country": "IE",
    }
    rec.update(overrides)
    return rec


NOW_DEFAULT = utc(2026, 10, 1, 12)


class TestPlan(unittest.TestCase):

    def assertInvariants(self, res, now):
        for r in res:
            self.assertEqual(set(r), KEYS)
            self.assertEqual(r["send_at"].utcoffset(), timedelta(0))
            self.assertGreaterEqual(r["send_at"], now)

    # Timing and DST

    def test_dst_spring_slot1_is_utc_minus_48h(self):
        now = utc(2026, 3, 27, 12)
        res = R.plan_reminders([appt(starts=dub(2026, 3, 30, 14))], now)
        self.assertEqual([r["send_at"] for r in res],
                         [utc(2026, 3, 28, 13), utc(2026, 3, 30, 11)])
        self.assertInvariants(res, now)

    def test_dst_autumn_slot1_displays_10_in_dublin(self):
        now = utc(2026, 10, 20, 12)
        res = R.plan_reminders([appt(starts=dub(2026, 10, 26, 9))], now)
        self.assertEqual(res[0]["send_at"], utc(2026, 10, 24, 9))
        self.assertEqual(res[0]["send_at"].astimezone(DUB).hour, 10)
        # Slot 2 nominal is 07:00 Dublin (GMT) on 26 Oct, which is quiet.
        # Back candidate is 20:00 Dublin on 25 Oct. Dublin is already on GMT
        # then, so this is 20:00 UTC (the spec's 19:00 UTC is inconsistent).
        self.assertEqual(res[1]["send_at"], utc(2026, 10, 25, 20))
        self.assertInvariants(res, now)

    def test_quiet_move_spring(self):
        cand = dub(2026, 3, 30, 7)
        self.assertEqual(R._quiet_adjust(cand, utc(2026, 3, 28, 12)),
                         utc(2026, 3, 29, 19))

    def test_quiet_move_autumn(self):
        cand = dub(2026, 10, 26, 7)
        self.assertEqual(R._quiet_adjust(cand, utc(2026, 10, 20, 12)),
                         utc(2026, 10, 25, 20))

    def test_quiet_edges(self):
        now = utc(2026, 6, 9, 12)
        cases = [
            (dub(2026, 6, 10, 20, 59, 59), dub(2026, 6, 10, 20, 59, 59)),
            (dub(2026, 6, 10, 21, 0, 0), dub(2026, 6, 10, 20, 0, 0)),
            (dub(2026, 6, 10, 7, 59, 59), dub(2026, 6, 9, 20, 0, 0)),
            (dub(2026, 6, 10, 8, 0, 0), dub(2026, 6, 10, 8, 0, 0)),
            (dub(2026, 6, 10, 20, 0, 0), dub(2026, 6, 10, 20, 0, 0)),
        ]
        for cand, want in cases:
            with self.subTest(cand=cand):
                self.assertEqual(R._quiet_adjust(cand, now), want)

    def test_immediate_daytime(self):
        now = dub(2026, 10, 13, 12)
        res = R.plan_reminders([appt(starts=dub(2026, 10, 14, 16))], now)
        self.assertEqual([r["send_at"] for r in res],
                         [now, dub(2026, 10, 14, 14)])
        self.assertInvariants(res, now)

    def test_immediate_quiet_moves_forward(self):
        now = dub(2026, 10, 13, 22, 30)
        res = R.plan_reminders([appt(starts=dub(2026, 10, 14, 12))], now)
        self.assertEqual([r["send_at"] for r in res],
                         [dub(2026, 10, 14, 8), dub(2026, 10, 14, 10)])
        self.assertInvariants(res, now)

    def test_superseded_slot1_dropped(self):
        now = dub(2026, 10, 13, 22, 0)
        res = R.plan_reminders([appt(starts=dub(2026, 10, 14, 9))], now)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["send_at"], dub(2026, 10, 14, 8))
        self.assertInvariants(res, now)

    def test_starts_within_two_hours(self):
        now = dub(2026, 10, 14, 12)
        res = R.plan_reminders([appt(starts=dub(2026, 10, 14, 13))], now)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["send_at"], now)
        self.assertInvariants(res, now)

    def test_past_or_equal_starts_gives_nothing(self):
        now = dub(2026, 10, 14, 12)
        self.assertEqual(R.plan_reminders([appt(starts=now)], now), [])
        self.assertEqual(R.plan_reminders([appt(starts=now - timedelta(hours=1))], now), [])

    # Status

    def test_cancelled_statuses(self):
        for status in ["cancelled", " Cancelled ", "canceled", "CANCELED"]:
            with self.subTest(status=status):
                self.assertEqual(
                    R.plan_reminders([appt(status=status)], NOW_DEFAULT), [])

    def test_booked_sends(self):
        res = R.plan_reminders([appt(status="booked")], NOW_DEFAULT)
        self.assertEqual(len(res), 2)

    # Channel rules

    def test_optout_true_with_email_gives_email_only(self):
        res = R.plan_reminders([appt(optout_sms_v2=True)], NOW_DEFAULT)
        self.assertEqual(len(res), 2)
        self.assertTrue(all(r["channel"] == "email" for r in res))

    def test_optout_true_no_email_gives_nothing(self):
        res = R.plan_reminders([appt(optout_sms_v2=True, email="")], NOW_DEFAULT)
        self.assertEqual(res, [])

    def test_optout_false_phone_and_email_gives_sms(self):
        res = R.plan_reminders([appt(optout_sms_v2=False)], NOW_DEFAULT)
        self.assertTrue(all(r["channel"] == "sms" for r in res))

    def test_no_phone_with_email_gives_email(self):
        res = R.plan_reminders([appt(phone="   ")], NOW_DEFAULT)
        self.assertTrue(all(r["channel"] == "email" for r in res))
        self.assertEqual(len(res), 2)

    def test_no_phone_no_email_gives_nothing(self):
        res = R.plan_reminders([appt(phone=None, email=" ")], NOW_DEFAULT)
        self.assertEqual(res, [])

    def test_missing_optout_treated_as_opted_out(self):
        a = appt()
        del a["optout_sms_v2"]
        res = R.plan_reminders([a], NOW_DEFAULT)
        self.assertTrue(all(r["channel"] == "email" for r in res))

    def test_old_opt_out_field_is_ignored(self):
        res = R.plan_reminders([appt(opt_out=True, optout_sms_v2=False)], NOW_DEFAULT)
        self.assertTrue(all(r["channel"] == "sms" for r in res))

    # SMS length and names

    def test_sms_full_name_used(self):
        res = R.plan_reminders([appt()], NOW_DEFAULT)
        expected = ("Hi Aoife Murphy, reminder of your Brennan Opticians appointment "
                    "on 14 Oct 2026 at 16:00. Siobhán Ní Dhuibhir")
        self.assertTrue(all(r["text"] == expected for r in res))

    def test_exact_160_passes(self):
        res = R.plan_reminders([appt(customer_name="A" * MAX_NAME)], NOW_DEFAULT)
        self.assertEqual(len(res[0]["text"]), 160)
        self.assertTrue(res[0]["text"].startswith("Hi " + "A" * MAX_NAME + ", "))

    def test_161_falls_back_to_first_name(self):
        res = R.plan_reminders([appt(customer_name="Aoife " + "B" * (MAX_NAME - 5))],
                               NOW_DEFAULT)
        self.assertTrue(res[0]["text"].startswith("Hi Aoife, "))
        self.assertLessEqual(len(res[0]["text"]), 160)

    def test_long_first_name_falls_back_to_hello(self):
        res = R.plan_reminders([appt(customer_name="B" * (MAX_NAME + 1))], NOW_DEFAULT)
        self.assertTrue(res[0]["text"].startswith("Hello, reminder of your"))
        self.assertLessEqual(len(res[0]["text"]), 160)

    def test_name_whitespace_collapsed(self):
        res = R.plan_reminders([appt(customer_name="  Aoife    Murphy ")], NOW_DEFAULT)
        self.assertTrue(res[0]["text"].startswith("Hi Aoife Murphy, "))

    def test_missing_name_uses_generic_greeting(self):
        res = R.plan_reminders([appt(customer_name="")], NOW_DEFAULT)
        self.assertTrue(res[0]["text"].startswith("Hello, reminder of your"))

    def test_diacritic_name_and_pl_signature_counted(self):
        res = R.plan_reminders(
            [appt(customer_name="Séamus Ó Dónaill", country="PL", optout_sms_v2=False)],
            NOW_DEFAULT)
        text = res[0]["text"]
        self.assertTrue(text.startswith("Hi Séamus Ó Dónaill, "))
        self.assertTrue(text.endswith(R.PL_SIGNATURE))
        self.assertLessEqual(len(text), 160)
        self.assertEqual(R.sms_encoding(text), "UCS-2")

    def test_sms_encoding_helper(self):
        self.assertEqual(R.sms_encoding("Hello, 16:00 @ x^y"), "GSM-7")
        self.assertEqual(R.sms_encoding("{}"), "GSM-7")
        self.assertEqual(R.sms_encoding("Siobhán"), "UCS-2")

    # Signature selection

    def test_signature_selection_both_channels(self):
        cases = [("PL", R.PL_SIGNATURE), (" pl ", R.PL_SIGNATURE),
                 ("IE", R.DEFAULT_SIGNATURE), (None, R.DEFAULT_SIGNATURE)]
        for country, sig in cases:
            with self.subTest(country=country):
                sms = R.plan_reminders([appt(country=country)], NOW_DEFAULT)
                email = R.plan_reminders([appt(country=country, optout_sms_v2=True)],
                                         NOW_DEFAULT)
                self.assertTrue(sms[0]["text"].endswith(sig))
                self.assertTrue(email[0]["text"].endswith(sig))
        a = appt()
        del a["country"]
        res = R.plan_reminders([a], NOW_DEFAULT)
        self.assertTrue(res[0]["text"].endswith(R.DEFAULT_SIGNATURE))

    # Email text

    def test_email_exact_text(self):
        res = R.plan_reminders([appt(optout_sms_v2=True)], NOW_DEFAULT)
        expected = ("Dear Aoife Murphy,\n\nThis is a reminder of your Brennan Opticians "
                    "appointment on 14 Oct 2026 at 16:00.\n\nKind regards,\n"
                    "Siobhán Ní Dhuibhir")
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertEqual(r["text"], expected)

    def test_email_without_name(self):
        res = R.plan_reminders([appt(optout_sms_v2=True, customer_name="")], NOW_DEFAULT)
        self.assertTrue(res[0]["text"].startswith("Hello,\n\nThis is a reminder"))
        self.assertTrue(res[0]["text"].endswith(R.DEFAULT_SIGNATURE))

    # Ordering, ids, duplicates

    def test_ties_sorted_by_str_id(self):
        now = dub(2026, 10, 13, 12)
        res = R.plan_reminders(
            [appt("b2", starts=dub(2026, 10, 13, 13)),
             appt("a1", starts=dub(2026, 10, 13, 13))], now)
        self.assertEqual([r["appointment_id"] for r in res], ["a1", "b2"])

    def test_id_returned_unchanged(self):
        res = R.plan_reminders([appt(42)], NOW_DEFAULT)
        self.assertIsInstance(res[0]["appointment_id"], int)
        self.assertEqual(res[0]["appointment_id"], 42)

    def test_duplicate_id_keeps_first(self):
        res = R.plan_reminders(
            [appt("D1", starts=dub(2026, 10, 14, 16)),
             appt("D1", starts=dub(2026, 11, 20, 10))], NOW_DEFAULT)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertIn("14 Oct 2026", r["text"])

    # Validation and logging

    def test_naive_now_raises_without_input_values(self):
        with self.assertRaises(ValueError) as cm:
            R.plan_reminders([], datetime(2026, 10, 13, 12))
        self.assertNotIn("2026", str(cm.exception))

    def test_naive_starts_skipped_with_id_only_warning(self):
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            res = R.plan_reminders(
                [appt("N1", starts=datetime(2026, 10, 14, 16))], NOW_DEFAULT)
        self.assertEqual(res, [])
        warnings = [r.getMessage() for r in cm.records if r.levelno == logging.WARNING]
        self.assertTrue(any("N1" in m for m in warnings))
        for m in warnings:
            self.assertNotIn("2026", m)
            self.assertNotIn("Aoife", m)

    def test_non_dict_and_missing_id_skipped(self):
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            res = R.plan_reminders(
                ["x", {"starts_at": dub(2026, 10, 14, 16)}, appt("ok")], NOW_DEFAULT)
        self.assertEqual({r["appointment_id"] for r in res}, {"ok"})
        self.assertGreaterEqual(len(cm.records), 2)

    def test_no_pii_in_any_log(self):
        now = dub(2026, 10, 13, 22)
        email = "client.test@example.com"
        name = "Aoife Murphy"
        fixture = [
            appt("email-only", optout_sms_v2=True, email=email, customer_name=name),
            appt("sms", phone="+353870000002", email=email, customer_name=name,
                 starts=dub(2026, 10, 14, 16)),
            appt("cancelled", status="cancelled", email=email, customer_name=name),
            appt("past", starts=dub(2026, 10, 13, 11), email=email, customer_name=name),
            appt("nocontact", phone="", email="", customer_name=name),
            appt("optout-noemail", phone="+353870000003", email="",
                 optout_sms_v2=True, customer_name=name),
            appt("naive", starts=datetime(2026, 10, 14, 16), email=email,
                 customer_name=name),
            email,
            {"starts_at": dub(2026, 10, 14, 16), "customer_name": name, "email": email},
            appt("dup", email=email, customer_name=name, optout_sms_v2=True),
            appt("dup", email=email, customer_name=name, optout_sms_v2=True),
            appt("superseded", starts=dub(2026, 10, 14, 9), email=email,
                 customer_name=name, optout_sms_v2=True),
            appt("soon", starts=dub(2026, 10, 13, 23, 30), email=email,
                 customer_name=name, optout_sms_v2=True),
        ]
        with self.assertLogs(LOGGER, level=logging.DEBUG) as cm:
            R.plan_reminders(fixture, now)
        blob = "\n".join(
            r.getMessage() + " " + repr(r.args) + " " + repr(r.exc_info)
            for r in cm.records)
        self.assertNotIn(email, blob)
        self.assertNotIn(name, blob)

    # Sorting and deterministic output

    def test_output_key_set_exact(self):
        res = R.plan_reminders([appt()], NOW_DEFAULT)
        for r in res:
            self.assertEqual(set(r), KEYS)


if __name__ == "__main__":
    unittest.main()