"""Purge planner for Tidewater Climbing member accounts (Python 3.12, stdlib only).

Spec: plan_purge(accounts, today) -> list of dicts with exactly the keys
account_id, action, due, approved_by.

- due = min(last_seen_at + 730d, closed_at + 30d if closed_at is set).
  last_seen_at None gives no inactivity due (last_login is never used).
  If both are None there is no action. due is emitted as an ISO string and may be in the past.
- due <= today: "delete", or "anonymise" if the account has unpaid invoices.
  approved_by is the DPO.
- today < due <= today + 40d: "warn" with approved_by None. This includes accounts
  with unpaid invoices. Member-closed accounts (closed_by == "member" and closed_at set)
  are never warned. Missing or odd closed_by counts as non-member.
- Skipped entirely: litigation_hold truthy, staff email (@tidewater-klatring.no,
  stripped and casefolded), and status "anonymised" or "deleted" (stripped, casefolded).
- Cap of 200 applies to "delete" only. Order: closed accounts first, then earliest due,
  then id. Deletes cut by the cap are neither emitted nor warned.
- Output is sorted by account id (ints first, then str(id)), then by action.
- Input is not mutated. tenant and last_login are ignored.

Assumptions and open questions for the client:
1. last_seen_at None with no closed_at: never purged. Is that intended?
2. The cap counts deletes only, not anonymise. Is that right?
3. Accounts with status "anonymised" or "deleted" are skipped. Please confirm the
   status values and that other values are irrelevant.
4. Unpaid-invoice accounts still get a warning, because the member should be told
   their data is about to go.
5. Cut deletes are not warned, and they reappear in the next run.
6. Conflict: a house rule asked for each action to also carry the account's email. The
   client brief forbids email in actions (the audit log is shared with the climbing
   federation), so email is NOT output. Please confirm with the client, and with support
   if they need a different channel.
7. Anonymise keeps invoices for 5 years (Skatteetaten). Retention of the anonymised
   record afterwards is out of scope.

Tests are included below (pytest) and have NOT been run in this session.
"""
from datetime import date, timedelta

DPO = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
CAP = 200


def _truthy(v):
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) > 0
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v > 0
    if v is None:
        return False
    return bool(v)


def _id_key(i):
    if isinstance(i, int) and not isinstance(i, bool):
        return (0, i)
    return (1, str(i))


def _is_staff(email):
    return isinstance(email, str) and email.strip().casefold().endswith(STAFF_SUFFIX)


def _skipped_status(s):
    return isinstance(s, str) and s.strip().casefold() in ("anonymised", "deleted")


def plan_purge(accounts, today):
    horizon = today + timedelta(days=40)
    deletes, others = [], []
    for a in accounts:
        if _truthy(a.get("litigation_hold")) or _is_staff(a.get("email")):
            continue
        if _skipped_status(a.get("status")):
            continue
        seen, closed = a.get("last_seen_at"), a.get("closed_at")
        cands = []
        if seen is not None:
            cands.append(seen + timedelta(days=730))
        if closed is not None:
            cands.append(closed + timedelta(days=30))
        if not cands:
            continue
        due = min(cands)
        aid = a.get("id")
        if due <= today:
            if _truthy(a.get("unpaid_invoices")):
                others.append((aid, "anonymise", due))
            else:
                deletes.append((aid, "delete", due, closed is not None))
        elif due <= horizon:
            if a.get("closed_by") == "member" and closed is not None:
                continue
            others.append((aid, "warn", due))
    deletes.sort(key=lambda d: (0 if d[3] else 1, d[2], _id_key(d[0])))
    chosen = [d[:3] for d in deletes[:CAP]]
    out = [
        {
            "account_id": aid,
            "action": act,
            "due": due.isoformat(),
            "approved_by": None if act == "warn" else DPO,
        }
        for aid, act, due in chosen + others
    ]
    out.sort(key=lambda r: (_id_key(r["account_id"]), r["action"]))
    return out


# ----------------------------- tests (pytest) -----------------------------
import copy

T = date(2026, 10, 13)


def _acc(**kw):
    base = dict(id=1, email="m@example.com", status="active",
                last_seen_at=T - timedelta(days=10), last_login=None,
                closed_at=None, closed_by=None, unpaid_invoices=[],
                litigation_hold=False, tenant="x")
    base.update(kw)
    return base


def _d(n):
    return T + timedelta(days=n)


def test_due_today_deletes():
    r = plan_purge([_acc(last_seen_at=_d(-730))], T)
    assert r == [{"account_id": 1, "action": "delete", "due": T.isoformat(), "approved_by": DPO}]


def test_warn_edges():
    assert plan_purge([_acc(last_seen_at=_d(-690))], T)[0]["action"] == "warn"
    assert plan_purge([_acc(last_seen_at=_d(-689))], T) == []
    assert plan_purge([_acc(last_seen_at=_d(-729))], T)[0]["approved_by"] is None


def test_closed_earlier_than_inactivity():
    r = plan_purge([_acc(closed_at=_d(-30), closed_by="staff")], T)
    assert r[0]["action"] == "delete" and r[0]["due"] == T.isoformat()
    r = plan_purge([_acc(closed_at=_d(-40), closed_by="staff")], T)
    assert r[0]["due"] == _d(-10).isoformat()


def test_member_closed_no_warn_but_deleted():
    assert plan_purge([_acc(closed_at=_d(-5), closed_by="member")], T) == []
    assert plan_purge([_acc(closed_at=_d(-30), closed_by="member")], T)[0]["action"] == "delete"


def test_odd_closed_by_warns():
    for cb in (None, "robot", "MEMBER"):
        assert plan_purge([_acc(closed_at=_d(-5), closed_by=cb)], T)[0]["action"] == "warn"


def test_future_closed_at():
    r = plan_purge([_acc(closed_at=_d(5), closed_by="staff")], T)
    assert r[0]["action"] == "warn" and r[0]["due"] == _d(35).isoformat()


def test_unpaid_anonymise_and_warn():
    r = plan_purge([_acc(last_seen_at=_d(-730), unpaid_invoices=[1])], T)
    assert r[0]["action"] == "anonymise" and r[0]["approved_by"] == DPO
    r = plan_purge([_acc(last_seen_at=_d(-700), unpaid_invoices=3)], T)
    assert r[0]["action"] == "warn"
    r = plan_purge([_acc(last_seen_at=_d(-730), unpaid_invoices=0)], T)
    assert r[0]["action"] == "delete"


def test_litigation_hold():
    for lh in (True, 1, "yes"):
        assert plan_purge([_acc(last_seen_at=_d(-800), litigation_hold=lh)], T) == []


def test_staff():
    old = _d(-800)
    for e in ("a@Tidewater-Klatring.NO", "  a@tidewater-klatring.no \n"):
        assert plan_purge([_acc(email=e, last_seen_at=old)], T) == []
    assert len(plan_purge([_acc(email=None, last_seen_at=old)], T)) == 1
    assert len(plan_purge([_acc(email=5, last_seen_at=old)], T)) == 1


def test_no_email_and_exact_keys():
    r = plan_purge([_acc(last_seen_at=_d(-800)), _acc(id=2, last_seen_at=_d(-700))], T)
    for a in r:
        assert set(a) == {"account_id", "action", "due", "approved_by"}
        assert "m@example.com" not in repr(a)


def test_cap_closed_first_and_anonymise_uncounted():
    accs = [_acc(id=i, last_seen_at=_d(-731 - i)) for i in range(150)]
    accs += [_acc(id=1000 + i, closed_at=_d(-30 - i), closed_by="staff") for i in range(120)]
    accs += [_acc(id=2000 + i, last_seen_at=_d(-800), unpaid_invoices=[1]) for i in range(5)]
    r = plan_purge(accs, T)
    dels = [a for a in r if a["action"] == "delete"]
    assert len(dels) == 200
    assert len([a for a in r if a["action"] == "anonymise"]) == 5
    ids = {a["account_id"] for a in dels}
    assert set(range(1000, 1120)) <= ids
    assert ids - set(range(1000, 1120)) == set(range(70, 150))
    assert not any(a["account_id"] < 70 for a in r)


def test_sorting_mixed_ids():
    accs = [_acc(id=i, last_seen_at=_d(-800)) for i in (10, "b", 2, "a")]
    assert [a["account_id"] for a in plan_purge(accs, T)] == [2, 10, "a", "b"]


def test_approved_by_exact():
    assert DPO == "Þórdís Sveinbjörnsdóttir"


def test_input_not_mutated():
    accs = [_acc(last_seen_at=_d(-800)), _acc(id=2, last_seen_at=_d(-700))]
    before = copy.deepcopy(accs)
    plan_purge(accs, T)
    assert accs == before


def test_last_seen_none():
    assert plan_purge([_acc(last_seen_at=None, last_login=_d(-900))], T) == []
    r = plan_purge([_acc(last_seen_at=None, closed_at=_d(-30), closed_by="staff")], T)
    assert r[0]["action"] == "delete"


def test_status_skip():
    for s in ("anonymised", " Deleted "):
        assert plan_purge([_acc(status=s, last_seen_at=_d(-800))], T) == []
    assert len(plan_purge([_acc(status="weird", last_seen_at=_d(-800))], T)) == 1