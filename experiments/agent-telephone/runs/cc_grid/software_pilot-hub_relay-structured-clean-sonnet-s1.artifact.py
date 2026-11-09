"""Brennan Opticians appointment reminders.

Not executed in the authoring environment (no tools available); run with:
    python -I reminders.py

Assumptions awaiting client confirmation (implemented as defaults):
Q1 PL appointments still use Europe/Dublin time. Q2 the SMS limit is 160 code
points, not GSM segments. Q3 English template. Q4 a late T-2h reminder is
omitted. Q5 the forward-to-08:00 fallback applies. Q6 a missing opt-out flag
means opted out (email). Q7 only cancelled/canceled suppress reminders.

Logging note: the house rule asks for the contact in each INFO line, but R9
forbids logging email or phone. R9 is the privacy requirement, so each INFO
line carries the appointment id and channel only, with no contact.
"""
import logging
import unicodedata
from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

__all__ = ["plan_reminders"]

_DUBLIN = ZoneInfo("Europe/Dublin")
_UTC = timezone.utc
_log = logging.getLogger(__name__)
_SMS_LIMIT = 160
_SIG_DEFAULT = "Siobhán Ní Dhuibhir"
_SIG_PL = "Grzegorz Szczepański"


def _get(a, name):
    if isinstance(a, Mapping):
        return a.get(name)
    return getattr(a, name, None)


def _safe_id(a):
    try:
        v = _get(a, "id")
        if isinstance(v, (str, int)) and not isinstance(v, bool):
            return v
    except Exception:
        pass
    return "?"


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _nonblank(v):
    return isinstance(v, str) and v.strip() != ""


def _is_quiet(local):
    return local.hour >= 21 or local.hour < 8


def _next_8(c):
    local = c.astimezone(_DUBLIN)
    t = datetime.combine(local.date(), time(8), _DUBLIN)
    if t < c:
        t = datetime.combine(local.date() + timedelta(days=1), time(8), _DUBLIN)
    return t.astimezone(_UTC)


def _adjust(send, now_u, starts):
    local = send.astimezone(_DUBLIN)
    if _is_quiet(local):
        d = local.date() if local.hour >= 21 else local.date() - timedelta(days=1)
        send = datetime.combine(d, time(20), _DUBLIN).astimezone(_UTC)
        if send < now_u:
            send = _next_8(send)
    if send >= starts:
        return None
    return send


def _name_options(name):
    parts = _nfc(name).split() if isinstance(name, str) else []
    if not parts:
        return [""]
    opts = [" ".join(parts)]
    if len(parts) > 1:
        opts.append(f"{parts[0]} {parts[-1][0]}.")
    opts.append(parts[0])
    opts.append("")
    return opts


def _build_text(name, starts_local, signature, sms):
    d = starts_local.strftime("%d/%m/%Y")
    t = starts_local.strftime("%H:%M")

    def render(n):
        greet = f"Hi {n}," if n else "Hi,"
        return _nfc(f"{greet} reminder of your Brennan Opticians "
                    f"appointment on {d} at {t}. {signature}")

    opts = _name_options(name)
    if not sms:
        return render(opts[0])
    text = ""
    for n in opts:
        text = render(n)
        if len(text) <= _SMS_LIMIT:
            return text
    return text


def _plan_one(a, now_u):
    aid = _get(a, "id")
    if isinstance(aid, bool) or not isinstance(aid, (str, int)) or aid == "":
        _log.warning("appointment skipped id=? reason=invalid_id")
        return []
    if isinstance(aid, str) and not aid.strip():
        _log.warning("appointment skipped id=? reason=invalid_id")
        return []
    starts_at = _get(a, "starts_at")
    if (not isinstance(starts_at, datetime) or starts_at.tzinfo is None
            or starts_at.utcoffset() is None):
        _log.warning("appointment skipped id=%s reason=invalid_starts_at", aid)
        return []
    status = _get(a, "status")
    if isinstance(status, str) and status.strip().casefold() in (
            "cancelled", "canceled"):
        _log.info("appointment skipped id=%s reason=cancelled", aid)
        return []
    starts = starts_at.astimezone(_UTC)
    if starts <= now_u:
        _log.info("appointment skipped id=%s reason=already_started", aid)
        return []

    phone = _get(a, "phone")
    if _nonblank(phone) and _get(a, "optout_sms_v2") is False:
        channel = "sms"
    else:
        channel = "email"
        if not _nonblank(_get(a, "email")):
            _log.warning("appointment skipped id=%s reason=no_email", aid)
            return []

    country = _get(a, "country")
    sig = _SIG_PL if isinstance(country, str) and country.strip().upper() == "PL" \
        else _SIG_DEFAULT
    text = _build_text(_get(a, "customer_name"), starts.astimezone(_DUBLIN),
                       sig, channel == "sms")

    # T-2h built first (higher priority, R11).
    r2 = None
    t2 = starts - timedelta(hours=2)
    if t2 >= now_u:
        r2 = _adjust(t2, now_u, starts)
    t48 = starts - timedelta(hours=48)
    r48 = _adjust(max(t48, now_u), now_u, starts)
    if r2 is not None and r48 == r2:
        r48 = None

    out = []
    for send in (r48, r2):
        if send is None:
            continue
        out.append({"appointment_id": aid, "channel": channel,
                    "send_at": send, "text": text})
        _log.info("reminder planned id=%s channel=%s send_at=%s",
                  aid, channel, send.isoformat())
    return out


def plan_reminders(appointments, now):
    if not isinstance(appointments, list):
        raise TypeError("appointments must be a list")
    if not isinstance(now, datetime):
        raise TypeError("now must be a datetime")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_u = now.astimezone(_UTC)
    out = []
    for a in appointments:
        try:
            out.extend(_plan_one(a, now_u))
        except Exception:
            _log.warning("appointment skipped id=%s reason=unexpected_error",
                         _safe_id(a))
    out.sort(key=lambda r: r["send_at"])
    return out


# ----------------------------------------------------------------- tests
import copy
import random
import unittest


def _appt(**kw):
    base = {"id": "a1", "customer_name": "Anna Kowalska",
            "email": "anna@example.com", "phone": "", "country": "IE",
            "status": "booked", "optout_sms_v2": True,
            "starts_at": datetime(2027, 1, 20, 12, 0, tzinfo=_UTC)}
    base.update(kw)
    return base


def _u(*a):
    return datetime(*a, tzinfo=_UTC)


class _TestPlan(unittest.TestCase):
    def test_empty_and_keys(self):
        now = _u(2027, 1, 1)
        self.assertEqual(plan_reminders([], now), [])
        out = plan_reminders([_appt()], now)
        self.assertEqual(len(out), 2)
        self.assertEqual(set(out[0]),
                         {"appointment_id", "channel", "send_at", "text"})
        self.assertEqual(out[0]["send_at"], _u(2027, 1, 18, 12))
        self.assertEqual(out[1]["send_at"], _u(2027, 1, 20, 10))
        self.assertEqual(__all__, ["plan_reminders"])

    def test_input_errors(self):
        with self.assertRaises(ValueError):
            plan_reminders([], datetime(2027, 1, 1))
        with self.assertRaises(TypeError):
            plan_reminders(({},), _u(2027, 1, 1))

    def test_no_mutation(self):
        apps = [_appt()]
        before = copy.deepcopy(apps)
        plan_reminders(apps, _u(2027, 1, 1))
        self.assertEqual(apps, before)

    def test_channel_rules(self):
        now = _u(2027, 1, 1)
        for flag, exp in ((False, "sms"), (True, "email"), (None, "email"),
                          ("false", "email")):
            out = plan_reminders([_appt(phone="+353", optout_sms_v2=flag)], now)
            self.assertEqual(out[0]["channel"], exp)
        a = _appt(phone="+353")
        del a["optout_sms_v2"]
        self.assertEqual(plan_reminders([a], now)[0]["channel"], "email")
        self.assertEqual(plan_reminders([_appt(email="  ")], now), [])

    def test_cancelled(self):
        for s in (" Cancelled ", "CANCELED"):
            self.assertEqual(plan_reminders([_appt(status=s)], _u(2027, 1, 1)), [])

    def test_late_cases(self):
        starts = _u(2027, 1, 20, 12)
        self.assertEqual(plan_reminders([_appt()], starts), [])
        now = _u(2027, 1, 20, 11)  # T-2h passed: only immediate first
        out = plan_reminders([_appt()], now)
        self.assertEqual([r["send_at"] for r in out], [now])

    def test_quiet_hours_immediate(self):
        cases = [((20, 59), (15, 20, 59)), ((21, 0), (16, 8, 0)),
                 ((7, 59), (15, 8, 0)), ((8, 0), (15, 8, 0)),
                 ((0, 0), (15, 8, 0))]
        for (h, m), (d, eh, em) in cases:
            now = _u(2027, 1, 15, h, m)
            out = plan_reminders([_appt(starts_at=now + timedelta(hours=47))], now)
            self.assertEqual(out[0]["send_at"], _u(2027, 1, d, eh, em), (h, m))

    def test_dedupe_keeps_2h(self):
        now = _u(2027, 1, 10, 22)
        out = plan_reminders([_appt(starts_at=_u(2027, 1, 11, 9))], now)
        self.assertEqual([r["send_at"] for r in out], [_u(2027, 1, 11, 8)])

    def test_dst_autumn(self):
        now = _u(2026, 10, 20, 12)
        out = plan_reminders([_appt(starts_at=_u(2026, 10, 26, 10))], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_u(2026, 10, 24, 10), _u(2026, 10, 26, 8)])
        out = plan_reminders([_appt(starts_at=_u(2026, 10, 27, 6, 30))], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_u(2026, 10, 24, 19), _u(2026, 10, 26, 20)])

    def test_dst_spring(self):
        now = _u(2026, 3, 20)
        out = plan_reminders([_appt(starts_at=_u(2026, 3, 30, 10))], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_u(2026, 3, 28, 10), _u(2026, 3, 30, 8)])
        self.assertIn("30/03/2026 at 11:00", out[0]["text"])
        out = plan_reminders([_appt(starts_at=_u(2026, 3, 30, 6, 30))], now)
        self.assertEqual([r["send_at"] for r in out],
                         [_u(2026, 3, 27, 20), _u(2026, 3, 29, 19)])

    def test_text_and_signature(self):
        out = plan_reminders([_appt()], _u(2027, 1, 1))
        self.assertEqual(out[0]["text"],
                         "Hi Anna Kowalska, reminder of your Brennan Opticians "
                         "appointment on 20/01/2027 at 12:00. Siobhán Ní Dhuibhir")
        out = plan_reminders([_appt(country=" pl ")], _u(2027, 1, 1))
        self.assertTrue(out[0]["text"].endswith("Grzegorz Szczepański"))

    def test_sms_length_and_shortening(self):
        now = _u(2027, 1, 1)
        for sig in (_SIG_DEFAULT, _SIG_PL):
            t = _build_text("", datetime(2027, 12, 31, 23, 59, tzinfo=_DUBLIN),
                            sig, True)
            self.assertLessEqual(len(t), 160)
            self.assertTrue(t.startswith("Hi, reminder"))
        name = "A" * 30 + " " + "B" * 60
        out = plan_reminders([_appt(phone="1", optout_sms_v2=False,
                                    customer_name=name)], now)
        t = out[0]["text"]
        self.assertLessEqual(len(t), 160)
        self.assertIn("A" * 30 + " B.", t)
        out = plan_reminders([_appt(phone="1", optout_sms_v2=False,
                                    customer_name="A" * 100 + " " + "B" * 100)], now)
        self.assertTrue(out[0]["text"].startswith("Hi, reminder"))
        out = plan_reminders([_appt(customer_name="A" * 100 + " " + "B" * 100)], now)
        self.assertIn("A" * 100 + " " + "B" * 100, out[0]["text"])

    def test_property(self):
        rng = random.Random(1)
        zones = [_UTC, ZoneInfo("America/New_York"), _DUBLIN]
        for _ in range(500):
            now = _u(2026, 1, 1) + timedelta(minutes=rng.randrange(60 * 24 * 400))
            starts = (now + timedelta(minutes=rng.randrange(-300, 60 * 24 * 5))
                      ).astimezone(rng.choice(zones))
            out = plan_reminders([_appt(starts_at=starts)], now)
            self.assertLessEqual(len(out), 2)
            for r in out:
                self.assertTrue(now <= r["send_at"] < starts)
                self.assertFalse(_is_quiet(r["send_at"].astimezone(_DUBLIN)))

    def test_malformed_and_privacy(self):
        class Boom(dict):
            def get(self, *a, **k):
                raise RuntimeError("secret@example.com +353871234567 Zed Secret")

        records = []

        class H(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage() + str(record.args)
                               + str(record.exc_info))

        h = H()
        root = logging.getLogger()
        old = root.level
        root.addHandler(h)
        root.setLevel(logging.DEBUG)
        try:
            sec = dict(email="secret@example.com", phone="+353871234567",
                       customer_name="Zed Secret")
            apps = [_appt(id="ok", **sec),
                    _appt(id="c", status="cancelled", **sec),
                    _appt(id="ne", **{**sec, "email": ""}),
                    _appt(id="bad", starts_at=datetime(2027, 1, 20), **sec),
                    {"customer_name": "Zed Secret", "email": "secret@example.com"},
                    Boom(), 5]
            out = plan_reminders(apps, _u(2027, 1, 1))
            self.assertEqual({r["appointment_id"] for r in out}, {"ok"})
            for bad in ((ValueError, lambda: plan_reminders([], datetime(2027, 1, 1))),):
                with self.assertRaises(bad[0]) as cm:
                    bad[1]()
                self.assertNotIn("secret", str(cm.exception))
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        blob = "\n".join(records)
        self.assertTrue(records)
        for s in ("secret@example.com", "+353871234567", "Zed", "Brennan"):
            self.assertNotIn(s, blob)

    def test_source_has_no_legacy_field(self):
        with open(__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("opt" + "_out", src)


if __name__ == "__main__":
    unittest.main()