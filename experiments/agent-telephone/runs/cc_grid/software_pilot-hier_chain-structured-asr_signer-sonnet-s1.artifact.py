# NOTE (comment, not code): I have no file or shell tools here, so nothing below was written to disk or run.
# Save the two sections below as reminders.py and test_reminders.py in
# /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-ldej8wxi and run
#   python3 -m unittest -v test_reminders
# Test results: NOT RUN (0 passed / 0 failed reported).
# Deviations and ambiguities:
#  1. House rule (log contact per reminder) conflicts with R11 (never log emails). The INFO line logs
#     the channel plus a masked contact: "phone ending NNNN" for SMS and "email address on file" for
#     email. No email address is logged.
#  2. Two files were requested, but this reply is one block, so the files are separated by markers.
#  3. 48h and 2h are absolute elapsed time (UTC arithmetic), not Dublin wall-clock.
#  4. A reminder with no usable channel logs one warning per appointment, not one per reminder.
#  5. optout_sms_v2 is read with bool(), so any truthy value counts as opted out.

# ===================== FILE: reminders.py =====================
"""Appointment reminders for Brennan Opticians.

plan_reminders(appointments, now) -> list of dicts with keys exactly
appointment_id, channel ("sms"|"email"), send_at, text.

Design (R = client requirement, D = architect decision):
* All times are tz-aware. send_at is returned in Europe/Dublin (R14).
  48h/2h offsets are absolute elapsed time (computed in UTC).
* D1: first = max(start-48h, now); second = start-2h.
* R9/D2: quiet hours 21:00 (inclusive) to 08:00 (exclusive) Dublin wall clock.
  A time inside moves back to the preceding 20:00. If the result is < now the
  reminder is dropped (never deferred forward).
* D3: appointments with start <= now get no reminders.
* D4: if the adjusted first and second send_at are the same instant, only the
  2h one is kept (R13).
* D5: a 2h point in quiet hours (appointment 08:00-10:00) moves to 20:00 the
  day before, so that reminder arrives well over 2h ahead.
* D6/R8: text uses "Tue 20 Oct 2026 at 14:30" (Dublin local time).
* R6: SMS if phone non-blank and optout_sms_v2 not true, else email, else skip.
  Only optout_sms_v2 is read; the old opt_out field is never read (R2).
* R7: SMS <= 160 chars; the name is shortened, never date/time/signature.
* R12: signature "Chevonne Nee Divver", or "Grzegorz Szczepański" for country PL.
* D7: malformed appointments are skipped with a warning (id + exception type
  name only). Naive `now` raises ValueError. Inputs are never mutated.
* D8: duplicate appointment ids are processed independently (no dedupe).
* D9: names are stripped and whitespace-collapsed; empty/None becomes "there".
* R11: logger "reminders"; email addresses are never logged.
* R15: sorted by send_at, then str(appointment_id), then 48h before 2h.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
log = logging.getLogger("reminders")

SMS_MAX = 160
_REQUIRED = ("id", "customer_name", "email", "phone", "country", "status", "starts_at")
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_BODIES = (
    "Reminder: your appointment at Brennan Opticians is on {d} at {t}.",
    "Reminder: your appointment at Brennan Opticians is coming up on {d} at {t}.",
)


def _apply_quiet_hours(dt):
    """Move an aware datetime out of 21:00-08:00 Dublin to the preceding 20:00."""
    local = dt.astimezone(DUBLIN)
    h = local.hour
    if 8 <= h < 21:
        return local
    day = local.date() if h >= 21 else local.date() - timedelta(days=1)
    return datetime(day.year, day.month, day.day, 20, 0, tzinfo=DUBLIN)


def _safe_id(a):
    try:
        v = a.get("id")
        if isinstance(v, (int, str)) and not isinstance(v, bool) and len(str(v)) <= 64:
            return str(v)
    except Exception:
        pass
    return "unknown"


def _opt_str(v):
    if v is not None and not isinstance(v, str):
        raise TypeError("expected str or None")
    return v or ""


def _signature(country):
    if country.strip().upper() == "PL":
        return "Grzegorz Szczepański"
    return "Chevonne Nee Divver"


def _sms_text(name, body, sig):
    first = name.split()[0] if name else ""
    cands = [name, first]
    cands += [first[:n] + "..." for n in range(len(first) - 1, 0, -1)]
    if first:
        cands.append(first[0] + ".")
    cands.append("there")
    for c in cands:
        if not c:
            continue
        text = f"Hi {c}, {body} {sig}"
        if len(text) <= SMS_MAX:
            assert len(text) <= SMS_MAX
            return text
    raise AssertionError("cannot fit SMS")  # unreachable by construction


def _mask(channel, phone):
    if channel == "email":
        return "email address on file"
    digits = [c for c in phone if c.isdigit()]
    return "phone ending " + "".join(digits[-4:]) if len(digits) >= 4 else "phone ending ***"


def _plan_one(a, now):
    if not isinstance(a, dict):
        raise TypeError("appointment must be a dict")
    for k in _REQUIRED:
        if k not in a:
            raise KeyError(k)
    aid = a["id"]
    starts = a["starts_at"]
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError("starts_at must be an aware datetime")
    status = _opt_str(a["status"])
    email = _opt_str(a["email"]).strip()
    phone = _opt_str(a["phone"]).strip()
    country = _opt_str(a["country"])
    if a["customer_name"] is not None and not isinstance(a["customer_name"], str):
        raise TypeError("name must be str or None")
    name = " ".join((a["customer_name"] or "").split())

    if status.strip().lower() in ("cancelled", "canceled"):
        log.info("appointment %s skipped: cancelled", aid)
        return []
    starts_utc = starts.astimezone(UTC)
    if starts_utc <= now:
        log.info("appointment %s skipped: already started", aid)
        return []

    raws = ((0, max(starts_utc - timedelta(hours=48), now)),
            (1, starts_utc - timedelta(hours=2)))
    keep = []
    for seq, raw in raws:
        adj = _apply_quiet_hours(raw)
        if adj < now:
            log.info("appointment %s reminder %d dropped: send time in the past after quiet hours", aid, seq + 1)
        else:
            keep.append((seq, adj))
    if len(keep) == 2 and keep[0][1] == keep[1][1]:
        log.info("appointment %s reminder 1 dropped: same time as reminder 2", aid)
        keep = keep[1:]
    if not keep:
        return []

    if phone and not a.get("optout_sms_v2"):
        channel = "sms"
    elif email:
        channel = "email"
    else:
        log.warning("appointment %s skipped: no usable channel", aid)
        return []

    local = starts_utc.astimezone(DUBLIN)
    d = f"{_DAYS[local.weekday()]} {local.day:02d} {_MONTHS[local.month - 1]} {local.year}"
    t = f"{local:%H:%M}"
    sig = _signature(country)
    out = []
    for seq, adj in keep:
        body = _BODIES[seq].format(d=d, t=t)
        if channel == "sms":
            text = _sms_text(name, body, sig)
        else:
            text = f"Hi {name or 'there'}, {body}\n{sig}"
        log.info("reminder planned appointment_id=%s which=%s channel=%s contact=%s send_at=%s",
                 aid, "48h" if seq == 0 else "2h", channel, _mask(channel, phone),
                 adj.isoformat())
        out.append(((adj, str(aid), seq),
                    {"appointment_id": aid, "channel": channel, "send_at": adj, "text": text}))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    planned = []
    for a in appointments:
        try:
            planned.extend(_plan_one(a, now_utc))
        except Exception as exc:
            log.warning("skipped malformed appointment id=%s error=%s", _safe_id(a), type(exc).__name__)
    planned.sort(key=lambda p: p[0])
    return [r for _, r in planned]


# ===================== FILE: test_reminders.py =====================
"""Tests for reminders.py (stdlib unittest).

Acceptance criteria by requirement:
| ID      | Criterion                                                        |
|---------|------------------------------------------------------------------|
| R1      | Result dicts have exactly the 4 keys; channel sms/email          |
| R2      | Only optout_sms_v2 used; old opt_out ignored; missing = False    |
| R3      | Reminders at start-48h and start-2h                              |
| R4      | Past 48h point sends at now                                      |
| R5      | No send_at < now; == now allowed                                 |
| R6      | sms > email > skip+warning; never both                           |
| R7      | SMS <= 160 (exactly 160 ok, 161 shortened); date/time/sig kept   |
| R8      | Text has "Tue 20 Oct 2026 at 14:30" in Dublin time               |
| R9      | Quiet hours 21:00-08:00 -> prior 20:00, DST-correct              |
| R10     | cancelled/canceled (any case/space) -> nothing                   |
| R11     | No email in any log record, incl. malformed paths                |
| R12     | Signature last; PL signature                                     |
| R13     | 2h kept when reminders collapse                                  |
| R14     | send_at aware, Europe/Dublin                                     |
| R15     | Sorted by send_at, id, 48h before 2h                             |
| R16     | Module imports only stdlib; no legacy code                       |
| D2-D9   | See test_D* tests                                                |
"""
import ast
import copy
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import reminders
from reminders import plan_reminders

UTC = timezone.utc
DUB = ZoneInfo("Europe/Dublin")
EMAIL = "secret.person@leak-test.example"
SIG = "Chevonne Nee Divver"


def utc(*a):
    return datetime(*a, tzinfo=UTC)


NOW = utc(2026, 10, 13, 12, 0)


def appt(**kw):
    d = dict(id="A1", customer_name="Mary Murphy", email=EMAIL, phone="+353851234567",
             country="IE", status="booked", starts_at=utc(2026, 10, 20, 13, 30),
             optout_sms_v2=False)
    d.update(kw)
    return d


class Tests(unittest.TestCase):
    def test_R1_keys_and_channel(self):
        res = plan_reminders([appt()], NOW)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertIn(r["channel"], ("sms", "email"))

    def test_R2_optout_v2_only(self):
        a = appt(opt_out=True)
        self.assertEqual(plan_reminders([a], NOW)[0]["channel"], "sms")
        b = appt()
        del b["optout_sms_v2"]
        self.assertEqual(plan_reminders([b], NOW)[0]["channel"], "sms")
        self.assertEqual(plan_reminders([appt(optout_sms_v2=True)], NOW)[0]["channel"], "email")

    def test_R3_two_reminders(self):
        res = plan_reminders([appt()], NOW)
        self.assertEqual([r["send_at"] for r in res], [utc(2026, 10, 18, 13, 30), utc(2026, 10, 20, 11, 30)])

    def test_R4_immediate_when_48h_passed(self):
        now = utc(2026, 10, 19, 12, 0)
        res = plan_reminders([appt()], now)
        self.assertEqual(res[0]["send_at"], now)
        self.assertEqual(res[1]["send_at"], utc(2026, 10, 20, 11, 30))

    def test_R5_never_before_now(self):
        for h in range(0, 24 * 5):
            now = utc(2026, 10, 17, 0, 0) + timedelta(hours=h, minutes=17)
            for s in (utc(2026, 10, 18, 9, 0), utc(2026, 10, 20, 13, 30), utc(2026, 10, 17, 23, 0)):
                for r in plan_reminders([appt(starts_at=s)], now):
                    self.assertGreaterEqual(r["send_at"], now)

    def test_R6_channels(self):
        self.assertEqual(plan_reminders([appt(phone="  ")], NOW)[0]["channel"], "email")
        self.assertEqual(plan_reminders([appt(phone=None)], NOW)[0]["channel"], "email")
        res = plan_reminders([appt(optout_sms_v2=True)], NOW)
        self.assertEqual({r["channel"] for r in res}, {"email"})
        with self.assertLogs("reminders", "DEBUG") as cm:
            self.assertEqual(plan_reminders([appt(optout_sms_v2=True, email=" ")], NOW), [])
        self.assertTrue(any(r.levelname == "WARNING" and "A1" in r.getMessage() for r in cm.records))

    def test_R7_boundary_160_161(self):
        best = None
        for n in range(1, 150):
            t = plan_reminders([appt(customer_name="a" * n)], NOW)[0]["text"]
            if "a" * n in t:
                best = (n, t)
        n, t = best
        self.assertEqual(len(t), 160)
        t2 = plan_reminders([appt(customer_name="a" * (n + 1))], NOW)[0]["text"]
        self.assertNotIn("a" * (n + 1), t2)
        self.assertLessEqual(len(t2), 160)
        for x in (t, t2):
            self.assertIn("20 Oct 2026 at 14:30", x)
            self.assertTrue(x.endswith(SIG))

    def test_R7_long_names(self):
        name = "Bartholomew Maximilian " * 20
        for r in plan_reminders([appt(customer_name=name)], NOW):
            self.assertLessEqual(len(r["text"]), 160)
            self.assertIn("at 14:30", r["text"])
            self.assertTrue(r["text"].endswith(SIG))
        res = plan_reminders([appt(customer_name="x" * 500, optout_sms_v2=True)], NOW)
        self.assertGreater(len(res[0]["text"]), 160)

    def test_R8_dublin_time(self):
        res = plan_reminders([appt()], NOW)
        self.assertIn("Tue 20 Oct 2026 at 14:30", res[0]["text"])
        res = plan_reminders([appt(starts_at=utc(2026, 7, 14, 13, 30))], utc(2026, 7, 1, 12, 0))
        self.assertIn("Tue 14 Jul 2026 at 14:30", res[0]["text"])
        self.assertEqual(res[0]["send_at"], utc(2026, 7, 12, 13, 30))

    def test_R9_quiet_hours_unit(self):
        f = reminders._apply_quiet_hours
        self.assertEqual(f(utc(2026, 7, 1, 19, 59)).astimezone(UTC), utc(2026, 7, 1, 19, 59))  # 20:59
        self.assertEqual(f(utc(2026, 7, 1, 20, 0)).astimezone(UTC), utc(2026, 7, 1, 19, 0))    # 21:00
        self.assertEqual(f(utc(2026, 7, 2, 6, 59)).astimezone(UTC), utc(2026, 7, 1, 19, 0))    # 07:59
        self.assertEqual(f(utc(2026, 7, 2, 7, 0)).astimezone(UTC), utc(2026, 7, 2, 7, 0))      # 08:00
        self.assertEqual(f(utc(2026, 7, 1, 20, 30)).astimezone(UTC), utc(2026, 7, 1, 19, 0))   # UTC input

    def test_R9_dst_transitions(self):
        f = lambda d: reminders._apply_quiet_hours(d).astimezone(UTC)
        self.assertEqual(f(utc(2026, 3, 29, 0, 30)), utc(2026, 3, 28, 20, 0))   # GMT 00:30
        self.assertEqual(f(utc(2026, 3, 29, 6, 30)), utc(2026, 3, 28, 20, 0))   # BST 07:30
        self.assertEqual(f(utc(2026, 3, 29, 7, 0)), utc(2026, 3, 29, 7, 0))     # BST 08:00 ok
        self.assertEqual(f(utc(2026, 10, 24, 23, 30)), utc(2026, 10, 24, 19, 0))  # BST 00:30 Oct 25
        self.assertEqual(f(utc(2026, 10, 25, 7, 30)), utc(2026, 10, 24, 19, 0))   # GMT 07:30
        self.assertEqual(f(utc(2026, 10, 25, 21, 0)), utc(2026, 10, 25, 20, 0))   # GMT 21:00

    def test_R9_dst_plan_level(self):
        r = plan_reminders([appt(starts_at=utc(2026, 3, 30, 9, 0))], utc(2026, 3, 25, 12, 0))
        self.assertEqual([x["send_at"] for x in r], [utc(2026, 3, 28, 9, 0), utc(2026, 3, 30, 7, 0)])
        r = plan_reminders([appt(starts_at=utc(2026, 3, 29, 11, 0))], utc(2026, 3, 25, 12, 0))
        self.assertEqual([x["send_at"] for x in r], [utc(2026, 3, 27, 11, 0), utc(2026, 3, 29, 9, 0)])
        r = plan_reminders([appt(starts_at=utc(2026, 10, 26, 9, 0))], utc(2026, 10, 20, 12, 0))
        self.assertEqual(r[1]["send_at"], utc(2026, 10, 25, 20, 0))

    def test_R10_cancelled(self):
        for s in ("cancelled", "Cancelled", " CANCELED ", "canceled"):
            self.assertEqual(plan_reminders([appt(status=s)], NOW), [])

    def test_R11_no_email_in_logs(self):
        bad = [
            {"id": "M1", "email": EMAIL},
            appt(id="M2", starts_at=datetime(2026, 10, 20, 13, 30)),
            appt(id="M3", starts_at="2026-10-20"),
            appt(id="M4", phone=12345, optout_sms_v2=True),
            appt(id="M5", optout_sms_v2=True, phone=None, email=" "),
            appt(id="M6", status="cancelled"),
            "not a dict",
            appt(id="G1"),
        ]
        with self.assertLogs("reminders", "DEBUG") as cm:
            res = plan_reminders(bad, NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"G1"})
        for rec in cm.records:
            self.assertNotIn(EMAIL, rec.getMessage())
            self.assertNotIn("secret.person", rec.getMessage())
            self.assertIsNone(rec.exc_info)
        self.assertNotIn(EMAIL, "\n".join(cm.output))

    def test_R12_signature(self):
        for r in plan_reminders([appt()], NOW) + plan_reminders([appt(optout_sms_v2=True)], NOW):
            self.assertTrue(r["text"].endswith(SIG))
        for c in ("PL", " pl "):
            for opt in (False, True):
                for r in plan_reminders([appt(country=c, optout_sms_v2=opt)], NOW):
                    self.assertTrue(r["text"].endswith("Grzegorz Szczepański"))
                    if r["channel"] == "sms":
                        self.assertLessEqual(len(r["text"]), 160)
        r = plan_reminders([appt(country="PL", customer_name="y" * 300)], NOW)
        self.assertTrue(all(len(x["text"]) <= 160 and x["text"].endswith("Grzegorz Szczepański") for x in r))

    def test_R13_R4_collapse_keeps_2h(self):
        s = NOW + timedelta(hours=2)
        res = plan_reminders([appt(starts_at=s)], NOW)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["send_at"], NOW)
        self.assertIn("coming up", res[0]["text"])

    def test_R14_aware_dublin(self):
        for r in plan_reminders([appt()], NOW):
            self.assertIsNotNone(r["send_at"].utcoffset())
            self.assertEqual(r["send_at"].tzinfo.key, "Europe/Dublin")

    def test_R15_sorting(self):
        res = plan_reminders([appt(id="B"), appt(id="A"), appt(id="C", starts_at=utc(2026, 10, 15, 13, 0))], NOW)
        keys = [r["send_at"] for r in res]
        self.assertEqual(keys, sorted(keys))
        same = [(r["appointment_id"], r["send_at"]) for r in res if r["appointment_id"] in "AB"]
        self.assertEqual([i for i, _ in same], ["A", "B", "A", "B"])

    def test_R16_stdlib_only(self):
        tree = ast.parse(open(reminders.__file__, encoding="utf-8").read())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add(n.module)
        self.assertLessEqual(mods, {"logging", "datetime", "zoneinfo"})

    def test_D2_quiet_now_drops_immediate(self):
        now = utc(2026, 10, 13, 22, 0)
        res = plan_reminders([appt(starts_at=utc(2026, 10, 14, 10, 0))], now)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["send_at"], utc(2026, 10, 14, 8, 0))  # 08:00 exactly allowed
        self.assertEqual(plan_reminders([appt(starts_at=utc(2026, 10, 14, 5, 0))], now), [])

    def test_D3_started_or_past(self):
        self.assertEqual(plan_reminders([appt(starts_at=NOW)], NOW), [])
        self.assertEqual(plan_reminders([appt(starts_at=NOW - timedelta(hours=1))], NOW), [])

    def test_D4_within_2h(self):
        res = plan_reminders([appt(starts_at=NOW + timedelta(hours=1))], NOW)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["send_at"], NOW)
        self.assertNotIn("coming up", res[0]["text"])

    def test_D5_early_appointment(self):
        res = plan_reminders([appt(starts_at=utc(2026, 10, 20, 9, 0))], NOW)
        self.assertEqual(res[1]["send_at"], utc(2026, 10, 19, 20, 0))

    def test_D7_robustness(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([appt()], datetime(2026, 10, 13, 12, 0))
        self.assertNotIn(EMAIL, str(cm.exception))
        orig = [appt(id="G"), {"id": "bad"}, appt(id="N", starts_at=datetime(2026, 10, 20, 1, 0))]
        snap = copy.deepcopy(orig)
        with self.assertLogs("reminders", "DEBUG") as cm:
            res = plan_reminders(orig, NOW)
        self.assertEqual(orig, snap)
        self.assertEqual({r["appointment_id"] for r in res}, {"G"})
        msgs = [r.getMessage() for r in cm.records if r.levelname == "WARNING"]
        self.assertTrue(any("bad" in m and "KeyError" in m for m in msgs))
        self.assertTrue(any("N" in m and "ValueError" in m for m in msgs))
        with self.assertLogs("reminders", "DEBUG") as cm:
            plan_reminders([42], NOW)
        self.assertIn("unknown", cm.records[0].getMessage())

    def test_D8_duplicates(self):
        self.assertEqual(len(plan_reminders([appt(), appt()], NOW)), 4)

    def test_D9_names(self):
        t = plan_reminders([appt(customer_name="  Mary   Murphy ")], NOW)[0]["text"]
        self.assertTrue(t.startswith("Hi Mary Murphy, "))
        for n in (None, "", "   "):
            self.assertTrue(plan_reminders([appt(customer_name=n)], NOW)[0]["text"].startswith("Hi there, "))
        e = plan_reminders([appt(customer_name="Mary", optout_sms_v2=True)], NOW)[0]["text"]
        self.assertTrue(e.endswith("\n" + SIG))

    def test_house_rule_info_line_per_reminder(self):
        with self.assertLogs("reminders", "INFO") as cm:
            plan_reminders([appt(), appt(id="E", optout_sms_v2=True)], NOW)
        lines = [r.getMessage() for r in cm.records if "reminder planned" in r.getMessage()]
        self.assertEqual(len(lines), 4)
        self.assertTrue(all(("channel=sms" in l and "phone ending 4567" in l) or
                            ("channel=email" in l and "email address on file" in l) for l in lines))
        self.assertFalse(any(EMAIL in l for l in lines))


if __name__ == "__main__":
    unittest.main()