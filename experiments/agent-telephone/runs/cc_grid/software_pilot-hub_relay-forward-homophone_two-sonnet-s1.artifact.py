"""Brennan Opticians appointment reminders: plan_reminders(appointments, now).

Tests are at the bottom of this module (run: pytest <this file>).

Assumptions (PM inferences, to relay to the client)
- Second reminder is 2h before start (SECOND_OFFSET); the brief's wording was garbled.
- Offsets are computed on instants (UTC), not Dublin wall-clock, so DST changes do not shift them.
- A passed 48h point sends reminder 1 at `now`. A passed 2h point is dropped.
- Quiet hours 21:00-08:00 Europe/Dublin (21:00 inside, 08:00 outside). Shift back to the
  previous 20:00; if that is < now, shift forward to the next 08:00; if that is >= starts_at, drop.
- Same-send_at reminders within one appointment are deduped, keeping the 2h one.
- Only optout_sms_v2 is read (legacy opt_out ignored); missing/None means not opted out.
  True, or the strings "true"/"1"/"yes", count as opted out.
- Email channel with a blank email: skipped, logged with the appointment id only.
- Date format is "14 Oct 2026" (no zero padding, English month abbreviations); time is HH:MM, Dublin.
- SMS limit is 160 characters (len of the string). Only the name shrinks: full, first name +
  last initial, first name, first initial, no name. Emails are not shortened.
- Logging: one INFO line per planned reminder with id, channel and contact. Email addresses
  are never logged (the line says "email-on-file"); phones are masked to their last 3 digits.

Open client questions
1. Is the second reminder really 2 hours before the appointment?
2. When the previous 20:00 has already passed, is forward-shifting to 08:00 right (or send at now / drop)?
3. Should a missing optout_sms_v2 mean "not opted out" (current default)?
4. Date format and wording of the text (e.g. "14 Oct 2026", English only, also for PL)?
5. Is 160 characters correct given that "ó", "í", "á", "ń" etc. in signatures are outside the
   GSM-7 alphabet, so the real SMS limit may be 70 characters per segment (UCS-2)?
6. If the 2h reminder has already passed when we run, should it be sent at now instead of dropped?
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DUB = ZoneInfo("Europe/Dublin")
UTC = timezone.utc
FIRST_OFFSET = timedelta(hours=48)
SECOND_OFFSET = timedelta(hours=2)
QUIET_START_HOUR = 21
QUIET_END_HOUR = 8
SEND_BACK_HOUR = 20
SMS_MAX = 160
SIGNATURE = "Siobhán Ní Dhuibhir"
SIGNATURE_PL = "Grzegorz Szczepański"
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _at(d: date, hour: int) -> datetime:
    return datetime.combine(d, time(hour), tzinfo=DUB).astimezone(UTC)


def _apply_quiet(t, now, starts):
    loc = t.astimezone(DUB)
    late = loc.hour >= QUIET_START_HOUR
    if not (late or loc.hour < QUIET_END_HOUR):
        return t
    one = timedelta(days=1)
    back = _at(loc.date() if late else loc.date() - one, SEND_BACK_HOUR)
    if back >= now:
        return back
    fwd = _at(loc.date() + one if late else loc.date(), QUIET_END_HOUR)
    return fwd if fwd < starts else None


def _opted_out(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return v is True


def _blank(v) -> bool:
    return v is None or not str(v).strip()


def _text(name_parts, starts, sig, limit):
    loc = starts.astimezone(DUB)
    tail = (f", reminder: your Brennan Opticians appointment is on "
            f"{loc.day} {_MONTHS[loc.month - 1]} {loc.year} at {loc:%H:%M}. {sig}")
    options = [" ".join(name_parts)]
    if len(name_parts) > 1:
        options.append(f"{name_parts[0]} {name_parts[-1][0]}.")
    if name_parts:
        options += [name_parts[0], name_parts[0][0]]
    options.append("")
    for n in options:
        s = f"Hi {n}{tail}" if n else f"Hi{tail}"
        if limit is None or len(s) <= limit:
            return s
    return s


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    now_u = now.astimezone(UTC)
    out = []
    for a in appointments:
        aid = a.get("id")
        st = a.get("starts_at")
        if not isinstance(st, datetime) or st.tzinfo is None or st.utcoffset() is None:
            raise ValueError(f"appointment {aid}: starts_at must be a timezone-aware datetime")
        if str(a.get("status") or "").strip().lower() == "cancelled":
            continue
        starts = st.astimezone(UTC)
        if starts <= now_u:
            continue

        cands = []
        t1 = starts - FIRST_OFFSET
        cands.append((1, max(t1, now_u)))
        t2 = starts - SECOND_OFFSET
        if t2 >= now_u:
            cands.append((2, t2))
        chosen = {}
        for kind, t in cands:
            t = _apply_quiet(t, now_u, starts)
            if t is not None:
                chosen[t] = kind  # later (2h) overwrites earlier on collision
        if not chosen:
            continue

        phone = a.get("phone")
        if not _blank(phone) and not _opted_out(a.get("optout_sms_v2")):
            channel = "sms"
            digits = "".join(c for c in str(phone) if c.isdigit())
            contact = "phone ***" + digits[-3:]
        elif not _blank(a.get("email")):
            channel, contact = "email", "email-on-file"
        else:
            logger.warning("Skipping appointment %s: no usable contact", aid)
            continue

        sig = SIGNATURE_PL if str(a.get("country") or "").strip().upper() == "PL" else SIGNATURE
        text = _text(str(a.get("customer_name") or "").split(), starts, sig,
                     SMS_MAX if channel == "sms" else None)
        for t in sorted(chosen):
            logger.info("Planned reminder appointment_id=%s which=%s channel=%s contact=%s send_at=%s",
                        aid, chosen[t], channel, contact, t.isoformat())
            out.append({"appointment_id": aid, "channel": channel,
                        "send_at": t.astimezone(DUB), "text": text})
    out.sort(key=lambda r: r["send_at"])
    return out


# ----------------------------------------------------------------- tests
import copy
import random

import pytest


def D(d, h=0, m=0, mo=10, y=2026):
    return datetime(y, mo, d, h, m, tzinfo=DUB)


def mk(**kw):
    base = dict(id="a1", customer_name="Aoife Murphy", email="aoife@example.com",
                phone="+353871234567", country="IE", status="booked",
                starts_at=D(20, 15), optout_sms_v2=None)
    base.update(kw)
    return base


def test_normal():
    r = plan_reminders([mk()], D(10, 9))
    assert [x["send_at"] for x in r] == [D(18, 15), D(20, 13)]
    assert all(x["channel"] == "sms" and x["appointment_id"] == "a1" for x in r)
    assert r[0]["text"] == ("Hi Aoife Murphy, reminder: your Brennan Opticians appointment "
                            "is on 20 Oct 2026 at 15:00. Siobhán Ní Dhuibhir")
    assert set(r[0]) == {"appointment_id", "channel", "send_at", "text"}
    assert r[0]["send_at"].utcoffset() is not None


def test_immediate_first():
    r = plan_reminders([mk()], D(19, 10))
    assert [x["send_at"] for x in r] == [D(19, 10), D(20, 13)]


def test_back_shift():
    r = plan_reminders([mk(starts_at=D(20, 6))], D(1, 9))
    assert [x["send_at"] for x in r] == [D(17, 20), D(19, 20)]


@pytest.mark.parametrize("h,m,exp", [
    (20, 59, D(15, 20, 59)), (21, 0, D(15, 20, 0)),
    (7, 59, D(14, 20, 0)), (8, 0, D(15, 8, 0))])
def test_boundaries(h, m, exp):
    target = D(15, h, m)
    starts = (target.astimezone(UTC) + FIRST_OFFSET)
    r = plan_reminders([mk(starts_at=starts)], D(1, 9))
    assert r[0]["send_at"] == exp


def test_now_in_quiet_hours():
    r = plan_reminders([mk()], D(19, 22))
    assert r[0]["send_at"] == D(20, 8)


def test_forward_shift_drop():
    assert plan_reminders([mk(starts_at=D(20, 7))], D(19, 22)) == []


def test_dedupe_collision():
    r = plan_reminders([mk(starts_at=D(20, 10))], D(19, 22))
    assert len(r) == 1 and r[0]["send_at"] == D(20, 8)


def test_property_never_past_and_sorted():
    rnd = random.Random(7)
    base = D(1, 0).astimezone(UTC)
    for _ in range(300):
        now = base + timedelta(minutes=rnd.randrange(0, 60 * 24 * 10))
        apps = [mk(id=str(i), starts_at=base + timedelta(minutes=rnd.randrange(0, 60 * 24 * 12)))
                for i in range(4)]
        r = plan_reminders(apps, now)
        starts = {a["id"]: a["starts_at"] for a in apps}
        assert all(x["send_at"] >= now and x["send_at"] < starts[x["appointment_id"]] for x in r)
        assert [x["send_at"] for x in r] == sorted(x["send_at"] for x in r)


def test_cancelled_and_past():
    assert plan_reminders([mk(status=" Cancelled ")], D(1)) == []
    assert plan_reminders([mk()], D(20, 15)) == []


def test_channel_matrix():
    now = D(10, 9)
    ch = lambda **kw: [x["channel"] for x in plan_reminders([mk(**kw)], now)][:1]
    assert ch() == ["sms"]
    assert ch(optout_sms_v2=True) == ["email"]
    assert ch(optout_sms_v2=False) == ["sms"]
    assert ch(phone="  ") == ["email"]
    assert ch(phone=None) == ["email"]
    assert ch(opt_out=True) == ["sms"]
    assert ch(phone="", email="  ") == []
    assert ch(optout_sms_v2=True, email=None) == []


def test_signature():
    r = plan_reminders([mk(country=" pl ")], D(10, 9))
    assert all(x["text"].endswith("Grzegorz Szczepański") for x in r)
    assert plan_reminders([mk()], D(10, 9))[0]["text"].endswith("Siobhán Ní Dhuibhir")


def test_sms_length_and_name_shrinking():
    now = D(10, 9)
    one = lambda name, **kw: plan_reminders([mk(customer_name=name, **kw)], now)[0]["text"]
    t = one("Zed " + "Q" * 200)
    assert len(t) <= 160 and t.startswith("Hi Zed Q., ")
    t = one("X" * 200 + " Y")
    assert len(t) <= 160 and t.startswith("Hi X, ")
    t = one("")
    assert t.startswith("Hi, reminder") and "20 Oct 2026 at 15:00" in t
    t = one("Aoife " + "M" * 200)
    assert len(t) <= 160 and "20 Oct 2026 at 15:00. Siobhán Ní Dhuibhir" in t
    long = "Aoife " + "M" * 200
    e = one(long, optout_sms_v2=True)
    assert long in e and len(e) > 160


def test_dst_2026_10_25():
    starts = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)  # 12:00 Dublin (GMT)
    r = plan_reminders([mk(starts_at=starts)], D(1, 9))
    assert [x["send_at"] for x in r] == [datetime(2026, 10, 23, 12, tzinfo=UTC),
                                         datetime(2026, 10, 25, 10, tzinfo=UTC)]
    assert "at 12:00." in r[0]["text"]


def test_ordering_stable():
    r = plan_reminders([mk(id="b1"), mk(id="b2")], D(10, 9))
    assert [x["appointment_id"] for x in r] == ["b1", "b2", "b1", "b2"]


def test_purity():
    apps = [mk(), mk(id="x", optout_sms_v2=True)]
    snap = copy.deepcopy(apps)
    plan_reminders(apps, D(10, 9))
    assert apps == snap


def test_validation():
    with pytest.raises(ValueError):
        plan_reminders([mk()], datetime(2026, 10, 10, 9))
    with pytest.raises(ValueError) as e:
        plan_reminders([mk(id="zz9", starts_at=datetime(2026, 10, 20, 15))], D(10, 9))
    msg = str(e.value)
    assert "zz9" in msg and "Aoife" not in msg and "example.com" not in msg and "353" not in msg


def test_logging_no_email(caplog):
    caplog.set_level(logging.INFO)
    r = plan_reminders([mk(optout_sms_v2=True, email="secret@example.com"),
                        mk(id="sms1"), mk(id="none", phone="", email="")], D(10, 9))
    infos = [x for x in caplog.records if x.levelno == logging.INFO]
    assert len(infos) == len(r) == 4
    assert "secret@example.com" not in caplog.text and "@" not in caplog.text
    assert "a1" in caplog.text and "none" in caplog.text
    assert "Aoife" not in caplog.text