"""GDPR purge planner: plan_purge(accounts, today).

Assumptions to confirm with the client:
- The 200 cap counts deletes only; anonymise and warn actions are uncapped.
- Accounts with unpaid invoices still get a warn action before they are due.
- `status`, `last_login` and `tenant` are ignored.
- Warnings are stateless, so an account is warned on each run in its 14-day window.
- Deferred deletes (over the cap) are omitted and will reappear on later runs.
- Actions carry no email. The client brief forbids it because the audit log is
  shared with the federation. This overrides the internal "house rule" that asked
  for an email in each action, and that conflict should be confirmed.

Tests can be run with: pytest purge.py
"""
import json
from datetime import date, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
MAX_DELETES = 200


def _is_staff(email):
    return email is not None and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(acc):
    candidates = []
    if acc.get("last_seen_at") is not None:
        candidates.append(acc["last_seen_at"] + timedelta(days=INACTIVITY_DAYS))
    if acc.get("closed_at") is not None:
        candidates.append(acc["closed_at"] + timedelta(days=CLOSED_DAYS))
    return min(candidates) if candidates else None


def _apply_delete_cap(deletes, limit=MAX_DELETES):
    """deletes: list of (account, action_dict). Closed first, earliest due, then id."""
    if len(deletes) <= limit:
        return deletes
    ranked = sorted(
        deletes,
        key=lambda p: (p[0].get("closed_at") is None, p[1]["due"], p[1]["account_id"]),
    )
    return ranked[:limit]


def plan_purge(accounts, today):
    ids = [a["id"] for a in accounts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate account ids")

    deletes, others = [], []
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        due = _due(acc)
        if due is None:
            continue
        if due <= today:
            action = "anonymise" if acc.get("unpaid_invoices") else "delete"
            approver = APPROVER
        elif due <= today + timedelta(days=WARN_DAYS):
            if acc.get("closed_at") is not None and acc.get("closed_by") == "member":
                continue
            action, approver = "warn", None
        else:
            continue
        item = {
            "account_id": acc["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": approver,
        }
        if action == "delete":
            deletes.append((acc, item))
        else:
            others.append(item)

    kept = [item for _, item in _apply_delete_cap(deletes)]
    return sorted(others + kept, key=lambda i: i["account_id"])


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)


def _acc(id, seen=None, closed=None, **kw):
    base = {
        "id": id, "email": f"{id}@example.com", "status": "active",
        "last_seen_at": seen, "last_login": None, "closed_at": closed,
        "closed_by": "staff", "unpaid_invoices": False, "litigation_hold": False,
    }
    base.update(kw)
    return base


def _d(n):
    return TODAY - timedelta(days=n)


def _actions(accs):
    return [(a["action"]) for a in plan_purge(accs, TODAY)]


def test_inactivity_boundaries():
    assert _actions([_acc("a", seen=_d(729))]) == ["warn"]
    assert _actions([_acc("a", seen=_d(730))]) == ["delete"]
    assert _actions([_acc("a", seen=_d(731))]) == ["delete"]


def test_closed_boundaries():
    assert _actions([_acc("a", seen=_d(1), closed=_d(29))]) == ["warn"]
    assert _actions([_acc("a", seen=_d(1), closed=_d(30))]) == ["delete"]
    assert _actions([_acc("a", seen=_d(1), closed=_d(31))]) == ["delete"]


def test_warn_window_boundaries():
    assert _actions([_acc("a", seen=_d(730 - 13))]) == ["warn"]
    assert _actions([_acc("a", seen=_d(730 - 14))]) == ["warn"]
    assert _actions([_acc("a", seen=_d(730 - 15))]) == []


def test_member_closed_no_warn_but_delete():
    a = _acc("a", seen=_d(1), closed=_d(20), closed_by="member")
    assert plan_purge([a], TODAY) == []
    b = _acc("b", seen=_d(1), closed=_d(40), closed_by="member")
    assert _actions([b]) == ["delete"]


def test_none_dates():
    assert plan_purge([_acc("a")], TODAY) == []
    assert _actions([_acc("a", closed=_d(30))]) == ["delete"]


def test_unpaid_anonymise_and_warn():
    r = plan_purge([_acc("a", seen=_d(800), unpaid_invoices=True),
                    _acc("b", seen=_d(720), unpaid_invoices=True)], TODAY)
    assert [x["action"] for x in r] == ["anonymise", "warn"]
    assert r[0]["approved_by"] == APPROVER and r[1]["approved_by"] is None


def test_exclusions():
    accs = [
        _acc("a", seen=_d(800), litigation_hold=True),
        _acc("b", seen=_d(800), email="  Bob@Tidewater-Klatring.NO "),
        _acc("c", seen=_d(800), email=None),
    ]
    assert [x["account_id"] for x in plan_purge(accs, TODAY)] == ["c"]


def test_cap_closed_first_then_due_then_id():
    accs = [_acc(f"i{n:03d}", seen=_d(1000 + n)) for n in range(200)]
    accs += [_acc("c1", seen=_d(1), closed=_d(31)), _acc("c2", seen=_d(1), closed=_d(31))]
    accs += [_acc("an", seen=_d(5000), unpaid_invoices=True)]
    accs += [_acc("w", seen=_d(720))]
    r = plan_purge(accs, TODAY)
    deletes = [x for x in r if x["action"] == "delete"]
    ids = {x["account_id"] for x in r}
    assert len(deletes) == 200
    assert {"c1", "c2", "an", "w"} <= ids
    # two least-overdue inactive accounts (i198, i199 have the earliest due) are... check
    assert "i000" in ids and "i199" not in ids and "i198" not in ids
    assert [x["account_id"] for x in r] == sorted(x["account_id"] for x in r)


def test_duplicates_and_empty():
    assert plan_purge([], TODAY) == []
    try:
        plan_purge([_acc("a"), _acc("a")], TODAY)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_output_shape_json_no_email_no_mutation():
    accs = [_acc("a", seen=_d(800)), _acc("b", seen=_d(720))]
    snapshot = json.dumps(accs, default=str)
    r = plan_purge(accs, TODAY)
    assert json.dumps(accs, default=str) == snapshot
    s = json.dumps(r)
    assert "example.com" not in s and "email" not in s
    for x in r:
        assert set(x) == {"account_id", "action", "due", "approved_by"}