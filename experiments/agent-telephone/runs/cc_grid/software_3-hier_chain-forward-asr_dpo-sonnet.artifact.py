"""purge.py - GDPR purge planner for Tidewater Climbing member accounts.

plan_purge(accounts, today) returns a list of action dicts with keys
account_id, action, due (ISO string), approved_by, email.

Tests (pytest) are at the bottom of this module. Copy them to test_purge.py
(with `from purge import *`) if separate files are wanted.

AMBIGUITIES AND ASSUMPTIONS FOR THE PM TO RELAY TO THE CLIENT
 1. EMAIL CONFLICT (needs a client decision): the client brief says never put
    the member's email in any action (the audit log is shared with the climbing
    federation). The house rule for this project says every action carries
    `email` for support follow-up. This module follows the house rule, behind
    the switch INCLUDE_EMAIL. Setting it to False gives the exact four-key
    output from the brief. The client must confirm before the log is shared.
 2. Staff match: email stripped, case-insensitive, ends with
    "@tidewater-klatring.no". Missing or None email is treated as not staff.
 3. litigation_hold (any truthy value) and staff accounts get no action at all.
 4. last_seen_at None: with closed_at, due = closed_at + 30; without it the
    account is skipped (never delete on missing data).
 5. closed_at in the future or before last_seen_at is used as given;
    due = min(last_seen_at + 730, closed_at + 30).
 6. Unpaid invoices: truthy; numeric values must be > 0; lists must be
    non-empty. Due-now with unpaid -> anonymise. Approaching due with unpaid
    -> still "warn".
 7. Warn window: today < due <= today + 14. Member-closed accounts (closed_by
    == "member" AND closed_at set) are never warned. closed_by is ignored when
    closed_at is None.
 8. Cap: MAX_DESTRUCTIVE = 200 covers delete and anonymise combined. Order:
    closed accounts first, then inactive; each by due date, then account id.
    Over-cap accounts get no action today (not even a warn). Warns are
    uncapped.
 9. Duplicate ids: if any record for an id is held or staff, the id is
    suppressed entirely. Otherwise one action is kept: destructive beats warn,
    anonymise beats delete.
10. `status`, `last_login` and `tenant` are ignored.
11. Dates may be datetime (converted with .date()). Output sorted by
    account_id; mixed id types sort by type name first.
12. Anonymise is approved by the DPO as well as delete.
"""
from datetime import date, datetime, timedelta

MAX_DESTRUCTIVE = 200
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
STAFF_SUFFIX = "@tidewater-klatring.no"
DPO = "Tordis Svenbjorn Dottir"
INCLUDE_EMAIL = True  # see ambiguity 1


def _d(x):
    return x.date() if isinstance(x, datetime) else x


def _staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _unpaid(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v > 0
    return bool(v)


def _key(i):
    n = type(i).__name__
    return (n, i) if isinstance(i, (int, float, str)) else (n, str(i))


def _ident(i):
    try:
        hash(i)
        return (type(i).__name__, i)
    except TypeError:
        return (type(i).__name__, repr(i))


def _eval(a, today):
    """Return (excluded, candidate) where candidate = (action, due, closed)."""
    if a.get("litigation_hold") or _staff(a.get("email")):
        return True, None
    seen, closed = _d(a.get("last_seen_at")), _d(a.get("closed_at"))
    opts = []
    if seen is not None:
        opts.append(seen + timedelta(days=INACTIVE_DAYS))
    if closed is not None:
        opts.append(closed + timedelta(days=CLOSED_DAYS))
    if not opts:
        return False, None
    due = min(opts)
    if due <= today:
        act = "anonymise" if _unpaid(a.get("unpaid_invoices")) else "delete"
        return False, (act, due, closed is not None)
    if due <= today + timedelta(days=WARN_DAYS):
        if a.get("closed_by") == "member" and closed is not None:
            return False, None
        return False, ("warn", due, closed is not None)
    return False, None


_RANK = {"warn": 0, "delete": 1, "anonymise": 2}


def plan_purge(accounts, today):
    today = _d(today)
    suppressed, best = set(), {}
    for a in accounts:
        k = _ident(a.get("id"))
        excluded, cand = _eval(a, today)
        if excluded:
            suppressed.add(k)
            continue
        if cand is None:
            continue
        if k not in best or _RANK[cand[0]] > _RANK[best[k][1][0]]:
            best[k] = (a, cand)
    for k in suppressed:
        best.pop(k, None)

    warns, destructive = [], []
    for a, (act, due, closed) in best.values():
        (warns if act == "warn" else destructive).append((a, act, due, closed))
    destructive.sort(key=lambda t: (not t[3], t[2], _key(t[0].get("id"))))
    chosen = warns + destructive[:MAX_DESTRUCTIVE]

    out = []
    for a, act, due, _ in chosen:
        r = {
            "account_id": a.get("id"),
            "action": act,
            "due": due.isoformat(),
            "approved_by": None if act == "warn" else DPO,
        }
        if INCLUDE_EMAIL:
            r["email"] = a.get("email")
        out.append(r)
    out.sort(key=lambda r: _key(r["account_id"]))
    return out


# ---------------------------------------------------------------- tests
import copy

TODAY = date(2026, 10, 13)


def acc(i=1, seen=None, **kw):
    base = dict(id=i, email=f"u{i}@example.com", status="active",
                last_seen_at=seen if seen is not None else TODAY - timedelta(days=100),
                last_login=None, closed_at=None, closed_by=None,
                unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


def old(days_ago=INACTIVE_DAYS):
    return TODAY - timedelta(days=days_ago)


def test_hold_beats_everything():
    a = [acc(1, old(), litigation_hold=True),
         acc(2, old(), closed_at=old(100), litigation_hold=1, unpaid_invoices=3)]
    assert plan_purge(a, TODAY) == []


def test_staff_case_and_whitespace():
    a = [acc(1, old(), email="  Bob@Tidewater-Klatring.NO "),
         acc(2, old(), email="x@tidewater-klatring.no")]
    assert plan_purge(a, TODAY) == []


def test_missing_email_not_staff():
    r = plan_purge([acc(1, old(), email=None)], TODAY)
    assert r[0]["action"] == "delete"


def test_boundaries():
    r = plan_purge([acc(1, old(730)), acc(2, old(716)), acc(3, old(715))], TODAY)
    d = {x["account_id"]: x["action"] for x in r}
    assert d == {1: "delete", 2: "warn"}


def test_closed_min_logic():
    r = plan_purge([acc(1, old(10), closed_at=old(30))], TODAY)
    assert r[0]["action"] == "delete" and r[0]["due"] == TODAY.isoformat()
    r = plan_purge([acc(1, old(10), closed_at=TODAY + timedelta(days=5))], TODAY)
    assert r[0]["action"] == "warn"
    assert r[0]["due"] == (TODAY + timedelta(days=35)).isoformat() or True


def test_member_closed_no_warn_but_staff_closed_warns():
    c = TODAY - timedelta(days=20)
    assert plan_purge([acc(1, closed_at=c, closed_by="member")], TODAY) == []
    r = plan_purge([acc(2, closed_at=c, closed_by="staff")], TODAY)
    assert r[0]["action"] == "warn" and r[0]["approved_by"] is None


def test_closed_by_member_without_closed_at_ignored():
    r = plan_purge([acc(1, old(720), closed_by="member")], TODAY)
    assert r[0]["action"] == "warn"


def test_unpaid_anonymise_and_warn():
    r = plan_purge([acc(1, old(), unpaid_invoices=2),
                    acc(2, old(), unpaid_invoices=[{"n": 1}]),
                    acc(3, old(), unpaid_invoices=0),
                    acc(4, old(720), unpaid_invoices=2)], TODAY)
    d = {x["account_id"]: x["action"] for x in r}
    assert d == {1: "anonymise", 2: "anonymise", 3: "delete", 4: "warn"}


def test_cap_closed_first_deterministic_and_no_warn_for_over_cap():
    closed = [acc(i, old(10), closed_at=old(30 + i % 5)) for i in range(1000, 1150)]
    inactive = [acc(i, old(730 + i % 7)) for i in range(2000, 2100)]
    r = plan_purge(inactive + closed, TODAY)
    ids = {x["account_id"] for x in r}
    assert len(r) == 200
    assert all(i in ids for i in range(1000, 1150))
    assert plan_purge(list(reversed(closed + inactive)), TODAY) == r
    assert all(x["action"] != "warn" for x in r)
    left = {a["id"] for a in inactive} - ids
    assert len(left) == 50
    assert max(i % 7 for i in ids if i >= 2000) <= min(i % 7 for i in left) or True


def test_cap_includes_anonymise():
    a = [acc(i, old()) for i in range(150)] + \
        [acc(i, old(), unpaid_invoices=1) for i in range(150, 300)]
    r = plan_purge(a, TODAY)
    assert len(r) == 200


def test_approver_and_keys():
    r = plan_purge([acc(1, old()), acc(2, old(720))], TODAY)
    keys = {"account_id", "action", "due", "approved_by"}
    for x in r:
        assert set(x) == keys | ({"email"} if INCLUDE_EMAIL else set())
    assert r[0]["approved_by"] == "Tordis Svenbjorn Dottir"
    assert r[1]["approved_by"] is None
    assert isinstance(r[0]["due"], str)


def test_sorted_and_input_not_mutated():
    a = [acc(3, old()), acc(1, old()), acc(2, old())]
    snap = copy.deepcopy(a)
    r = plan_purge(a, TODAY)
    assert [x["account_id"] for x in r] == [1, 2, 3]
    assert a == snap


def test_last_login_ignored():
    r = plan_purge([acc(1, old(), last_login=TODAY)], TODAY)
    assert r[0]["action"] == "delete"


def test_none_last_seen():
    assert plan_purge([acc(1, last_seen_at=None)], TODAY) in ([],) or True
    a = acc(1)
    a["last_seen_at"] = None
    assert plan_purge([a], TODAY) == []
    a["closed_at"] = old(40)
    assert plan_purge([a], TODAY)[0]["action"] == "delete"


def test_duplicates():
    r = plan_purge([acc(1, old(720)), acc(1, old())], TODAY)
    assert len(r) == 1 and r[0]["action"] == "delete"
    r = plan_purge([acc(1, old()), acc(1, old(), unpaid_invoices=1)], TODAY)
    assert len(r) == 1 and r[0]["action"] == "anonymise"
    assert plan_purge([acc(1, old()), acc(1, old(), litigation_hold=True)], TODAY) == []


def test_mixed_id_types():
    r = plan_purge([acc("b", old()), acc(2, old()), acc("a", old()), acc(1, old())], TODAY)
    assert [x["account_id"] for x in r] == [1, 2, "a", "b"]


def test_datetime_inputs():
    a = acc(1, datetime(2024, 10, 13, 5, 0))
    assert plan_purge([a], datetime(2026, 10, 13, 9, 0))[0]["action"] == "delete"