"""Tidewater Climbing GDPR clean-up planner. Pure function: no I/O, no side effects.

Conflict for tech lead: the house rule requires every action dict to carry the account's `email` for support follow-up. The spec says "do not include the member's email in any output value". The house rule is implemented here, so the "no output value contains an email" acceptance criterion is not asserted in the self-tests. Needs sign-off.
"""
import datetime as dt

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = dt.timedelta(days=730)
CLOSE_GRACE = dt.timedelta(days=30)
WARN_WINDOW = dt.timedelta(days=14)
DELETE_CAP = 200
_REQUIRED = ("id", "email", "status", "last_seen_at", "last_login",
             "closed_at", "closed_by", "unpaid_invoices", "litigation_hold")


def _is_date(v):
    return isinstance(v, dt.date) and not isinstance(v, dt.datetime)


def _validate(acc):
    if not isinstance(acc, dict):
        raise ValueError("account must be a dict")
    missing = [k for k in _REQUIRED if k not in acc]
    if missing:
        raise ValueError(f"account missing fields: {missing}")
    aid = acc["id"]
    if not isinstance(aid, str) or not aid:
        raise ValueError("id must be a non-empty string")
    if not isinstance(acc["email"], str):
        raise ValueError(f"{aid}: email must be a string")
    if not _is_date(acc["last_seen_at"]):
        raise ValueError(f"{aid}: last_seen_at must be a date")
    if not _is_date(acc["last_login"]):
        raise ValueError(f"{aid}: last_login must be a date")
    if acc["closed_at"] is not None and not _is_date(acc["closed_at"]):
        raise ValueError(f"{aid}: closed_at must be a date or None")
    if acc["closed_by"] not in ("member", "staff"):
        raise ValueError(f"{aid}: closed_by must be 'member' or 'staff'")
    u = acc["unpaid_invoices"]
    if not isinstance(u, int) or isinstance(u, bool) or u < 0:
        raise ValueError(f"{aid}: unpaid_invoices must be a non-negative int")
    if not isinstance(acc["litigation_hold"], bool):
        raise ValueError(f"{aid}: litigation_hold must be a bool")


def _due_date(acc):
    due = acc["last_seen_at"] + INACTIVITY
    if acc["closed_at"] is not None:
        due = min(due, acc["closed_at"] + CLOSE_GRACE)
    return due


def _action(acc, kind, due):
    return {
        "account_id": acc["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": None if kind == "warn" else APPROVER,
        "email": acc["email"],
    }


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")
    seen = set()
    deletes = []
    actions = []
    for acc in accounts:
        _validate(acc)
        aid = acc["id"]
        if aid in seen:
            raise ValueError(f"duplicate account id: {aid}")
        seen.add(aid)
        if acc["email"].lower().endswith(STAFF_SUFFIX):
            continue
        if acc["litigation_hold"]:
            continue
        due = _due_date(acc)
        if due <= today:
            if acc["unpaid_invoices"] > 0:
                actions.append(_action(acc, "anonymise", due))
            else:
                group = 0 if acc["closed_at"] is not None else 1
                deletes.append((group, due, aid, acc))
        elif due <= today + WARN_WINDOW and acc["closed_by"] != "member":
            actions.append(_action(acc, "warn", due))
    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    for _, due, _, acc in deletes[:DELETE_CAP]:
        actions.append(_action(acc, "delete", due))
    actions.sort(key=lambda a: a["account_id"])
    return actions


TODAY = dt.date(2026, 10, 13)


def _acc(i, **kw):
    base = {"id": f"acc{i:04d}", "email": f"member{i}@example.com", "status": "active",
            "last_seen_at": TODAY, "last_login": TODAY, "closed_at": None,
            "closed_by": "staff", "unpaid_invoices": 0, "litigation_hold": False}
    base.update(kw)
    return base


def _selftest():
    T = TODAY
    ago = lambda n: T - dt.timedelta(days=n)
    k = lambda accs: {a["account_id"]: a["action"] for a in plan_purge(accs, T)}

    assert k([_acc(1, last_seen_at=ago(730))]) == {"acc0001": "delete"}
    assert k([_acc(2, last_seen_at=ago(729))]) == {"acc0002": "warn"}
    assert k([_acc(3, last_seen_at=ago(1), closed_at=ago(30), closed_by="member")]) == {"acc0003": "delete"}
    assert k([_acc(4, last_seen_at=ago(730), unpaid_invoices=2)]) == {"acc0004": "anonymise"}
    assert k([_acc(5, last_seen_at=ago(900), litigation_hold=True)]) == {}
    assert k([_acc(6, email="Ops@TIDEWATER-klatring.NO", last_seen_at=ago(900))]) == {}
    assert k([_acc(7, last_seen_at=ago(720), closed_at=ago(20), closed_by="member")]) == {}
    assert k([_acc(8, last_seen_at=ago(720), closed_at=ago(20), closed_by="staff")]) == {"acc0008": "warn"}
    assert k([_acc(9, last_seen_at=ago(720))]) == {"acc0009": "warn"}
    assert k([_acc(10, last_seen_at=ago(716))]) == {"acc0010": "warn"}
    assert k([_acc(11, last_seen_at=ago(715))]) == {}
    assert k([_acc(12, last_seen_at=ago(731), last_login=T)]) == {"acc0012": "delete"}

    accs = [_acc(i, last_seen_at=ago(800 + i),
                 closed_at=ago(40) if i < 100 else None,
                 closed_by="member" if i < 100 else "staff") for i in range(250)]
    out = plan_purge(accs, T)
    deletes = [a for a in out if a["action"] == "delete"]
    assert len(deletes) == 200
    assert {f"acc{i:04d}" for i in range(100)} <= {d["account_id"] for d in deletes}
    ids = [a["account_id"] for a in out]
    assert ids == sorted(ids)
    assert plan_purge(accs, T) == plan_purge(list(reversed(accs)), T)

    def raises(bad):
        try:
            plan_purge([bad], T)
        except ValueError:
            return True
        return False

    bad = _acc(13)
    del bad["unpaid_invoices"]
    assert raises(bad)
    assert raises(_acc(14, last_seen_at=None))
    assert raises(_acc(15, closed_at="2026-01-01"))
    assert raises(_acc(16, last_seen_at=dt.datetime(2024, 1, 1)))
    print("selftest ok")


if __name__ == "__main__":
    _selftest()