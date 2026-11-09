"""Brennan Opticians appointment reminder planner (pure, stdlib only).

Public entry point: plan_reminders(appointments, now) -> list of dicts with keys
appointment_id, channel, send_at, text. No sending, no clock, no network.
Tests are in this module: python3 this_file.py

Logging: one INFO line per planned reminder with appointment id and channel.
The contact value is deliberately NOT logged (R10 forbids emails, phones, names
and message text in logs), so support traces deliveries by appointment id.

Easy-to-change defaults live in the constants below.

Open points for the client
- Stateless: repeated runs re-emit immediate reminders (send_at == now); the
  caller must dedupe.
- Polish customers' time zone: COUNTRY_TZ["PL"] defaults to Europe/Dublin
  (R13 followed literally). Change it there if Warsaw time is wanted. The
  country zone drives text and quiet hours; send_at is always Europe/Dublin.
- "n with acute" (and any accent) forces SMS to UCS-2 encoding (70 chars per
  segment), so a 160 code point SMS may be billed as several segments.
- If a reminder falls in quiet hours and 20:00 before has passed, it is moved
  FORWARD to 08:00 (can be later than the nominal time, still before start).
- Missing/None optout_sms_v2 is treated as opted out (fail closed, no SMS).
- Template, date format and email subject are unspecified; output has text only.
"""
import copy
import io
import logging
import unicodedata
import unittest
from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("brennan.reminders")

DUBLIN = ZoneInfo("Europe/Dublin")
DEFAULT_TZ = DUBLIN
COUNTRY_TZ = {"PL": DUBLIN}  # [ASSUMPTION] per-country text/quiet-hours zone
OFFSETS = (timedelta(hours=48), timedelta(hours=2))  # [ASSUMPTION]
QUIET_START_H, QUIET_END_H, SHIFT_BACK_H = 21, 8, 20  # [ASSUMPTION]
SMS_LIMIT = 160
SIGNATURE = "Chevonne Nee Divver"
SIGNATURE_PL = "Grzegorz Szcz\u0119pa\u0144ski".replace("\u0119", "e\u0328") if False else "Grzegorz Szczepa\u0144ski"
PL_COUNTRY = "PL"
CANCELLED = {"cancelled", "canceled"}
TEMPLATE = "Hi{name}, your Brennan Opticians appointment is on {date} at {hhmm}. {sig}"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _text(v):
    """Stripped string or '' (blank/non-string = absent)."""
    return v.strip() if isinstance(v, str) else ""


def _aware(v):
    return isinstance(v, datetime) and v.utcoffset() is not None


def _country(appt):
    return _text(appt.get("country")).upper()


def _tz(country):
    return COUNTRY_TZ.get(country, DEFAULT_TZ)


def _adjust(cand, now, tz):
    """Quiet hours [21:00, 08:00): back to prior 20:00, else forward to 08:00."""
    loc = cand.astimezone(tz)
    if QUIET_END_H <= loc.hour < QUIET_START_H:
        return cand
    day = loc.date()
    if loc.hour >= QUIET_START_H:
        back_day, fwd_day = day, day + timedelta(days=1)
    else:
        back_day, fwd_day = day - timedelta(days=1), day
    back = datetime.combine(back_day, time(SHIFT_BACK_H), tz)
    if back < now:
        return datetime.combine(fwd_day, time(QUIET_END_H), tz)
    return back


def _compose(name, loc_start, sig):
    date = f"{loc_start.day:02d} {MONTHS[loc_start.month - 1]} {loc_start.year}"
    hhmm = f"{loc_start.hour:02d}:{loc_start.minute:02d}"
    n = f" {name}" if name else ""
    return _nfc(TEMPLATE.format(name=n, date=date, hhmm=hhmm, sig=sig))


def _name_options(raw):
    parts = _nfc(raw).split() if isinstance(raw, str) else []
    if not parts:
        return [""]
    first = parts[0]
    opts = [" ".join(parts)]
    if len(parts) > 1:
        opts.append(f"{first} {parts[-1][0].upper()}.")
    opts += [first, f"{first[0].upper()}.", ""]
    return opts


def _build_text(appt, channel, loc_start, sig):
    opts = _name_options(appt.get("customer_name"))
    if channel == "email":
        return _compose(opts[0], loc_start, sig)
    for n in opts:
        t = _compose(n, loc_start, sig)
        if len(t) <= SMS_LIMIT:
            return t
    return _compose("", loc_start, sig)


def plan_reminders(appointments, now):
    if not _aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    out = []
    for appt in appointments:
        if not isinstance(appt, Mapping):
            log.warning("skipped appointment id=<unknown> reason=malformed")
            continue
        aid = appt.get("id")
        if isinstance(aid, bool) or not isinstance(aid, (str, int)) or str(aid).strip() == "":
            log.warning("skipped appointment id=<missing> reason=malformed")
            continue
        starts = appt.get("starts_at")
        if not _aware(starts):
            log.warning("skipped appointment id=%s reason=malformed", aid)
            continue
        if _text(appt.get("status")).casefold() in CANCELLED or starts <= now:
            continue
        has_phone = bool(_text(appt.get("phone")))
        has_email = bool(_text(appt.get("email")))
        if has_phone and appt.get("optout_sms_v2") is False:
            channel = "sms"
        elif has_email:
            channel = "email"
        else:
            reason = "optout_no_email" if has_phone else "no_contact"
            log.info("no reminders appointment id=%s reason=%s", aid, reason)
            continue
        country = _country(appt)
        tz = _tz(country)
        sig = SIGNATURE_PL if country == PL_COUNTRY else SIGNATURE
        text = _build_text(appt, channel, starts.astimezone(tz), sig)
        sends = []
        for off in OFFSETS:
            cand = starts.astimezone(timezone.utc) - off
            if cand < now:
                cand = now
            send = _adjust(cand, now, tz)
            if send >= starts:
                continue
            sends.append(send)
        if len(sends) == 2 and sends[0] == sends[1]:
            sends = sends[1:]
        for s in sends:
            out.append({"appointment_id": aid, "channel": channel,
                        "send_at": s.astimezone(DUBLIN), "text": text})
    out.sort(key=lambda r: r["send_at"])  # stable: ties keep input order
    for r in out:
        log.info("reminder planned appointment_id=%s channel=%s send_at=%s",
                 r["appointment_id"], r["channel"], r["send_at"].isoformat())
    return out


# ----------------------------------------------------------------- tests
def D(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=DUBLIN)


def A(**kw):
    base = {"id": "a1", "customer_name": "Mary Murphy", "email": "mary@example.com",
            "phone": "+353851234567", "country": "IE", "status": "booked",
            "starts_at": D(2026, 7, 15, 10), "optout_sms_v2": False}
    base.update(kw)
    return base


class PlanTests(unittest.TestCase):
    def sends(self, appt, now):
        return [r["send_at"] for r in plan_reminders([appt], now)]

    def test_july_acs(self):
        cases = [
            (D(2026, 7, 10, 12), D(2026, 7, 15, 10), [D(2026, 7, 13, 10), D(2026, 7, 15, 8)]),
            (D(2026, 7, 10, 12), D(2026, 7, 15, 9, 30), [D(2026, 7, 13, 9, 30), D(2026, 7, 14, 20)]),
            (D(2026, 7, 14, 10), D(2026, 7, 15, 9, 30), [D(2026, 7, 14, 10), D(2026, 7, 14, 20)]),
            (D(2026, 7, 14, 22, 30), D(2026, 7, 15, 9, 30), [D(2026, 7, 15, 8)]),
            (D(2026, 7, 15, 9), D(2026, 7, 15, 9, 30), [D(2026, 7, 15, 9)]),
            (D(2026, 7, 15, 9, 45), D(2026, 7, 15, 9, 30), []),
        ]
        for now, st, exp in cases:
            self.assertEqual(self.sends(A(starts_at=st), now), exp)

    def test_quiet_boundaries(self):
        self.assertEqual(self.sends(A(starts_at=D(2026, 7, 15, 23)), D(2026, 7, 14, 12))[-1],
                         D(2026, 7, 15, 20))
        self.assertEqual(self.sends(A(starts_at=D(2026, 7, 15, 10)), D(2026, 7, 14, 12))[-1],
                         D(2026, 7, 15, 8))

    def test_dst_oct_48h(self):
        r = self.sends(A(starts_at=D(2026, 10, 26, 10)), D(2026, 10, 20, 12))
        self.assertEqual(r[0], D(2026, 10, 24, 11))
        self.assertEqual(r[0].utcoffset(), timedelta(hours=1))

    def test_dst_march_elapsed(self):
        r = self.sends(A(starts_at=D(2026, 3, 30, 10)), D(2026, 3, 25, 12))
        self.assertEqual(r[0], datetime(2026, 3, 28, 9, tzinfo=timezone.utc))
        self.assertEqual(r[0].hour, 9)

    def test_dst_quiet_shift(self):
        r = self.sends(A(starts_at=D(2026, 3, 29, 9, 30)), D(2026, 3, 25, 12))
        self.assertEqual(r[-1], datetime(2026, 3, 28, 20, tzinfo=timezone.utc))
        r = self.sends(A(starts_at=D(2026, 10, 25, 9, 30)), D(2026, 10, 20, 12))
        self.assertEqual(r[-1], datetime(2026, 10, 24, 19, tzinfo=timezone.utc))

    def test_text_and_tz(self):
        r = plan_reminders([A(starts_at=datetime(2026, 7, 15, 9, tzinfo=timezone.utc))],
                           D(2026, 7, 10, 12))
        self.assertEqual(r[0]["text"], "Hi Mary Murphy, your Brennan Opticians appointment "
                         "is on 15 Jul 2026 at 10:00. Chevonne Nee Divver")
        self.assertEqual(set(r[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertEqual(r[0]["send_at"].tzinfo, DUBLIN)

    def test_long_names(self):
        for name in ("A" * 70 + " " + "B" * 79, "C" * 150):
            r = plan_reminders([A(customer_name=name)], D(2026, 7, 10, 12))
            for x in r:
                t = x["text"]
                self.assertEqual(x["channel"], "sms")
                self.assertLessEqual(len(t), 160)
                self.assertIn("15 Jul 2026 at 10:00", t)
                self.assertTrue(t.endswith("Chevonne Nee Divver"))
        self.assertIn("Hi C., your", r[0]["text"])
        self.assertIn("Hi AAAA", plan_reminders([A(customer_name="A" * 70 + " " + "B" * 79)],
                                                D(2026, 7, 10, 12))[0]["text"])

    def test_email_not_shortened(self):
        r = plan_reminders([A(customer_name="C" * 300, optout_sms_v2=True)], D(2026, 7, 10, 12))
        self.assertEqual(r[0]["channel"], "email")
        self.assertIn("C" * 300, r[0]["text"])

    def test_optout_flags(self):
        n = D(2026, 7, 10, 12)
        r = plan_reminders([A(optout_sms_v2=True, opt_out=False)], n)
        self.assertEqual({x["channel"] for x in r}, {"email"})
        r = plan_reminders([A(optout_sms_v2=False, opt_out=True)], n)
        self.assertEqual({x["channel"] for x in r}, {"sms"})
        a = A()
        del a["optout_sms_v2"]
        self.assertEqual({x["channel"] for x in plan_reminders([a], n)}, {"email"})

    def test_no_channel(self):
        n = D(2026, 7, 10, 12)
        self.assertEqual(plan_reminders([A(optout_sms_v2=True, email=" ")], n), [])
        self.assertEqual(plan_reminders([A(phone="  ", email=None)], n), [])
        r = plan_reminders([A(phone="  ")], n)
        self.assertEqual({x["channel"] for x in r}, {"email"})

    def test_cancelled(self):
        for s in (" Cancelled ", "CANCELED", "cancelled"):
            self.assertEqual(plan_reminders([A(status=s)], D(2026, 7, 10, 12)), [])

    def test_polish_signature(self):
        r = plan_reminders([A(country=" pl ", customer_name="Zo\u0301fia")], D(2026, 7, 10, 12))
        self.assertTrue(r[0]["text"].endswith("Grzegorz Szczepa\u0144ski"))
        self.assertIn("Z\u00f3fia", r[0]["text"])

    def test_naive_now_and_malformed(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 7, 10, 12))
        bad = [A(id="bad1", starts_at=datetime(2026, 7, 15, 10)), A(id=None),
               A(id="bad2", starts_at=None), "x", A(id="ok")]
        r = plan_reminders(bad, D(2026, 7, 10, 12))
        self.assertEqual({x["appointment_id"] for x in r}, {"ok"})

    def test_no_mutation_and_order(self):
        apps = [A(id="b", starts_at=D(2026, 7, 16, 10)), A(id="a")]
        snap = copy.deepcopy(apps)
        r = plan_reminders(apps, D(2026, 7, 10, 12))
        self.assertEqual(apps, snap)
        self.assertEqual([x["send_at"] for x in r], sorted(x["send_at"] for x in r))
        r = plan_reminders([A(id="x", starts_at=D(2026, 7, 11, 10)),
                            A(id="y", starts_at=D(2026, 7, 11, 10))], D(2026, 7, 10, 12))
        self.assertEqual([x["appointment_id"] for x in r][:2], ["x", "y"])

    def test_logging_privacy(self):
        buf = io.StringIO()
        h = logging.StreamHandler(buf)
        root = logging.getLogger()
        old = root.level
        root.addHandler(h)
        root.setLevel(logging.DEBUG)
        try:
            apps = [A(id="bad", starts_at=datetime(2026, 7, 15, 10), email="leak@secret.com",
                      phone="0851112222", customer_name="Secretname"),
                    A(id="noemail", optout_sms_v2=True, email="", phone="0853334444",
                      customer_name="Hidden Person"),
                    A(id="fine", email="fine@secret.com", phone="0855556666",
                      customer_name="Visible Nobody"),
                    A(id="mail", optout_sms_v2=True, email="m@secret.com")]
            res = plan_reminders(apps, D(2026, 7, 10, 12))
            with self.assertRaises(ValueError) as cm:
                plan_reminders(apps, datetime(2026, 7, 10))
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        out = buf.getvalue() + str(cm.exception)
        self.assertIn("bad", out)
        self.assertIn("noemail", out)
        for s in ("secret.com", "0851112222", "0853334444", "0855556666", "Secretname",
                  "Hidden", "Visible", "Brennan", "@"):
            self.assertNotIn(s, out)
        self.assertEqual(sum("reminder planned" in ln for ln in buf.getvalue().splitlines()),
                         len(res))


if __name__ == "__main__":
    unittest.main()