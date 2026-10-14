"""Brennan Opticians appointment reminder planner.

Entry point: plan_reminders(appointments, now) -> list of dicts with exactly
appointment_id, channel ("sms"/"email"), send_at, text.

NOTE: I had no file or execution tools in this run. Everything (module plus
unittest suite) is in this one file and has NOT been executed. Run with
`python -m unittest brennan_reminders`. Suggested split: move the test classes
to test_brennan_reminders.py.

DECISIONS (assumptions, flag to PM)
- now must be tz-aware, else ValueError (message carries no data). Inputs are
  never mutated. A bad record is skipped and logged by appointment id only.
- Arithmetic is in UTC (real 48h / 2h durations); Europe/Dublin is used only for
  quiet-hours checks and display. Naive starts_at => malformed, skipped.
- Quiet window is Dublin local [21:00, 08:00): 21:00:00 is quiet, 08:00:00 allowed.
  20:00 / 08:00 are built with ZoneInfo and verified by a UTC round trip.
- Scheduling for candidate c (48h: c = max(starts-48h, now); 2h: starts-2h):
  1 c not quiet and c >= now -> c.
  2 c quiet -> previous 20:00 Dublin if >= now.
  3 otherwise -> now if now is not quiet, else next 08:00 after now.
  4 result must be strictly before starts_at, else that reminder is dropped.
  starts_at <= now -> no reminders. Quiet hours beat "send at now".
- 2h reminder for a 09:00 appointment (07:00 is quiet) goes out 20:00 the evening
  before (13h ahead). Intentional per brief; PM to confirm.
- Dedup: if the 48h send_at >= the 2h send_at, the 48h one is dropped (2h priority).
- Channel (once per appointment): phone non-blank and not opted out -> sms; else
  email non-blank -> email; else skipped. Strings are stripped; blank = missing.
  Only optout_sms_v2 is read (never opt_out). Missing/None => NOT opted out (flag).
  bool accepted; strings true/1/yes => True, false/0/no/"" => False; any other
  value => treated as opted out (conservative; flag).
- Status: stripped, casefolded, "cancelled"/"canceled" => no reminders; else active.
- Signature: country stripped+casefolded == "pl" -> "Grzegorz Szczepański", else
  "Siobhán Ní Dhuibhir"; text always ends exactly with it.
- Text: "Hi {name}, reminder: your Brennan Opticians appointment is on {D Mon YYYY}
  at {HH:MM}. {signature}" (without name: "Reminder: your ..."). English month
  abbreviations hardcoded; date/time in Dublin local time. Same wording for 48h/2h.
- SMS limit: len(text) <= 160 characters. Shortening: full name -> first token ->
  initial ("S.") -> no name. If still too long, reminders for that appointment
  are skipped and logged. Email uses the full name, no limit.
- send_at is returned tz-aware in Europe/Dublin. Sort key: (send_at instant,
  str(appointment_id), kind with 2h before 48h).
- LOGGING: one INFO line per planned reminder with appointment id, channel and
  send_at. The house rule asks for the contact too, but the brief forbids logging
  email addresses (DPC audit) and the architect forbids phone/name, so the contact
  is logged only as "on file". Flag to PM/support: tracing is by appointment id.

OPEN CLIENT QUESTIONS
- Siobhán / Szczepański / Ní are non-GSM characters: real SMS may be UCS-2 with
  70-char segments. Only the 160-character rule is implemented. Should it be
  segment-aware?
- Confirm the evening-before 20:00 send for early-morning appointments.
- Confirm missing opt-out flag means "not opted out".
- Should the 2h reminder say "today"? Currently identical wording.
- Support tracing without contact in logs: acceptable?
"""
import copy
import logging
import unittest
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"
_SMS_MAX = 160


def _safe_id(rec):
    try:
        return str(rec.get("id"))
    except Exception:
        return "?"


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return None


def _parse_optout(v):
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().casefold()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no", ""):
            return False
        return True
    if isinstance(v, int):
        return v != 0
    return True


def _parse_record(rec):
    if not hasattr(rec, "get"):
        raise ValueError("malformed")
    starts = rec.get("starts_at")
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError("malformed")
    status = rec.get("status")
    status = status.strip().casefold() if isinstance(status, str) else ""
    name = _clean(rec.get("customer_name"))
    return {
        "id": rec.get("id"),
        "name": " ".join(name.split()) if name else None,
        "email": _clean(rec.get("email")),
        "phone": _clean(rec.get("phone")),
        "country": (_clean(rec.get("country")) or "").casefold(),
        "cancelled": status in ("cancelled", "canceled"),
        "optout": _parse_optout(rec.get("optout_sms_v2")),
        "starts": starts.astimezone(UTC),
    }


def _choose_channel(p):
    if p["phone"] and not p["optout"]:
        return "sms"
    if p["email"]:
        return "email"
    return None


def _in_quiet(local_dt):
    return local_dt.hour >= 21 or local_dt.hour < 8


def _local_at(d, t):
    dt = datetime.combine(d, t, tzinfo=DUB)
    back = dt.astimezone(UTC).astimezone(DUB)
    if back.replace(tzinfo=None) != datetime.combine(d, t):
        raise ValueError("nonexistent local time")
    return dt


def _prev_2000(dt):
    local = dt.astimezone(DUB)
    d = local.date()
    cand = _local_at(d, time(20, 0))
    while cand > local:
        d -= timedelta(days=1)
        cand = _local_at(d, time(20, 0))
    return cand


def _next_0800(dt):
    local = dt.astimezone(DUB)
    d = local.date()
    cand = _local_at(d, time(8, 0))
    while cand <= local:
        d += timedelta(days=1)
        cand = _local_at(d, time(8, 0))
    return cand


def _schedule(candidate, now, starts_at):
    result = None
    if _in_quiet(candidate.astimezone(DUB)):
        c2 = _prev_2000(candidate)
        if c2 >= now:
            result = c2
    elif candidate >= now:
        result = candidate
    if result is None:
        result = now if not _in_quiet(now.astimezone(DUB)) else _next_0800(now)
    return result if result < starts_at else None


def _format_date(dt):
    return f"{dt.day} {_MONTHS[dt.month - 1]} {dt.year}"


def _format_time(dt):
    return f"{dt.hour:02d}:{dt.minute:02d}"


def _build_text(name, date_s, time_s, sig):
    body = f"your Brennan Opticians appointment is on {date_s} at {time_s}. {sig}"
    return f"Hi {name}, reminder: {body}" if name else f"Reminder: {body}"


def _sms_text_fitting(name, date_s, time_s, sig):
    options = [None]
    if name:
        first = name.split()[0]
        options = [name, first, first[0] + ".", None]
    for n in options:
        text = _build_text(n, date_s, time_s, sig)
        if len(text) <= _SMS_MAX:
            return text
    return None


def _plan_one(rec, now):
    p = _parse_record(rec)
    aid = _safe_id(rec)
    if p["cancelled"] or p["starts"] <= now:
        return []
    channel = _choose_channel(p)
    if channel is None:
        log.info("skip appointment id=%s: no usable contact", aid)
        return []
    local_start = p["starts"].astimezone(DUB)
    sig = _SIG_PL if p["country"] == "pl" else _SIG_DEFAULT
    d, t = _format_date(local_start), _format_time(local_start)
    if channel == "sms":
        text = _sms_text_fitting(p["name"], d, t, sig)
    else:
        text = _build_text(p["name"], d, t, sig)
    if text is None:
        log.warning("skip appointment id=%s: sms text too long", aid)
        return []
    s2 = _schedule(p["starts"] - timedelta(hours=2), now, p["starts"])
    s48 = _schedule(max(p["starts"] - timedelta(hours=48), now), now, p["starts"])
    if s2 is not None and s48 is not None and s48 >= s2:
        s48 = None
    out = []
    for kind, order, when in (("2h", 0, s2), ("48h", 1, s48)):
        if when is None:
            log.info("no %s reminder for appointment id=%s", kind, aid)
            continue
        when = when.astimezone(DUB)
        out.append((when, aid, order, kind, {
            "appointment_id": p["id"], "channel": channel,
            "send_at": when, "text": text}))
    return out


def plan_reminders(appointments, now):
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        raise ValueError("now must be a timezone-aware datetime")
    now_u = now.astimezone(UTC)
    items = []
    for rec in list(appointments):
        try:
            items.extend(_plan_one(rec, now_u))
        except Exception:
            log.warning("skipping malformed record id=%s", _safe_id(rec))
    items.sort(key=lambda x: (x[0].astimezone(UTC), x[1], x[2]))
    for when, aid, _o, kind, rem in items:
        log.info("planned %s reminder id=%s channel=%s contact=on-file send_at=%s",
                 kind, aid, rem["channel"], when.isoformat())
    return [x[4] for x in items]


# ----------------------------------------------------------------- tests
def _utc(*a):
    return datetime(*a, tzinfo=UTC)


def _appt(**kw):
    base = {"id": "a1", "customer_name": "Mary Murphy", "email": "m@x.ie",
            "phone": "0851234567", "country": "IE", "status": "booked",
            "optout_sms_v2": False, "starts_at": _utc(2026, 1, 15, 10, 0)}
    base.update(kw)
    return base


NOW = _utc(2026, 1, 1, 12, 0)
D, T = "5 Jan 2026", "10:00"


class PlanTests(unittest.TestCase):
    def test_now_naive(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2026, 1, 1))

    def test_keys_and_dublin_zone(self):
        out = plan_reminders([_appt()], NOW)
        self.assertEqual(len(out), 2)
        self.assertEqual(set(out[0]), {"appointment_id", "channel", "send_at", "text"})
        self.assertEqual(out[0]["send_at"].tzinfo, DUB)
        self.assertEqual(out[0]["channel"], "sms")
        self.assertIn("15 Jan 2026 at 10:00", out[0]["text"])

    def test_dst_march(self):
        a = _appt(starts_at=_utc(2026, 3, 30, 13, 0))  # 14:00 BST
        out = plan_reminders([a], _utc(2026, 3, 20))
        self.assertEqual(out[0]["send_at"], _utc(2026, 3, 28, 13, 0))
        self.assertEqual(out[0]["send_at"].hour, 13)
        self.assertIn("at 14:00", out[0]["text"])

    def test_dst_october(self):
        a = _appt(starts_at=_utc(2026, 10, 26, 14, 0))  # 14:00 GMT
        out = plan_reminders([a], _utc(2026, 10, 20))
        self.assertEqual(out[0]["send_at"], _utc(2026, 10, 24, 14, 0))
        self.assertEqual(out[0]["send_at"].hour, 15)  # BST local

    def test_transition_helpers(self):
        self.assertEqual(_prev_2000(_utc(2026, 3, 29, 3, 0)).hour, 20)
        self.assertEqual(_next_0800(_utc(2026, 10, 25, 3, 0)).utcoffset(), timedelta(0))

    def test_quiet_edges(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 15, 23, 0))], NOW)
        self.assertEqual(out[-1]["send_at"], _utc(2026, 1, 15, 20, 0))  # 21:00 quiet
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 15, 10, 0))], NOW)
        self.assertEqual(out[-1]["send_at"], _utc(2026, 1, 15, 8, 0))  # 08:00 ok

    def test_early_appointment_goes_evening_before(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 15, 9, 0))], NOW)
        self.assertEqual(out[-1]["send_at"], _utc(2026, 1, 14, 20, 0))

    def test_48h_passed_sends_now(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 15, 16, 0))],
                             _utc(2026, 1, 15, 10, 0))
        self.assertEqual(out[0]["send_at"], _utc(2026, 1, 15, 10, 0))
        self.assertEqual(out[1]["send_at"], _utc(2026, 1, 15, 14, 0))

    def test_now_in_quiet_hours(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 15, 16, 0))],
                             _utc(2026, 1, 15, 6, 0))
        self.assertEqual(out[0]["send_at"], _utc(2026, 1, 15, 8, 0))

    def test_dedup(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 15, 9, 30))],
                             _utc(2026, 1, 15, 8, 30))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["send_at"], _utc(2026, 1, 15, 8, 30))

    def test_past_and_started(self):
        for s in (_utc(2026, 1, 1, 12, 0), _utc(2025, 12, 1)):
            self.assertEqual(plan_reminders([_appt(starts_at=s)], NOW), [])

    def test_never_after_start_or_past(self):
        out = plan_reminders([_appt(starts_at=_utc(2026, 1, 1, 12, 30))], NOW)
        for r in out:
            self.assertGreaterEqual(r["send_at"], NOW)
            self.assertLess(r["send_at"], _utc(2026, 1, 1, 12, 30))

    def test_cancelled_variants(self):
        for s in ("cancelled", " Canceled ", "CANCELLED"):
            self.assertEqual(plan_reminders([_appt(status=s)], NOW), [])
        self.assertEqual(len(plan_reminders([_appt(status=None)], NOW)), 2)

    def test_signature(self):
        for c in ("PL", " pl ", "Pl"):
            t = plan_reminders([_appt(country=c)], NOW)[0]["text"]
            self.assertTrue(t.endswith("Grzegorz Szczepański"))
        for c in ("IE", None, ""):
            t = plan_reminders([_appt(country=c)], NOW)[0]["text"]
            self.assertTrue(t.endswith("Siobhán Ní Dhuibhir"))

    def test_channels(self):
        r = plan_reminders([_appt(optout_sms_v2=True)], NOW)
        self.assertEqual({x["channel"] for x in r}, {"email"})
        self.assertEqual(plan_reminders([_appt(optout_sms_v2=True, email="  ")], NOW), [])
        self.assertEqual(plan_reminders([_appt(phone=" ", email=None)], NOW), [])
        r = plan_reminders([_appt(phone="  ")], NOW)
        self.assertEqual(r[0]["channel"], "email")
        r = plan_reminders([_appt(optout_sms_v2=None)], NOW)
        self.assertEqual(r[0]["channel"], "sms")
        r = plan_reminders([_appt(optout_sms_v2="maybe")], NOW)
        self.assertEqual(r[0]["channel"], "email")
        r = plan_reminders([_appt(optout_sms_v2="No", opt_out=True)], NOW)
        self.assertEqual(r[0]["channel"], "sms")

    def test_sms_boundary_and_shortening(self):
        sig = _SIG_DEFAULT
        k = 160 - len(_build_text("a", D, T, sig)) + 1
        t = _sms_text_fitting("a" * k, D, T, sig)
        self.assertEqual(len(t), 160)
        self.assertIn("a" * k, t)
        t = _sms_text_fitting("a" * (k + 1), D, T, sig)  # 161 -> initial
        self.assertIn("Hi a.,", t)
        t = _sms_text_fitting("a" * k + " bbb", D, T, sig)  # first token
        self.assertIn("Hi " + "a" * k + ",", t)
        self.assertNotIn("bbb", t)
        s = 160 - len(_build_text(None, D, T, ""))
        t = _sms_text_fitting("Mary Murphy", D, T, "S" * s)  # name dropped
        self.assertEqual(len(t), 160)
        self.assertTrue(t.startswith("Reminder:"))
        self.assertIsNone(_sms_text_fitting("Mary", D, T, "S" * (s + 1)))

    def test_email_full_name_no_limit(self):
        r = plan_reminders([_appt(optout_sms_v2=True, customer_name="N" * 300)], NOW)
        self.assertIn("N" * 300, r[0]["text"])

    def test_sorting_and_tiebreak(self):
        a = _appt(id="b")
        b = _appt(id="a")
        out = plan_reminders([a, b], NOW)
        self.assertEqual([r["appointment_id"] for r in out], ["a", "b", "a", "b"])
        sends = [r["send_at"] for r in out]
        self.assertEqual(sends, sorted(sends))

    def test_naive_and_malformed_skipped(self):
        bad = [_appt(id="n", starts_at=datetime(2026, 1, 15, 10)),
               _appt(id="s", starts_at="tomorrow"), "junk", None, {"id": object()}]
        out = plan_reminders(bad + [_appt(id="ok")], NOW)
        self.assertEqual({r["appointment_id"] for r in out}, {"ok"})

    def test_non_mutation(self):
        recs = [_appt(), _appt(id="z", optout_sms_v2=True)]
        snap = copy.deepcopy(recs)
        plan_reminders(recs, NOW)
        self.assertEqual(recs, snap)

    def test_logs_have_no_personal_data(self):
        recs = [_appt(email="secret@x.ie", phone="0851112222", customer_name="Zed Zorro"),
                _appt(id="bad", email="leak@x.ie", starts_at="x"),
                _appt(id="e", optout_sms_v2=True, email="mail@x.ie", customer_name="Zed Zorro")]
        with self.assertLogs(__name__, level="INFO") as cm:
            plan_reminders(recs, NOW)
        blob = "\n".join(cm.output)
        for s in ("secret@x.ie", "leak@x.ie", "mail@x.ie", "0851112222", "Zed", "Zorro", "@"):
            self.assertNotIn(s, blob)
        self.assertEqual(sum("planned" in m for m in cm.output), 4)
        try:
            plan_reminders([], datetime(2026, 1, 1))
        except ValueError as e:
            self.assertNotIn("@", str(e))


if __name__ == "__main__":
    unittest.main()