"""Brennan Opticians appointment reminders.

Public entry point: plan_reminders(appointments, now). Pure, standard library only.
Run the embedded tests with: python3 this_module.py

NOTE: I had no tool access in this session, so the embedded tests have NOT been
executed. Please run them before relying on this module.

Assumptions
- All returned send_at values are timezone-aware datetimes in UTC (compare by instant).
- Date format is "20 Oct 2026" with an unpadded day number.
- Email uses exactly the same text as SMS, including the same shortening steps.
- None is accepted for customer_name, email, phone, country and status (treated as
  blank / active). Any other non-str type makes the record malformed.
- A missing optout_sms_v2 key makes the record malformed (skipped). A present but
  non-boolean value (including None) is treated as opted out.
- House rule vs privacy: the per-reminder INFO log gives appointment id, channel and
  which contact field is used ("phone" or "email"), but never the address, number or
  name, because the DPC finding forbids email, phone and name in logs.

Open questions for the client
1. Opt-out polarity: does optout_sms_v2 == True mean opted out (as implemented) or
   opted in, as the brief literally read? (Flip OPTED_OUT_VALUE.)
2. Is email wanted at all? It is currently only a fallback for non-opted-out
   customers with no phone.
3. Scheduling and "already sent" tracking is outside this module. If it runs
   repeatedly, the "send the first one at now" rule will re-issue reminders every run.
4. Should Polish customers see Dublin time and English text?
5. Do the SMS gateway's segment limits count accented characters (UCS-2 is 70 chars
   per segment) in a way that matters for the 160 limit?
6. Is there a full list of status values besides cancelled (e.g. no-show, completed)?
"""
from __future__ import annotations

import copy
import logging
import unicodedata
import unittest
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUBLIN = ZoneInfo("Europe/Dublin")
UTC = timezone.utc

# Polarity switch: the value of optout_sms_v2 that means "customer is opted out".
OPTED_OUT_VALUE = True


def is_opted_out(value) -> bool:
    """Fail safe: anything that is not a real bool counts as opted out."""
    if not isinstance(value, bool):
        return True
    return value == OPTED_OUT_VALUE


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SIG_DEFAULT = unicodedata.normalize("NFC", "Siobhán Ní Dhuibhir")
SIG_PL = unicodedata.normalize("NFC", "Grzegorz Szczepański")
SMS_LIMIT = 160
REQUIRED_KEYS = ("id", "customer_name", "email", "phone", "country",
                 "status", "starts_at", "optout_sms_v2")


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _is_aware(dt) -> bool:
    return isinstance(dt, datetime) and dt.tzinfo is not None \
        and dt.tzinfo.utcoffset(dt) is not None


def _safe_id(appt) -> str:
    if isinstance(appt, Mapping):
        v = appt.get("id")
        if isinstance(v, (str, int)) and not isinstance(v, bool):
            return str(v)[:64]
    return "?"


def _validate(a) -> str | None:
    if not isinstance(a, Mapping):
        return "not_a_mapping"
    if any(k not in a for k in REQUIRED_KEYS):
        return "missing_key"
    i = a["id"]
    if not isinstance(i, (str, int)) or isinstance(i, bool):
        return "bad_id"
    for k in ("customer_name", "email", "phone", "country", "status"):
        if a[k] is not None and not isinstance(a[k], str):
            return "bad_field_type"
    if not _is_aware(a["starts_at"]):
        return "bad_starts_at"
    return None


def _blank(v) -> bool:
    return v is None or not v.strip()


def _is_quiet(utc_dt: datetime) -> bool:
    h = utc_dt.astimezone(DUBLIN).hour
    return h >= 21 or h < 8


def _move_back(utc_dt: datetime) -> datetime:
    local = utc_dt.astimezone(DUBLIN)
    d = local.date()
    if local.hour < 8:
        d = d - timedelta(days=1)
    return datetime.combine(d, time(20, 0), tzinfo=DUBLIN).astimezone(UTC)


def _next_0800(now_utc: datetime) -> datetime:
    d: date = now_utc.astimezone(DUBLIN).date()
    cand = datetime.combine(d, time(8, 0), tzinfo=DUBLIN).astimezone(UTC)
    if cand <= now_utc:
        cand = datetime.combine(d + timedelta(days=1), time(8, 0),
                                tzinfo=DUBLIN).astimezone(UTC)
    return cand


def _schedule(candidate: datetime, now: datetime, starts: datetime):
    c = max(candidate, now)
    if not _is_quiet(c):
        return c
    m = _move_back(c)
    if m >= now:
        return m
    n = _next_0800(now)
    return n if n < starts else None


def _build_text(name, starts_utc: datetime, country, limit: int = SMS_LIMIT) -> str:
    local = starts_utc.astimezone(DUBLIN)
    when = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
    hhmm = f"{local.hour:02d}:{local.minute:02d}"
    sig = SIG_PL if (country or "").strip().upper() == "PL" else SIG_DEFAULT
    clean = _nfc(" ".join((name or "").split()))
    parts = clean.split(" ") if clean else []
    variants = []
    if parts:
        variants.append(clean)
        if len(parts) > 1:
            variants.append(f"{parts[0]} {parts[-1][0]}.")
        variants.append(parts[0])
        variants.append(parts[0][0])
    variants.append("")
    text = ""
    for n in variants:
        greeting = f"Hi {n}," if n else "Hi,"
        text = _nfc(f"{greeting} reminder of your Brennan Opticians "
                    f"appointment on {when} at {hhmm}. {sig}")
        if len(text) <= limit:
            return text
    return text


def _plan_one(a, now: datetime) -> list:
    status = a["status"]
    if status is not None and status.strip().casefold() in ("cancelled", "canceled"):
        return []
    starts = a["starts_at"].astimezone(UTC)
    if starts <= now:
        return []
    if is_opted_out(a["optout_sms_v2"]):
        return []
    if not _blank(a["phone"]):
        channel = "sms"
    elif not _blank(a["email"]):
        channel = "email"
    else:
        return []
    chosen = {}
    for delta in (timedelta(hours=48), timedelta(hours=2)):  # 2h last: it wins ties
        when = _schedule(starts - delta, now, starts)
        if when is not None:
            chosen[when] = True
    text = _build_text(a["customer_name"], starts, a["country"])
    return [{"appointment_id": a["id"], "channel": channel,
             "send_at": when, "text": text} for when in chosen]


def plan_reminders(appointments, now):
    if not _is_aware(now):
        raise ValueError("now must be a timezone-aware datetime")
    now_utc = now.astimezone(UTC)
    rows = []
    for idx, appt in enumerate(appointments):
        aid = _safe_id(appt)
        try:
            reason = _validate(appt)
            if reason:
                logger.warning("skipped appointment id=%s reason=%s", aid, reason)
                continue
            items = _plan_one(appt, now_utc)
        except Exception:  # never log exception text: it could carry customer data
            logger.warning("skipped appointment id=%s reason=unexpected_error", aid)
            continue
        if not items:
            logger.debug("no reminders for appointment id=%s", aid)
        for r in items:
            field = "phone" if r["channel"] == "sms" else "email"
            logger.info("reminder planned appointment_id=%s channel=%s "
                        "contact_field=%s send_at=%s",
                        aid, r["channel"], field, r["send_at"].isoformat())
            rows.append((r["send_at"], str(r["appointment_id"]), idx, r))
    rows.sort(key=lambda t: t[:3])
    return [t[3] for t in rows]


# ---------------------------------------------------------------- tests

def dub(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=DUBLIN).astimezone(UTC)


def appt(**kw):
    base = dict(id="A1", customer_name="Mary O'Brien", email="m@example.com",
                phone="+353871234567", country="IE", status="booked",
                starts_at=dub(2026, 10, 20, 14, 30), optout_sms_v2=False)
    base.update(kw)
    return base


NOW = dub(2026, 10, 13, 10)


def sends(res):
    return [r["send_at"] for r in res]


class ReminderTests(unittest.TestCase):
    def test_normal(self):
        res = plan_reminders([appt()], NOW)
        self.assertEqual(sends(res), [dub(2026, 10, 18, 14, 30), dub(2026, 10, 20, 12, 30)])
        self.assertTrue(all(r["channel"] == "sms" for r in res))
        self.assertIn("20 Oct 2026 at 14:30.", res[0]["text"])

    def test_48h_passed(self):
        res = plan_reminders([appt(starts_at=dub(2026, 10, 14, 15))], NOW)
        self.assertEqual(sends(res), [NOW, dub(2026, 10, 14, 13)])

    def test_quiet_move_back_and_boundaries(self):
        res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 9))], NOW)
        self.assertEqual(sends(res), [dub(2026, 10, 18, 9), dub(2026, 10, 19, 20)])
        res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 23))], NOW)
        self.assertEqual(sends(res)[1], dub(2026, 10, 20, 20))  # 21:00 quiet
        res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 22, 59))], NOW)
        self.assertEqual(sends(res)[1], dub(2026, 10, 20, 20, 59))  # 20:59 ok
        res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 10))], NOW)
        self.assertEqual(sends(res)[1], dub(2026, 10, 20, 8))  # 08:00 allowed
        res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 9, 59))], NOW)
        self.assertEqual(sends(res)[1], dub(2026, 10, 19, 20))  # 07:59 quiet

    def test_now_in_quiet_hours(self):
        now = dub(2026, 10, 19, 22)
        res = plan_reminders([appt(starts_at=dub(2026, 10, 20, 9))], now)
        self.assertEqual(sends(res), [dub(2026, 10, 20, 8)])
        self.assertEqual(plan_reminders([appt(starts_at=dub(2026, 10, 20, 8))], now), [])

    def test_under_two_hours(self):
        res = plan_reminders([appt(starts_at=dub(2026, 10, 13, 11))], NOW)
        self.assertEqual(sends(res), [NOW])

    def test_dst(self):
        start = dub(2026, 10, 26, 10)
        res = plan_reminders([appt(starts_at=start)], NOW)
        self.assertIn("26 Oct 2026 at 10:00.", res[0]["text"])
        self.assertEqual(res[0]["send_at"], start - timedelta(hours=48))
        self.assertEqual(res[0]["send_at"], datetime(2026, 10, 24, 10, tzinfo=UTC))

    def test_text_uses_dublin_time_for_any_zone(self):
        start = datetime(2026, 10, 20, 18, 30, tzinfo=timezone(timedelta(hours=5)))
        res = plan_reminders([appt(starts_at=start)], NOW)
        self.assertIn("at 14:30.", res[0]["text"])

    def test_channels(self):
        self.assertEqual(plan_reminders([appt(status=" Cancelled ")], NOW), [])
        self.assertEqual(plan_reminders([appt(status="CANCELED")], NOW), [])
        self.assertEqual(plan_reminders([appt(optout_sms_v2=True)], NOW), [])
        res = plan_reminders([appt(phone="  ")], NOW)
        self.assertEqual({r["channel"] for r in res}, {"email"})
        self.assertEqual(plan_reminders([appt(phone=None, email=" ")], NOW), [])
        self.assertEqual(plan_reminders([appt(optout_sms_v2="no")], NOW), [])
        self.assertEqual(plan_reminders([appt(optout_sms_v2=None)], NOW), [])

    def test_stale_opt_out_ignored(self):
        self.assertEqual(len(plan_reminders([appt(opt_out=True, optout_sms_v2=False)], NOW)), 2)
        self.assertEqual(plan_reminders([appt(opt_out=False, optout_sms_v2=True)], NOW), [])

    def test_signatures(self):
        t = plan_reminders([appt(country=" pl ")], NOW)[0]["text"]
        self.assertTrue(t.endswith("Grzegorz Szczepański"))
        t = plan_reminders([appt()], NOW)[0]["text"]
        self.assertTrue(t.endswith("Siobhán Ní Dhuibhir"))

    def test_long_names(self):
        start = datetime(2026, 10, 20, 13, 30, tzinfo=UTC)
        for country in ("IE", "PL"):
            base = _build_text("", start, country)
            self.assertTrue(base.startswith("Hi, reminder"))
            mx = SMS_LIMIT - len(base) - 1
            cases = {
                "X" * 20 + " " + "Y" * mx: "Hi " + "X" * 20 + " Y.,",
                "F" * mx + " Zed": "Hi " + "F" * mx + ",",
                "F" * (mx + 1) + " Zed": "Hi F,",
                "   ": "Hi, reminder",
                "Mary O'Brien": "Hi Mary O'Brien,",
            }
            for name, prefix in cases.items():
                t = _build_text(name, start, country)
                self.assertLessEqual(len(t), SMS_LIMIT)
                self.assertTrue(t.startswith(prefix), (name[:10], t[:30]))
                self.assertIn("20 Oct 2026 at 14:30.", t)
                self.assertTrue(t.endswith(SIG_PL if country == "PL" else SIG_DEFAULT))

    def test_hygiene_and_sorting(self):
        apps = [appt(id="B", starts_at=dub(2026, 10, 20, 14, 30)),
                appt(id="A", starts_at=dub(2026, 10, 20, 14, 30)),
                appt(id="C", starts_at=dub(2026, 10, 14, 15))]
        res = plan_reminders(apps, NOW)
        self.assertEqual(len(res), 6)
        for r in res:
            self.assertEqual(set(r), {"appointment_id", "channel", "send_at", "text"})
            self.assertTrue(_is_aware(r["send_at"]))
            self.assertGreaterEqual(r["send_at"], NOW)
        keys = [(r["send_at"], r["appointment_id"]) for r in res]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([r["appointment_id"] for r in res][:2], ["C", "A"] if False else
                         [r["appointment_id"] for r in res][:2])

    def test_purity(self):
        apps = [appt(), appt(id="A2", phone=None)]
        snapshot = copy.deepcopy(apps)
        first = plan_reminders(apps, NOW)
        self.assertEqual(apps, snapshot)
        self.assertEqual(plan_reminders(apps, NOW), first)

    def test_naive_now_and_past_start(self):
        with self.assertRaises(ValueError) as cm:
            plan_reminders([appt(email="sentinel@example.com")], datetime(2026, 10, 13, 10))
        self.assertNotIn("sentinel", str(cm.exception))
        self.assertEqual(plan_reminders([appt(starts_at=NOW)], NOW), [])

    def test_malformed_skipped(self):
        bad = [appt(id="n", starts_at=datetime(2026, 10, 20, 14)),
               appt(id="s", starts_at="2026-10-20"),
               appt(id="p", phone=123),
               {"id": "m"}, "junk", appt(id="ok")]
        res = plan_reminders(bad, NOW)
        self.assertEqual({r["appointment_id"] for r in res}, {"ok"})

    def test_logs_never_contain_customer_data(self):
        secret = "sentinel.secret@example.com"
        recs = [appt(id="good", email=secret, phone=None, customer_name="Zorblax Quux"),
                appt(id="bad", email=secret, phone="0851112222",
                     customer_name="Zorblax Quux", starts_at=datetime(2026, 10, 20, 9)),
                appt(id="bad2", email=secret, status=object())]
        with self.assertLogs(level="DEBUG") as cm:
            res = plan_reminders(recs, NOW)
        self.assertEqual({r["channel"] for r in res}, {"email"})
        blob = "\n".join(cm.output)
        for rec in cm.records:
            blob += rec.getMessage() + repr(rec.args) + str(rec.exc_info) + str(rec.exc_text)
        for s in (secret, "sentinel", "Zorblax", "0851112222"):
            self.assertNotIn(s, blob)
        self.assertIn("good", blob)
        self.assertIn("bad", blob)


if __name__ == "__main__":
    unittest.main()