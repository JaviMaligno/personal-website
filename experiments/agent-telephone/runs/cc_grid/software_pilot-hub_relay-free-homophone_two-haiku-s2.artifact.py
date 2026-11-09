# Note: no test run was executed for this module. The tests below are written but unverified.
# Caveat: SMS length is the literal Python character count (<= 160). "í", "ń" and "…" are not GSM-7, so carrier encoding may segment or UCS-2 the message. The client has not decided this yet.
# Caveat: the house rule asked for logs of "who it goes to and how". Contact details are barred by the privacy rule, so logs carry only appointment_id, channel, kind and reason code.
# Caveat: the weekday labels in the acceptance cases do not match 2026 (13 Oct 2026 is a Tuesday). Tests assert on dates only.
import logging
from collections.abc import Mapping
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
SMS_MAX = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
ELLIPSIS = "…"


def _get(appt, key):
    if isinstance(appt, Mapping):
        return appt.get(key)
    return getattr(appt, key, None)


def _aware(dt):
    return isinstance(dt, datetime) and dt.utcoffset() is not None


def _clean(value):
    return "" if value is None else str(value).strip()


def _quiet(local):
    return local.hour >= 21 or local.hour < 8


def _adjust(target, now):
    # Rule 1: never before now.
    if target < now:
        target = now
    local = target.astimezone(DUBLIN)
    # Rule 2: quiet hours move back to 20:00 on the evening that opened the window.
    if not _quiet(local):
        return target
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    evening = datetime.combine(day, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)
    if evening >= now:
        return evening
    now_local = now.astimezone(DUBLIN)
    if not _quiet(now_local):
        return now
    day = now_local.date() if now_local.hour < 8 else now_local.date() + timedelta(days=1)
    return datetime.combine(day, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)


def _plan_slots(starts, now):
    second = _adjust(starts - timedelta(hours=2), now)
    if starts - now < timedelta(hours=2):
        return [("second", second)]
    first = _adjust(starts - timedelta(hours=48), now)
    if first >= second:
        return [("second", second)]
    return [("first", first), ("second", second)]


def _date_time(starts_utc):
    local = starts_utc.astimezone(DUBLIN)
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}", f"{local:%H:%M}"


def _sig(country):
    return SIG_PL if _clean(country).upper() == "PL" else SIG_DEFAULT


def _body(greet, date_s, time_s, sig):
    head = f"Hi {greet}. " if greet else ""
    return f"{head}Reminder: your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"


def _sms(full, date_s, time_s, sig):
    if len(_body("", date_s, time_s, sig)) > SMS_MAX:
        raise ValueError("SMS template without name exceeds 160 characters")
    first = full.split(" ")[0] if full else ""
    options = [full, first] + [first[:k] + ELLIPSIS for k in range(len(first) - 1, 0, -1)]
    for name in options:
        text = _body(name, date_s, time_s, sig)
        if len(text) <= SMS_MAX:
            return text
    return _body("", date_s, time_s, sig)


def _skip(appointment_id, reason):
    log.info("skipped appointment_id=%s reason=%s", appointment_id, reason)


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for appt in appointments:
        aid = _get(appt, "id")
        if _clean(_get(appt, "status")).lower() == "cancelled":
            _skip(aid, "CANCELLED")
            continue
        starts = _get(appt, "starts_at")
        if not _aware(starts):
            _skip(aid, "MALFORMED_STARTS_AT")
            continue
        starts_utc = starts.astimezone(UTC)
        if starts_utc <= now_utc:
            _skip(aid, "NOT_IN_FUTURE")
            continue
        phone = _clean(_get(appt, "phone"))
        email = _clean(_get(appt, "email"))
        if _get(appt, "optout_sms_v2") is False and phone:
            channel = "sms"
        elif email:
            channel = "email"
        else:
            _skip(aid, "NO_CONTACT")
            continue
        name = " ".join(_clean(_get(appt, "customer_name")).split())
        date_s, time_s = _date_time(starts_utc)
        sig = _sig(_get(appt, "country"))
        for kind, send_at in _plan_slots(starts_utc, now_utc):
            if channel == "sms":
                text = _sms(name, date_s, time_s, sig)
            else:
                text = _body(name, date_s, time_s, sig)
            planned.append((send_at, str(aid), kind, aid, channel, text))
    planned.sort(key=lambda p: (p[0], p[1], p[2]))
    result = []
    for send_at, _, kind, aid, channel, text in planned:
        log.info("planned reminder appointment_id=%s channel=%s kind=%s", aid, channel, kind)
        result.append({"appointment_id": aid, "channel": channel, "send_at": send_at, "text": text})
    return result


# ---- tests (not executed) ----
import unittest


def _dt(*args):
    return datetime(*args, tzinfo=DUBLIN)


class ReminderTests(unittest.TestCase):
    NOW = _dt(2026, 10, 13, 9, 0)

    def appt(self, **kw):
        base = {
            "id": "A1", "customer_name": "Ann Murphy", "email": "ann@example.ie",
            "phone": "0871234567", "country": "IE", "status": "booked",
            "starts_at": _dt(2026, 10, 21, 14, 0), "optout_sms_v2": False,
        }
        base.update(kw)
        return base

    def test_case1_standard_slots(self):
        r = plan_reminders([self.appt()], self.NOW)
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 10, 19, 14, 0), _dt(2026, 10, 21, 12, 0)])
        self.assertEqual({x["channel"] for x in r}, {"sms"})

    def test_case2_quiet_hours(self):
        r = plan_reminders([self.appt(starts_at=_dt(2026, 10, 21, 7, 30))], self.NOW)
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 10, 18, 20, 0), _dt(2026, 10, 20, 20, 0)])

    def test_case3_single_reminder(self):
        r = plan_reminders([self.appt(starts_at=_dt(2026, 10, 13, 15, 0))], _dt(2026, 10, 13, 13, 30))
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 10, 13, 13, 30)])

    def test_case4_both_clamped_to_now(self):
        r = plan_reminders([self.appt(starts_at=_dt(2026, 10, 13, 16, 0))], _dt(2026, 10, 13, 13, 0))
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 10, 13, 13, 0), _dt(2026, 10, 13, 14, 0)])

    def test_case5_late_evening_now(self):
        r = plan_reminders([self.appt(starts_at=_dt(2026, 10, 15, 10, 0))], _dt(2026, 10, 13, 22, 0))
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 10, 14, 8, 0), _dt(2026, 10, 15, 8, 0)])

    def test_case6_cancelled_any_case(self):
        self.assertEqual(plan_reminders([self.appt(status="  CANCELLED ")], self.NOW), [])

    def test_case7_past_or_exactly_now(self):
        self.assertEqual(plan_reminders([self.appt(starts_at=self.NOW)], self.NOW), [])
        self.assertEqual(plan_reminders([self.appt(starts_at=_dt(2026, 10, 1, 9, 0))], self.NOW), [])

    def test_case8_opted_out_email_only(self):
        r = plan_reminders([self.appt(optout_sms_v2=True)], self.NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_case9_opted_out_no_email(self):
        self.assertEqual(plan_reminders([self.appt(optout_sms_v2=True, email="")], self.NOW), [])

    def test_case10_missing_optout_email_only(self):
        r = plan_reminders([self.appt(optout_sms_v2=None, phone="")], self.NOW)
        self.assertEqual(len(r), 2)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_case11_no_contact(self):
        self.assertEqual(plan_reminders([self.appt(phone="", email="")], self.NOW), [])

    def test_case12_long_name_sms_limit(self):
        r = plan_reminders([self.appt(customer_name="Ann " + "B" * 56)], self.NOW)
        for x in r:
            self.assertLessEqual(len(x["text"]), SMS_MAX)
            self.assertIn("21 Oct 2026", x["text"])
            self.assertIn("14:00", x["text"])
            self.assertTrue(x["text"].endswith(SIG_DEFAULT))

    def test_case13_signatures(self):
        pl = plan_reminders([self.appt(country="pl")], self.NOW)
        self.assertTrue(all(x["text"].endswith(SIG_PL) for x in pl))
        ie = plan_reminders([self.appt(country=None)], self.NOW)
        self.assertTrue(all(x["text"].endswith(SIG_DEFAULT) for x in ie))

    def test_case14_naive_now_raises(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 9, 0))

    def test_case15_sorted(self):
        r = plan_reminders([
            self.appt(id="B", starts_at=_dt(2026, 10, 21, 14, 0)),
            self.appt(id="A", starts_at=_dt(2026, 10, 16, 10, 0)),
        ], self.NOW)
        sends = [x["send_at"] for x in r]
        self.assertEqual(sends, sorted(sends))

    def test_case16_logs_contain_no_email(self):
        with self.assertLogs(level="INFO") as cm:
            plan_reminders([
                self.appt(),
                self.appt(id="C", optout_sms_v2=True, phone=""),
                self.appt(id="D", status="cancelled"),
            ], self.NOW)
        joined = "\n".join(cm.output)
        self.assertNotIn("@", joined)
        self.assertNotIn("Ann", joined)

    def test_case17_dst_boundary(self):
        r = plan_reminders([self.appt(starts_at=_dt(2026, 10, 27, 7, 30), customer_name="X")],
                           _dt(2026, 10, 20, 9, 0))
        self.assertEqual([x["send_at"] for x in r], [_dt(2026, 10, 24, 20, 0), _dt(2026, 10, 26, 20, 0)])
        self.assertEqual(r[0]["send_at"].astimezone(UTC).hour, 19)

    def test_naive_starts_skipped(self):
        self.assertEqual(plan_reminders([self.appt(starts_at=datetime(2026, 10, 21, 14, 0))], self.NOW), [])

    def test_sms_template_guard_cannot_trigger(self):
        self.assertLessEqual(len(_body("", "30 Sep 2026", "00:00", SIG_PL)), SMS_MAX)


if __name__ == "__main__":
    unittest.main()