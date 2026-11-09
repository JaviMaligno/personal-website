"""Brennan Opticians reminder planner.

Entry point: plan_reminders(appointments, now). Standard library only.
Run the tests with: python3 this_file.py   (unittest)

Output: send_at values are tz-aware and expressed in Europe/Dublin local time.

ASSUMPTIONS (need client confirmation where marked):
- SECOND_OFFSET = 2h. The brief omitted the number ("hours before"). CONFIRM.
- Only optout_sms_v2 is read; the stale opt_out field is ignored.
- No phone number -> email fallback. No phone and no email -> skipped, with a
  warning that carries the appointment id only.
- starts_at <= now -> no reminders.
- Quiet hours (>=21:00 or <08:00 Dublin local) -> move back to the preceding
  20:00. If that is before now (cannot send in the past), defer forward to the
  next 08:00 only if that is still before starts_at, else drop that reminder.
  Isolated in _apply_quiet_hours.
- A reminder whose adjusted send_at is >= starts_at is dropped.
- If both reminders resolve to exactly the same send_at, keep only the 2h one.
- SMS limit counts code points (160). Characters such as s-acute or o-acute
  force UCS-2, where a real SMS segment is 70 characters; not modelled.
- Logging: the house rule asks for one INFO line per planned reminder naming
  the recipient and how. The DPC audit forbids logging email addresses, so the
  line gives the appointment id, the channel and a masked contact (last 3
  phone digits, or "email on file"). No name, address or full number is logged.
"""
import logging
import unittest
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Dublin")
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)  # ASSUMPTION, see docstring
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
FALLBACK_LOCAL_HOUR = 20
SMS_MAX = 160
SIG_DEFAULT = "Siobhán Ní Dhuibhir"
SIG_PL = "Grzegorz Szczepański"


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _clean(v):
    return v.strip() if isinstance(v, str) else ""


def _channel(appt):
    if _clean(appt.get("phone")) and not appt.get("optout_sms_v2"):
        return "sms"
    if _clean(appt.get("email")):
        return "email"
    return None


def _is_quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def _apply_quiet_hours(t, now, starts_at):
    """Return an adjusted send time, or None if the reminder must be dropped."""
    local = t.astimezone(TZ)
    if not _is_quiet(local):
        return local
    day = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
    moved = datetime.combine(day, time(FALLBACK_LOCAL_HOUR), TZ)
    if moved >= now:
        return moved
    # Cannot go back without being in the past: defer to next 08:00 if possible.
    day = local.date() if local.hour < 8 else local.date() + timedelta(days=1)
    fwd = datetime.combine(day, QUIET_END, TZ)
    return fwd if fwd < starts_at else None


def _signature(appt):
    return SIG_PL if _clean(appt.get("country")).upper() == "PL" else SIG_DEFAULT


def _build_text(appt, starts_at, channel):
    local = starts_at.astimezone(TZ)
    body = (f"your Brennan Opticians appointment is on "
            f"{local:%d/%m/%Y} at {local:%H:%M}. {_signature(appt)}")
    name = _clean(appt.get("customer_name"))
    if channel == "email":
        variants = [name]
    else:
        parts = name.split()
        variants = [name, parts[0] if parts else "",
                    parts[0][0] + "." if parts else "", ""]
    for v in variants:
        text = f"Hi {v}, reminder: {body}" if v else f"Reminder: {body}"
        if channel == "email" or len(text) <= SMS_MAX:
            return text
    return text


def _plan_one(appt, now):
    aid = appt.get("id")
    starts_at = appt.get("starts_at")
    if not _aware(starts_at):
        raise ValueError(f"appointment {aid}: starts_at must be timezone-aware")
    if _clean(appt.get("status")).lower() == "cancelled" or starts_at <= now:
        return []
    channel = _channel(appt)
    if channel is None:
        log.warning("appointment %s skipped: no contact details", aid)
        return []
    text = _build_text(appt, starts_at, channel)
    out = []
    for kind, offset in ((0, FIRST_OFFSET), (1, SECOND_OFFSET)):
        t = _apply_quiet_hours(max(starts_at - offset, now), now, starts_at)
        if t is None or t >= starts_at:
            continue
        out.append((kind, {"appointment_id": aid, "channel": channel,
                           "send_at": t, "text": text}))
    if len(out) == 2 and out[0][1]["send_at"] == out[1][1]["send_at"]:
        out = out[1:]  # 2h reminder has priority
    return out


def _masked(appt, channel):
    if channel == "email":
        return "email on file"
    digits = "".join(c for c in _clean(appt.get("phone")) if c.isdigit())
    return "phone ***" + digits[-3:]


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be timezone-aware")
    planned = []
    for appt in appointments:
        for kind, r in _plan_one(appt, now):
            planned.append((r["send_at"], str(r["appointment_id"]), kind, r))
            log.info("Planned reminder %s for appointment %s to customer via %s (%s) at %s",
                     "2h" if kind else "48h", r["appointment_id"], r["channel"],
                     _masked(appt, r["channel"]), r["send_at"].isoformat())
    planned.sort(key=lambda p: p[:3])
    return [p[3] for p in planned]


class _Tests(unittest.TestCase):
    NOW = datetime(2026, 10, 13, 12, 0, tzinfo=ZoneInfo("UTC"))

    def appt(self, **kw):
        base = dict(id=1, customer_name="Aoife Ní Bhriain", email="secret.x@example.com",
                    phone="+353851234567", country="IE", status="booked",
                    starts_at=datetime(2026, 11, 20, 10, 0, tzinfo=TZ), optout_sms_v2=False)
        base.update(kw)
        return base

    def test_basic(self):
        r = plan_reminders([self.appt()], self.NOW)
        self.assertEqual([x["send_at"] for x in r],
                         [datetime(2026, 11, 18, 10, 0, tzinfo=TZ),
                          datetime(2026, 11, 20, 8, 0, tzinfo=TZ)])
        self.assertTrue(r[0]["text"].endswith("Siobhán Ní Dhuibhir"))
        self.assertIn("20/11/2026 at 10:00", r[0]["text"])

    def test_quiet_boundaries(self):
        far = datetime(2030, 1, 1, tzinfo=TZ)
        now = datetime(2026, 1, 1, tzinfo=TZ)
        ok = lambda h, m: _apply_quiet_hours(datetime(2026, 6, 10, h, m, tzinfo=TZ), now, far)
        self.assertEqual(ok(20, 59).hour, 20)
        self.assertEqual(ok(21, 0), datetime(2026, 6, 10, 20, 0, tzinfo=TZ))
        self.assertEqual(ok(7, 59), datetime(2026, 6, 9, 20, 0, tzinfo=TZ))
        self.assertEqual(ok(8, 0), datetime(2026, 6, 10, 8, 0, tzinfo=TZ))

    def test_dst_local_quiet(self):
        utc = ZoneInfo("UTC")
        a = self.appt(starts_at=datetime(2027, 7, 1, 22, 30, tzinfo=utc))  # 23:30 BST
        r = plan_reminders([a], self.NOW)[-1]
        self.assertEqual(r["send_at"], datetime(2027, 7, 1, 20, 0, tzinfo=TZ))
        self.assertEqual(r["send_at"].astimezone(utc).hour, 19)

    def test_now_in_quiet_hours_defers(self):
        now = datetime(2026, 10, 13, 22, 0, tzinfo=TZ)
        a = self.appt(starts_at=datetime(2026, 10, 14, 12, 0, tzinfo=TZ))
        r = plan_reminders([a], now)
        self.assertTrue(all(x["send_at"] >= now for x in r))
        self.assertEqual(r[0]["send_at"], datetime(2026, 10, 14, 8, 0, tzinfo=TZ))
        self.assertEqual(len(r), 1)  # deduped to the 2h one

    def test_channels_and_skips(self):
        self.assertEqual(plan_reminders([self.appt(optout_sms_v2=True)], self.NOW)[0]["channel"], "email")
        self.assertEqual(plan_reminders([self.appt(phone=" ")], self.NOW)[0]["channel"], "email")
        self.assertEqual(plan_reminders([self.appt(phone="", email="")], self.NOW), [])
        self.assertEqual(plan_reminders([self.appt(status=" Cancelled ")], self.NOW), [])
        past = self.appt(starts_at=datetime(2026, 10, 1, 10, 0, tzinfo=TZ))
        self.assertEqual(plan_reminders([past], self.NOW), [])

    def test_text(self):
        long = self.appt(customer_name="Bartholomew " + "X" * 200, country=" pl ")
        for r in plan_reminders([long], self.NOW):
            self.assertLessEqual(len(r["text"]), SMS_MAX)
            self.assertIn("10:00", r["text"])
            self.assertTrue(r["text"].endswith(SIG_PL))

    def test_naive_rejected(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 1, 1))
        with self.assertRaises(ValueError) as cm:
            plan_reminders([self.appt(starts_at=datetime(2026, 12, 1, 9))], self.NOW)
        self.assertNotIn("example.com", str(cm.exception))

    def test_sorted_and_no_pii_logged(self):
        a = self.appt(id=2, optout_sms_v2=True)
        b = self.appt(id=1)
        with self.assertLogs(__name__, level="DEBUG") as cm:
            r = plan_reminders([a, b], self.NOW)
        keys = [(x["send_at"], str(x["appointment_id"])) for x in r]
        self.assertEqual(keys, sorted(keys))
        self.assertNotIn("secret.x", "\n".join(cm.output))
        self.assertNotIn("851234567", "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()