# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-e15ekm1h/purge.py =====
```
"""GDPR clean-up planner for Tidewater Climbing member accounts.

Rules:
- Skipped entirely: litigation_hold truthy, or staff email (str ending with
  STAFF_DOMAIN after strip().lower()). Non-str/None email is non-staff.
- inactivity_due = last_seen_at + 730d; closed_due = closed_at + 30d
  (closed_at not None is the closure signal). due = earliest available;
  none available -> skipped.
- due <= today: "anonymise" if unpaid invoices else "delete".
- today < due <= today + 40d: "warn" unless closed_by == "member".
- At most MAX_DELETES deletes, chosen by (closed first, earliest due, id).
  Anonymise and warn are never capped. Dropped deletes yield no action.
- Output sorted by account_id; at most one action per account.
- last_login, status and tenant are ignored. Email never appears in output.

Decisions / ambiguities (reported to client):
- Cap applies to deletes only; anonymise is uncapped (may exceed DB lock
  concerns - FLAG). Cap priority first, then final sort by id.
- warn approved_by is None. Capped accounts get no warn or report.
- Warn window is today < due <= today+40.
- closed_at not None drives closure, not status (FLAG).
- Unpaid invoices on closed/member-closed accounts follow the same rules
  (anonymise; member-closed still never warned).
- Missing last_seen_at on an open account is skipped (FLAG).
- Member-closed accounts never warn, even if inactivity is the earlier due.
- unpaid_invoices: numbers are unpaid if > 0; other values by bool().
- Unknown closed_by values are treated as non-member.
- closed_at in the future is used as-is. Duplicate ids are not deduplicated.
- Staff check is case-insensitive and whitespace tolerant.
- Warn is emitted for accounts with unpaid invoices.
- CONFLICT (FLAG): a house rule asked for the email on every action dict,
  but the task spec requires exactly four keys and no email in any output.
  The spec was followed; confirm with the client if the email is wanted.
"""
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 40
MAX_DELETES = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO_NAME = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"


def _is_staff(email):
    """True if email is a str ending with the staff domain (case/space-insensitive)."""
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _due_date(acct):
    """Earliest of inactivity and closed due dates, or None if neither exists."""
    dues = []
    if acct.get("last_seen_at") is not None:
        dues.append(acct["last_seen_at"] + timedelta(days=INACTIVITY_DAYS))
    if acct.get("closed_at") is not None:
        dues.append(acct["closed_at"] + timedelta(days=CLOSED_GRACE_DAYS))
    return min(dues) if dues else None


def _has_unpaid(value):
    """Positive number or non-empty collection is unpaid; None/0/[] is not."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    return bool(value)


def _id_key(account_id):
    """Sort key tolerant of mixed id types."""
    if isinstance(account_id, (int, str)):
        return (type(account_id).__name__, account_id)
    return (type(account_id).__name__, str(account_id))


def _classify(acct, today):
    """Return (action, due) for one account, or None for no action."""
    if acct.get("litigation_hold") or _is_staff(acct.get("email")):
        return None
    due = _due_date(acct)
    if due is None:
        return None
    if due <= today:
        return ("anonymise" if _has_unpaid(acct.get("unpaid_invoices")) else "delete"), due
    if due <= today + timedelta(days=WARN_WINDOW_DAYS):
        if acct.get("closed_by") == "member":
            return None
        return "warn", due
    return None


def _action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_NAME,
    }


def plan_purge(accounts, today):
    """Return the list of purge actions for accounts as of today."""
    if not isinstance(today, date):
        raise TypeError("today must be a datetime.date")
    deletes, others = [], []
    for acct in accounts:
        res = _classify(acct, today)
        if res is None:
            continue
        action, due = res
        if action == "delete":
            closed = acct.get("closed_at") is not None
            deletes.append(((0 if closed else 1, due, _id_key(acct["id"])), acct["id"], due))
        else:
            others.append(_action(acct["id"], action, due))
    deletes.sort(key=lambda t: t[0])
    out = others + [_action(i, "delete", d) for _, i, d in deletes[:MAX_DELETES]]
    out.sort(key=lambda a: _id_key(a["account_id"]))
    return out
```

# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-e15ekm1h/test_purge.py =====
```
import copy
import json
from datetime import date, timedelta

import pytest

import purge
from purge import plan_purge, DPO_NAME

TODAY = date(2026, 10, 13)


def acct(**kw):
    base = dict(id=1, email="m@example.com", status="active",
                last_seen_at=TODAY, last_login=TODAY, closed_at=None,
                closed_by=None, unpaid_invoices=0, litigation_hold=False,
                tenant="t")
    base.update(kw)
    return base


def seen(days_ago):
    return TODAY - timedelta(days=days_ago)


def one(a):
    return plan_purge([a], TODAY)


def test_dpo_name_literal():
    assert DPO_NAME == "Þórdís Sveinbjörnsdóttir"


def test_delete_at_730_not_729():
    assert one(acct(last_seen_at=seen(730)))[0]["action"] == "delete"
    assert one(acct(last_seen_at=seen(729))) == [] or one(acct(last_seen_at=seen(729)))[0]["action"] == "warn"
    assert one(acct(last_seen_at=seen(729)))[0]["action"] == "warn"


def test_warn_window_edges():
    assert one(acct(last_seen_at=seen(730 - 40)))[0]["action"] == "warn"
    assert one(acct(last_seen_at=seen(730 - 41))) == []


def test_due_today_is_delete_not_warn():
    assert one(acct(last_seen_at=seen(730)))[0]["action"] == "delete"


def test_closed_sooner_and_inactivity_sooner():
    r = one(acct(last_seen_at=seen(10), closed_at=seen(30)))
    assert r[0]["action"] == "delete" and r[0]["due"] == TODAY.isoformat()
    r = one(acct(last_seen_at=seen(730), closed_at=seen(1)))
    assert r[0]["due"] == TODAY.isoformat()


def test_last_login_ignored():
    assert one(acct(last_seen_at=seen(800), last_login=TODAY))[0]["action"] == "delete"


def test_member_closed():
    assert one(acct(closed_at=seen(-10), closed_by="member")) == []
    assert one(acct(closed_at=seen(31), closed_by="member"))[0]["action"] == "delete"


def test_staff_closed_warns_and_unknown_closed_by():
    assert one(acct(closed_at=seen(-10), closed_by="staff"))[0]["action"] == "warn"
    assert one(acct(closed_at=seen(-10), closed_by=None))[0]["action"] == "warn"
    assert one(acct(closed_at=seen(-10), closed_by="robot"))[0]["action"] == "warn"


@pytest.mark.parametrize("val,exp", [(2, "anonymise"), (["inv"], "anonymise"),
                                     (0, "delete"), (None, "delete"), ([], "delete")])
def test_unpaid(val, exp):
    assert one(acct(last_seen_at=seen(800), unpaid_invoices=val))[0]["action"] == exp


def test_warn_with_unpaid():
    assert one(acct(last_seen_at=seen(700), unpaid_invoices=3))[0]["action"] == "warn"


def test_anonymise_uncapped():
    accts = [acct(id=i, last_seen_at=seen(800), unpaid_invoices=1) for i in range(300)]
    assert len(plan_purge(accts, TODAY)) == 300


def test_litigation_hold():
    assert one(acct(last_seen_at=seen(800), litigation_hold=True)) == []
    assert one(acct(last_seen_at=seen(700), litigation_hold=True)) == []


@pytest.mark.parametrize("email", ["a@tidewater-klatring.no", "A@TIDEWATER-KLATRING.NO",
                                   "  a@Tidewater-Klatring.no \n"])
def test_staff_skipped(email):
    assert one(acct(email=email, last_seen_at=seen(800))) == []


@pytest.mark.parametrize("email", ["x@tidewater-klatring.no.evil.com",
                                   "x@not-tidewater-klatring.no", None, 42])
def test_not_staff(email):
    assert one(acct(email=email, last_seen_at=seen(800)))[0]["action"] == "delete"


def test_output_shape_and_privacy():
    out = plan_purge([acct(id=1, last_seen_at=seen(800)),
                      acct(id=2, last_seen_at=seen(700))], TODAY)
    d, w = out
    assert d["approved_by"] == DPO_NAME and w["approved_by"] is None
    assert set(d) == {"account_id", "action", "due", "approved_by"}
    assert isinstance(d["due"], str) and date.fromisoformat(d["due"])
    assert "m@example.com" not in json.dumps(out)


def test_anonymise_approver():
    assert one(acct(last_seen_at=seen(800), unpaid_invoices=1))[0]["approved_by"] == DPO_NAME


def test_tenant_ignored():
    a = acct(last_seen_at=seen(800), tenant=object())
    assert one(a)[0]["action"] == "delete"
    del a["tenant"]
    assert one(a)[0]["action"] == "delete"


def test_inputs_unchanged():
    accts = [acct(id=1, last_seen_at=seen(800)), acct(id=2, last_seen_at=seen(700))]
    before = copy.deepcopy(accts)
    plan_purge(accts, TODAY)
    assert accts == before


def test_missing_last_seen():
    assert one(acct(last_seen_at=None)) == []
    r = one(acct(last_seen_at=None, closed_at=seen(31)))
    assert r[0]["action"] == "delete"


def test_cap_priority():
    accts = []
    for i in range(100):  # closed, various dues
        accts.append(acct(id=1000 + i, last_seen_at=None, closed_at=seen(31 + i % 5)))
    for i in range(150):  # inactive, earlier dues for higher i
        accts.append(acct(id=i, last_seen_at=seen(731 + i % 10)))
    out = plan_purge(accts, TODAY)
    assert len(out) == 200
    ids = {a["account_id"] for a in out}
    assert all(1000 + i in ids for i in range(100))
    kept_inactive = [a for a in accts if a["id"] < 1000 and a["id"] in ids]
    dropped = [a for a in accts if a["id"] < 1000 and a["id"] not in ids]
    assert len(kept_inactive) == 100
    worst_kept = max(a["last_seen_at"] for a in kept_inactive)
    assert all(a["last_seen_at"] >= worst_kept for a in dropped)
    # tie-break by id among equal due
    tied = [a for a in kept_inactive if a["last_seen_at"] == worst_kept]
    tied_dropped = [a for a in dropped if a["last_seen_at"] == worst_kept]
    if tied_dropped:
        assert max(a["id"] for a in tied) < min(a["id"] for a in tied_dropped)
    assert [a["account_id"] for a in out] == sorted(ids)


def test_warns_unaffected_by_cap():
    accts = [acct(id=i, last_seen_at=seen(800)) for i in range(250)]
    accts.append(acct(id=999, last_seen_at=seen(700)))
    out = plan_purge(accts, TODAY)
    assert sum(a["action"] == "delete" for a in out) == 200
    assert sum(a["action"] == "warn" for a in out) == 1


def test_sorted_by_id():
    out = plan_purge([acct(id=i, last_seen_at=seen(800)) for i in (5, 3, 9, 1)], TODAY)
    assert [a["account_id"] for a in out] == [1, 3, 5, 9]


def test_empty_and_bad_today():
    assert plan_purge([], TODAY) == []
    with pytest.raises(TypeError):
        plan_purge([], "2026-10-13")
```