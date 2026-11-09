"""Appointment reminder planner for Brennan Opticians.

plan_reminders(appointments, now) returns a list of dicts with exactly the keys
appointment_id, channel ("sms" or "email"), send_at (timezone-aware, Europe/Dublin)
and text, sorted by (send_at, appointment_id, channel).

Rules:
- now and every starts_at must be timezone-aware, otherwise ValueError. Error
  messages name only the key and the appointment id or index.
- Opt-out uses optout_sms_v2 only; the legacy opt_out field is never read.
  SMS is allowed only when optout_sms_v2 is exactly False. ASSUMPTION: True,
  None or a missing field all mean opted out, so no SMS is sent.
- Status is compared case-insensitively after stripping. "cancelled" and
  "canceled" produce no reminders.
- Reminder points are starts_at - 48h (first) and starts_at - 2h (second), computed
  in UTC. ASSUMPTION: "hours before" for the second reminder is 2 hours (SECOND_OFFSET).
- If starts_at <= now, the appointment gets no reminders.
- First reminder: if its point has passed, it is sent at now.
- Second reminder: if its point has passed, it is skipped and never sent late.
  ASSUMPTION. Under cuts the second reminder has priority over the first.
- Quiet hours: a send time whose Dublin local hour is 21:00-07:59 moves to 20:00
  Dublin local. For 21:00-23:59 that is the same day; for 00:00-07:59 it is the
  previous day.
- Never in the past: an adjusted time earlier than now becomes now. This wins over
  quiet hours, so if now is itself in quiet hours the reminder goes out at now.
  OPEN QUESTION for PM.
- If the first and second reminders resolve to the same send time, the first is dropped.
- One channel per reminder point. SMS is used when a usable phone exists and SMS is
  allowed. Otherwise email is used when a usable email exists. Otherwise no reminder
  is planned and a warning is logged.
- SMS is limited to 160 characters, counted with len(). If the name must be shortened,
  it is truncated first and the greeting is dropped if no room is left. Date, time and
  signature are never truncated. If the SMS still does not fit, that reminder is sent
  by email instead. NOTE: characters outside GSM-7 (e.g. the accent in Siobhán) may make
  carriers use UCS-2, which allows 70 characters per segment. The len() count rule is
  kept as specified.
- Signature: country "PL" (case-insensitive, stripped) gets Grzegorz Szczepański;
  everything else gets Siobhán Ní Dhuibhir.
- Logging uses the logger "brennan.reminders". Each planned reminder produces one INFO
  line with the appointment id, channel and send time. DEVIATION: the contact address is
  not logged, following the Data Protection Commission audit finding. Support traces
  deliveries by appointment id and channel. Customer data is never logged.
- The function does not mutate its inputs.
- DEVIATION: the requested test_reminders.py is not a separate file. The tests are at the
  bottom of this module, under the __main__ guard, so that the deliverable stays a single
  module. Run them with: python3 -I /absolute/path/reminders.py
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Dublin")
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)  # ASSUMPTION: "hours before" = 2
SMS_MAX = 160
QUIET_START_HOUR = 21  # 21:00 local
QUIET_END_HOUR = 8     # 08:00 local; quiet window is [21:00, 08:00)
HOLD_HOUR = 20         # 20:00 local, target for quiet-hour moves
CANCELLED = frozenset({"cancelled", "canceled"})
REQUIRED_KEYS = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")
SIG_PL = "Grzegorz Szczepański"
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
LOG = logging.getLogger("brennan.reminders")


def _label(idx, appt):
    aid = appt.get("id")
    return str(aid) if aid not in (None, "") else f"index {idx}"


def _validate(idx, appt):
    if not isinstance(appt, dict):
        raise ValueError(f"appointment at index {idx} is not a dict")
    for key in REQUIRED_KEYS:
        if key not in appt:
            raise ValueError(f"appointment {_label(idx, appt)} is missing required key '{key}'")
    starts = appt["starts_at"]
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError(f"starts_at of appointment {_label(idx, appt)} must be timezone-aware")


def _usable(value):
    return isinstance(value, str) and value.strip() != ""


def _clean_name(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _signature(country):
    if isinstance(country, str) and country.strip().upper() == "PL":
        return SIG_PL
    return SIG_DEFAULT


def _quiet_adjust(t_utc):
    local = t_utc.astimezone(TZ)
    if QUIET_END_HOUR <= local.hour < QUIET_START_HOUR:
        return t_utc
    if local.hour >= QUIET_START_HOUR:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    return datetime(day.year, day.month, day.day, HOLD_HOUR, 0, tzinfo=TZ).astimezone(timezone.utc)


def _sms_text(name, date, clock, sig):
    tail = f"your Brennan Opticians appointment is on {date} at {clock}. {sig}"
    if name:
        full = f"Hi {name}, {tail}"
        if len(full) <= SMS_MAX:
            text = full
        else:
            room = SMS_MAX - len(tail) - len("Hi , ")
            short = name[:room].rstrip() if room > 0 else ""
            text = f"Hi {short}, {tail}" if short else tail
    else:
        text = tail
    if len(text) > SMS_MAX:
        return None
    assert len(text) <= SMS_MAX
    return text


def _email_text(name, date, clock, sig):
    greet = f"Hi {name},\n\n" if name else "Hi,\n\n"
    return (f"{greet}This is a reminder of your Brennan Opticians appointment "
            f"on {date} at {clock}.\n\n{sig}")


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(timezone.utc)
    out = []

    for idx, appt in enumerate(appointments):
        _validate(idx, appt)
        aid = appt["id"]
        sid = str(aid)
        status = str(appt["status"] or "").strip().lower()
        if status in CANCELLED:
            LOG.debug("skipped cancelled appointment_id=%s", sid)
            continue

        starts = appt["starts_at"].astimezone(timezone.utc)
        if starts <= now_utc:
            LOG.debug("skipped past appointment_id=%s", sid)
            continue

        email_ok = _usable(appt["email"])
        sms_ok = _usable(appt["phone"]) and appt.get("optout_sms_v2") is False
        if sms_ok:
            channel = "sms"
        elif email_ok:
            channel = "email"
        else:
            LOG.warning("no reminder channel for appointment_id=%s", sid)
            continue

        local = starts.astimezone(TZ)
        date = local.strftime("%d/%m/%Y")
        clock = local.strftime("%H:%M")
        name = _clean_name(appt["customer_name"])
        sig = _signature(appt["country"])

        first = starts - FIRST_OFFSET
        second = starts - SECOND_OFFSET
        planned = [("first", first if first > now_utc else now_utc)]
        if second > now_utc:
            planned.append(("second", second))
        else:
            LOG.debug("skipped second reminder, point passed appointment_id=%s", sid)

        due = [(label, max(_quiet_adjust(t), now_utc)) for label, t in planned]
        if len(due) == 2 and due[0][1] == due[1][1]:
            due = due[1:]  # second has priority

        for _label_name, t in due:
            use = channel
            if use == "sms":
                text = _sms_text(name, date, clock, sig)
                if text is None:
                    if not email_ok:
                        LOG.warning("SMS too long and no email appointment_id=%s", sid)
                        continue
                    LOG.warning("SMS too long, sending email instead appointment_id=%s", sid)
                    use = "email"
            if use == "email":
                text = _email_text(name, date, clock, sig)
            send_at = t.astimezone(TZ)
            out.append({
                "appointment_id": aid,
                "channel": use,
                "send_at": send_at,
                "text": text,
            })
            LOG.info("planned reminder appointment_id=%s channel=%s send_at=%s",
                     sid, use, send_at.isoformat())

    out.sort(key=lambda r: (r["send_at"], str(r["appointment_id"]), r["channel"]))
    return out


if __name__ == "__main__":
    import unittest

    NOW = datetime(2026, 10, 13, 10, 0, tzinfo=TZ)

    def make(**kw):
        base = {
            "id": 1,
            "customer_name": "Aoife Murphy",
            "email": "aoife@example.ie",
            "phone": "+353850000000",
            "country": "IE",
            "status": "booked",
            "starts_at": datetime(2026, 10, 20, 14, 0, tzinfo=TZ),
            "optout_sms_v2": False,
        }
        base.update(kw)
        return base

    class RemindersTests(unittest.TestCase):
        def test_optout_v2_true_uses_email(self):
            r = plan_reminders([make(optout_sms_v2=True)], NOW)
            self.assertTrue(r and all(x["channel"] == "email" for x in r))

        def test_old_opt_out_ignored(self):
            r = plan_reminders([make(opt_out=True, optout_sms_v2=False)], NOW)
            self.assertTrue(r and all(x["channel"] == "sms" for x in r))

        def test_no_contact_no_reminder(self):
            r = plan_reminders([make(phone="  ", email="")], NOW)
            self.assertEqual(r, [])

        def test_cancelled_no_reminder(self):
            self.assertEqual(plan_reminders([make(status=" Cancelled ")], NOW), [])

        def test_first_passed_sends_at_now(self):
            a = make(starts_at=datetime(2026, 10, 13, 11, 0, tzinfo=TZ))
            r = plan_reminders([a], NOW)
            self.assertEqual(len(r), 1)
            self.assertEqual(r[0]["send_at"], NOW)

        def test_exact_offsets(self):
            r = plan_reminders([make()], NOW)
            self.assertEqual([x["send_at"] for x in r],
                             [datetime(2026, 10, 18, 14, 0, tzinfo=TZ),
                              datetime(2026, 10, 20, 12, 0, tzinfo=TZ)])

        def test_quiet_hours_22_30(self):
            a = make(starts_at=datetime(2026, 10, 17, 0, 30, tzinfo=TZ))
            times = [x["send_at"] for x in plan_reminders([a], NOW)]
            self.assertIn(datetime(2026, 10, 16, 20, 0, tzinfo=TZ), times)

        def test_quiet_hours_05_00_previous_day(self):
            a = make(starts_at=datetime(2026, 10, 17, 7, 0, tzinfo=TZ))
            times = [x["send_at"] for x in plan_reminders([a], NOW)]
            self.assertIn(datetime(2026, 10, 16, 20, 0, tzinfo=TZ), times)

        def test_never_in_past(self):
            for x in plan_reminders([make()], NOW):
                self.assertGreaterEqual(x["send_at"], NOW)

        def test_sms_length_and_date_time_kept(self):
            r = plan_reminders([make(customer_name="B" * 300)], NOW)
            sms = [x for x in r if x["channel"] == "sms"]
            self.assertTrue(sms)
            for x in sms:
                self.assertLessEqual(len(x["text"]), SMS_MAX)
                self.assertIn("20/10/2026 at 14:00", x["text"])
                self.assertTrue(x["text"].endswith(SIG_DEFAULT))

        def test_pl_signature(self):
            r = plan_reminders([make(country=" pl ")], NOW)
            self.assertTrue(all(x["text"].endswith(SIG_PL) for x in r))

        def test_output_sorted(self):
            a = make(id=1, starts_at=datetime(2026, 10, 25, 14, 0, tzinfo=TZ))
            b = make(id=2, starts_at=datetime(2026, 10, 21, 14, 0, tzinfo=TZ))
            r = plan_reminders([a, b], NOW)
            times = [x["send_at"] for x in r]
            self.assertEqual(times, sorted(times))

        def test_naive_raises(self):
            with self.assertRaises(ValueError):
                plan_reminders([make(starts_at=datetime(2026, 10, 20, 14, 0))], NOW)
            with self.assertRaises(ValueError):
                plan_reminders([], datetime(2026, 10, 13, 10, 0))

        def test_email_never_logged(self):
            with self.assertLogs("brennan.reminders", level="DEBUG") as cm:
                plan_reminders([make(email="secret.person@example.com"),
                                make(id=2, phone="", email="other.person@example.com")], NOW)
            self.assertNotIn("secret.person@example.com", "\n".join(cm.output))
            self.assertNotIn("other.person@example.com", "\n".join(cm.output))

    unittest.main()