"""Brennan Opticians appointment reminder planner (stdlib only).

Entry point: plan_reminders(appointments, now). Run the embedded tests with:
    python3 -I -m unittest <path to this file>

ASSUMPTIONS
A1  Per appointment: skip cancelled (R10); skip if starts_at <= now; t48 = start-48h,
    t2 = start-2h, computed on absolute UTC instants (R15). t48 < now -> now (R5).
A2  adjust_for_quiet_hours: Dublin hour >= 21 -> same day 20:00; hour < 8 -> previous
    day 20:00; 08:00..20:59:59 unchanged.
A3  If the adjusted time is before now (R6 beats R9): candidate = now if now is in
    allowed hours, else the next 08:00 Dublin. Used only if candidate < start-30min,
    otherwise the reminder is dropped (logged). So R5's "immediately" becomes the next
    08:00 when now is in quiet hours.
A4  If both reminders land on the same instant, keep only the 2h one (R13).
A5  Channel: phone and not opted out -> sms; else email if it contains "@"; else no
    reminder (WARNING "no_channel"). Missing/None/unrecognised optout_sms_v2 is treated
    as opted out (missing key also logs a WARNING). Only bool and "true"/"false" strings
    are interpreted.
A6  Neutral wording ("is coming up") for both kinds and both channels.
A7  SMS limit is len() <= 160 on the final text. sms_needs_ucs2() flags non-GSM-7 chars
    (a WARNING is logged, id only). No transliteration. OPEN QUESTION for client:
    should the limit count UCS-2 segments (70 chars) given the diacritics in the
    signatures? Name shortening: full, "First L.", first, truncated first + "…", none.
A8  Malformed records are skipped with a WARNING; naive now raises ValueError; input is
    not mutated; duplicate ids are processed independently.
A9  Logger "brennan_reminders". The house rule asks for the contact in the INFO line,
    but R11/A9 forbid logging email, phone and name, so each INFO line carries
    appointment id, channel, kind and send_at only.
A10 send_at is returned in Europe/Dublin; output dicts have exactly four keys.
A11 If the 2h point is already past it moves to now, then A2/A3 apply and A4 resolves
    the collision with the 48h reminder.
R17 No legacy code is imported or referenced.
"""
import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
log = logging.getLogger("brennan_reminders")

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_GSM = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
           "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\\[~]|€")


def sms_needs_ucs2(text):
    return any(c not in _GSM for c in text)


def _in_quiet(dt):
    h = dt.astimezone(DUB).hour
    return h >= 21 or h < 8


def adjust_for_quiet_hours(dt):
    d = dt.astimezone(DUB)
    if d.hour >= 21:
        day = d.date()
    elif d.hour < 8:
        day = d.date() - timedelta(days=1)
    else:
        return d
    return datetime(day.year, day.month, day.day, 20, tzinfo=DUB)


def _next_allowed(now):
    d = now.astimezone(DUB)
    if not _in_quiet(d):
        return d
    day = d.date() + timedelta(days=1) if d.hour >= 21 else d.date()
    return datetime(day.year, day.month, day.day, 8, tzinfo=DUB)


def _clean(s):
    if not isinstance(s, str):
        return ""
    s = "".join(" " if unicodedata.category(c).startswith("C") else c for c in s)
    return " ".join(s.split())


def _fmt_date(d):
    return f"{_DAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]} {d.year}"


def _sms_text(name, date, hhmm, sig):
    def build(n):
        greet = f"Hi {n}," if n else "Hi,"
        return f"{greet} reminder: your Brennan Opticians appointment is on {date} at {hhmm}. {sig}"

    def cands():
        yield name
        parts = name.split()
        if len(parts) > 1:
            yield f"{parts[0]} {parts[-1][0]}."
        if parts:
            yield parts[0]
            for k in range(len(parts[0]) - 1, 0, -1):
                yield parts[0][:k] + "…"
        yield ""

    for c in cands():
        t = build(c)
        if len(t) <= 160:
            return t
    return build("")


def _email_text(name, date, hhmm, sig):
    greet = f"Hi {name}," if name else "Hi,"
    return (f"{greet}\n\nThis is a friendly reminder that your appointment at Brennan "
            f"Opticians is coming up on {date} at {hhmm}.\n\n"
            f"If you need to change it, please get in touch.\n\nKind regards,\n{sig}")


def _opted_out(appt, aid):
    if "optout_sms_v2" not in appt:
        log.warning("appointment id=%s: optout_sms_v2 missing, treating as opted out", aid)
        return True
    v = appt["optout_sms_v2"]
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return True


def _plan_one(appt, now):
    aid = appt.get("id") if isinstance(appt, dict) else None
    start = appt.get("starts_at") if isinstance(appt, dict) else None
    if aid is None or not isinstance(start, datetime) or start.utcoffset() is None:
        log.warning("skipping malformed appointment id=%s", aid)
        return []
    if str(appt.get("status") or "").strip().lower() == "cancelled":
        log.info("appointment id=%s skipped: cancelled", aid)
        return []
    start = start.astimezone(timezone.utc)
    if start <= now:
        log.info("appointment id=%s skipped: already started", aid)
        return []
    phone = appt.get("phone")
    email = appt.get("email")
    has_phone = isinstance(phone, str) and bool(phone.strip())
    has_email = isinstance(email, str) and "@" in email.strip()
    opted_out = _opted_out(appt, aid)
    if has_phone and not opted_out:
        channel = "sms"
    elif has_email:
        channel = "email"
    else:
        log.warning("appointment id=%s: no_channel", aid)
        return []

    sig = "Grzegorz Szczepański" if str(appt.get("country") or "").strip().upper() == "PL" \
        else "Siobhán Ní Dhuibhir"
    local = start.astimezone(DUB)
    date, hhmm = _fmt_date(local), local.strftime("%H:%M")
    name = _clean(appt.get("customer_name"))
    if channel == "sms":
        text = _sms_text(name, date, hhmm, sig)
        if sms_needs_ucs2(text):
            log.warning("appointment id=%s: sms may be split into multiple segments", aid)
    else:
        text = _email_text(name, date, hhmm, sig)

    planned = {}
    for rank, kind, t in ((0, "48h", start - timedelta(hours=48)), (1, "2h", start - timedelta(hours=2))):
        t = max(t, now)
        adj = adjust_for_quiet_hours(t)
        if adj >= now:
            send = adj
        else:
            cand = _next_allowed(now)
            if cand < start - timedelta(minutes=30):
                send = cand
            else:
                log.info("appointment id=%s %s reminder dropped: quiet_hours_too_close_to_start", aid, kind)
                continue
        planned[rank] = (kind, send)
    if 0 in planned and 1 in planned and planned[0][1] == planned[1][1]:
        log.info("appointment id=%s 48h reminder dropped: collides with 2h reminder", aid)
        del planned[0]
    out = []
    for rank, (kind, send) in planned.items():
        send = send.astimezone(DUB)
        log.info("planned reminder appointment_id=%s channel=%s kind=%s send_at=%s",
                 aid, channel, kind, send.isoformat())
        out.append((send, str(aid), rank,
                    {"appointment_id": aid, "channel": channel, "send_at": send, "text": text}))
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    items = []
    for appt in appointments:
        try:
            items.extend(_plan_one(appt, now))
        except Exception as e:  # one bad record must not abort the batch
            aid = appt.get("id") if isinstance(appt, dict) else None
            log.warning("appointment id=%s skipped: error %s", aid, type(e).__name__)
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in items]


# ----------------------------------------------------------------- tests
import unittest  # noqa: E402


def L(*a):
    return datetime(*a, tzinfo=DUB)


def mk(start, **kw):
    d = dict(id="a1", customer_name="Aoife Ní Bhriain-Murphy", email="secret.person@example.com",
             phone="+353851234567", country="IE", status="booked", starts_at=start,
             optout_sms_v2=False)
    d.update(kw)
    return d


NOW = L(2026, 10, 13, 12, 0)


class T(unittest.TestCase):
    def test_R1_R2_shape(self):
        r = plan_reminders([mk(L(2026, 10, 18, 14, 0))], NOW)
        self.assertEqual(len(r), 2)
        for x in r:
            self.assertEqual(set(x), {"appointment_id", "channel", "send_at", "text"})
            self.assertIn(x["channel"], ("sms", "email"))

    def test_R3_optout_v2_only(self):
        s = L(2026, 10, 18, 14, 0)
        r = plan_reminders([mk(s, opt_out=True, optout_sms_v2=False)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"sms"})
        r = plan_reminders([mk(s, opt_out=False, optout_sms_v2=True)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_R4_two_reminders(self):
        r = plan_reminders([mk(L(2026, 10, 18, 14, 0))], NOW)
        self.assertEqual([x["send_at"] for x in r], [L(2026, 10, 16, 14, 0), L(2026, 10, 18, 12, 0)])

    def test_R5_immediate_first(self):
        r = plan_reminders([mk(NOW + timedelta(hours=10))], NOW)
        self.assertEqual([x["send_at"] for x in r], [NOW, L(2026, 10, 13, 20, 0)])

    def test_R6_never_past_sweep(self):
        for h in range(0, 24, 3):
            for out in (1, 3, 5, 12, 30, 47, 49, 100):
                now = L(2026, 10, 13, h, 17)
                for x in plan_reminders([mk(now + timedelta(hours=out))], now):
                    self.assertGreaterEqual(x["send_at"], now)
                    self.assertFalse(_in_quiet(x["send_at"]))

    def test_R7_channels(self):
        s = L(2026, 10, 18, 14, 0)
        self.assertEqual({x["channel"] for x in plan_reminders([mk(s, phone="")], NOW)}, {"email"})
        self.assertEqual({x["channel"] for x in plan_reminders([mk(s, optout_sms_v2=True)], NOW)}, {"email"})
        self.assertEqual({x["channel"] for x in plan_reminders([mk(s)], NOW)}, {"sms"})

    def test_R8_sms_length(self):
        s = L(2026, 10, 18, 14, 0)
        for nm in ("A" * 200, " ".join(["Bartholomew"] * 20)):
            for c in ("IE", "PL"):
                for x in plan_reminders([mk(s, customer_name=nm, country=c)], NOW):
                    self.assertLessEqual(len(x["text"]), 160)
                    self.assertIn("Sun 18 Oct 2026 at 14:00", x["text"])
        x = plan_reminders([mk(s)], NOW)[0]
        self.assertIn("Hi Aoife Ní Bhriain-Murphy,", x["text"])

    def test_R9_boundaries(self):
        a = adjust_for_quiet_hours
        t = L(2026, 10, 13, 20, 59, 59)
        self.assertEqual(a(t), t)
        self.assertEqual(a(L(2026, 10, 13, 21, 0)), L(2026, 10, 13, 20, 0))
        self.assertEqual(a(L(2026, 10, 13, 7, 59)), L(2026, 10, 12, 20, 0))
        self.assertEqual(a(L(2026, 10, 13, 8, 0)), L(2026, 10, 13, 8, 0))
        self.assertEqual(a(L(2026, 3, 29, 7, 59)), L(2026, 3, 28, 20, 0))
        self.assertEqual(a(L(2026, 10, 25, 2, 30)), L(2026, 10, 24, 20, 0))
        self.assertEqual(a(L(2026, 10, 25, 21, 0)), L(2026, 10, 25, 20, 0))

    def test_R9_R15_absolute_48h_across_dst(self):
        now = L(2026, 10, 20, 12, 0)
        r = plan_reminders([mk(L(2026, 10, 26, 14, 0))], now)
        self.assertEqual(r[0]["send_at"], L(2026, 10, 24, 15, 0))

    def test_R9_R6_conflicts(self):
        now = L(2026, 10, 13, 21, 30)
        r = plan_reminders([mk(L(2026, 10, 14, 15, 0))], now)
        self.assertEqual([x["send_at"] for x in r], [L(2026, 10, 14, 8, 0), L(2026, 10, 14, 13, 0)])
        r = plan_reminders([mk(L(2026, 10, 14, 9, 0))], now)
        self.assertEqual([x["send_at"] for x in r], [L(2026, 10, 14, 8, 0)])
        self.assertEqual(plan_reminders([mk(L(2026, 10, 14, 8, 20))], now), [])

    def test_R10_cancelled(self):
        s = L(2026, 10, 18, 14, 0)
        for st in ("Cancelled ", "cancelled", " CANCELLED"):
            self.assertEqual(plan_reminders([mk(s, status=st)], NOW), [])

    def test_R11_no_pii_in_logs(self):
        s = L(2026, 10, 18, 14, 0)
        bad = mk(s, id="bad", starts_at="x")
        with self.assertLogs("brennan_reminders", level="DEBUG") as cm:
            plan_reminders([mk(s, optout_sms_v2=True), mk(s, id="a2"), bad], NOW)
        for rec in cm.records:
            blob = rec.getMessage() + str(rec.args)
            for secret in ("secret.person@example.com", "secret.person", "+353851234567", "Aoife"):
                self.assertNotIn(secret, blob)

    def test_R12_signature(self):
        s = L(2026, 10, 18, 14, 0)
        for country, sig in (("PL", "Grzegorz Szczepański"), ("IE", "Siobhán Ní Dhuibhir"),
                             (None, "Siobhán Ní Dhuibhir")):
            for ov in (False, True):
                for x in plan_reminders([mk(s, country=country, optout_sms_v2=ov)], NOW):
                    self.assertTrue(x["text"].endswith(sig))

    def test_R13_collision_keeps_2h(self):
        r = plan_reminders([mk(L(2026, 10, 13, 13, 0))], NOW)
        self.assertEqual([x["send_at"] for x in r], [NOW])

    def test_R14_R15_display_timezone(self):
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        t = plan_reminders([mk(datetime(2026, 7, 1, 13, 0, tzinfo=timezone.utc))], now)[0]["text"]
        self.assertIn("Wed 1 Jul 2026 at 14:00", t)
        t = plan_reminders([mk(datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc))],
                           datetime(2026, 1, 1, tzinfo=timezone.utc))[0]["text"]
        self.assertIn("15 Jan 2026 at 14:00", t)
        t = plan_reminders([mk(datetime(2026, 7, 1, 23, 30, tzinfo=timezone.utc))], now)[0]["text"]
        self.assertIn("2 Jul 2026 at 00:30", t)

    def test_R16_sorted(self):
        a = [mk(L(2026, 10, 20, 14, 0), id="b"), mk(L(2026, 10, 18, 14, 0), id="a"),
             mk(L(2026, 10, 18, 14, 0), id="A")]
        r = plan_reminders(a, NOW)
        keys = [x["send_at"] for x in r]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([x["appointment_id"] for x in r[:2]], ["A", "a"])

    def test_R17_stdlib_only(self):
        import ast
        import sys
        tree = ast.parse(open(__file__, encoding="utf-8").read())
        for n in ast.walk(tree):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                [n.module] if isinstance(n, ast.ImportFrom) else []
            for m in names:
                self.assertIn(m.split(".")[0], sys.stdlib_module_names)

    def test_A5_no_channel(self):
        s = L(2026, 10, 18, 14, 0)
        self.assertEqual(plan_reminders([mk(s, phone=None, email="")], NOW), [])
        self.assertEqual(plan_reminders([mk(s, optout_sms_v2=True, email=None)], NOW), [])
        d = mk(s)
        del d["optout_sms_v2"]
        self.assertEqual({x["channel"] for x in plan_reminders([d], NOW)}, {"email"})
        self.assertEqual({x["channel"] for x in plan_reminders([mk(s, optout_sms_v2="false")], NOW)}, {"sms"})
        self.assertEqual({x["channel"] for x in plan_reminders([mk(s, optout_sms_v2="maybe")], NOW)}, {"email"})

    def test_A8_validation(self):
        import copy
        s = L(2026, 10, 18, 14, 0)
        a = [mk(datetime(2026, 10, 18, 14, 0)), mk("x", id="b"), {"starts_at": s}, mk(s, id="ok")]
        before = copy.deepcopy(a)
        r = plan_reminders(a, NOW)
        self.assertEqual({x["appointment_id"] for x in r}, {"ok"})
        self.assertEqual(a, before)
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 10, 13, 12, 0))

    def test_A7_ucs2_helper(self):
        self.assertTrue(sms_needs_ucs2("Siobhán"))
        self.assertFalse(sms_needs_ucs2("Hello 12:00"))


if __name__ == "__main__":
    unittest.main()