# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-vae0p235/purge.py =====
# Open client questions (unanswered, no answers invented):
# (1) Does the 200 cap also apply to anonymise?
# (2) Are deferred past-due accounts meant to get no warning?
# (3) What status values exist, and should status ever override closed_at?
# (4) What should happen with accounts with no last_seen_at?
# (5) Is unpaid_invoices a count or a flag, and can it be negative or None?
# (6) Should accounts with unpaid invoices be warned?
# (7) Should a future closed_at be treated as a data error?
# (8) Is a closed_by == "member" with no closed_at meaningful?
#
# Note: a house rule asked for the account email on every action dict. The
# task spec requires exactly four keys and no email in output (GDPR), so the
# email is deliberately NOT emitted. Please confirm with the client.
from datetime import timedelta

INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
MAX_PURGES = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
DPO = "Þórdís Sveinbjörnsdóttir"


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _due(acct):
    dues = []
    seen = acct.get("last_seen_at")
    if seen is not None:
        dues.append(seen + timedelta(days=INACTIVITY_DAYS))
    closed = acct.get("closed_at")
    if closed is not None:
        dues.append(closed + timedelta(days=CLOSED_DAYS))
    return min(dues) if dues else None


def plan_purge(accounts, today):
    purges = []  # (rank_key, action dict)
    warns = []
    horizon = today + timedelta(days=WARN_DAYS)
    for a in accounts:
        if a.get("litigation_hold") or _is_staff(a.get("email")):
            continue
        due = _due(a)
        if due is None:
            continue
        aid = a["id"]
        if due <= today:
            action = "anonymise" if (a.get("unpaid_invoices") or 0) > 0 else "delete"
            closed = a.get("closed_at")
            is_closed = closed is not None and closed <= today
            purges.append(((0 if is_closed else 1, due, aid), {
                "account_id": aid, "action": action,
                "due": due.isoformat(), "approved_by": DPO}))
        elif due <= horizon and a.get("closed_by") != "member":
            warns.append({"account_id": aid, "action": "warn",
                          "due": due.isoformat(), "approved_by": None})

    # ASSUMPTION (flagged, client question 1): the cap counts delete and
    # anonymise together. Deferred accounts are dropped entirely (no warning).
    purges.sort(key=lambda p: p[0])
    kept = [p[1] for p in purges[:MAX_PURGES]]

    return sorted(kept + warns, key=lambda r: r["account_id"])


# ===== /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-vae0p235/test_purge.py =====
import copy
import json
import random
from datetime import date, timedelta

from purge import DPO, plan_purge

TODAY = date(2026, 10, 13)


def d(n):
    return TODAY + timedelta(days=n)


def acct(id="a1", **kw):
    base = dict(id=id, email="m@example.com", status="active",
                last_seen_at=d(-10), last_login=d(-10), closed_at=None,
                closed_by="staff", unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


def run(*accts):
    return plan_purge(list(accts), TODAY)


def test_last_seen_not_last_login():
    assert run(acct(last_login=d(-5000))) == []


def test_730_deletes_and_729_warns():
    r = run(acct(last_seen_at=d(-730)))
    assert r == [dict(account_id="a1", action="delete", due=TODAY.isoformat(), approved_by=DPO)]
    r = run(acct(last_seen_at=d(-729)))
    assert r[0]["action"] == "warn" and r[0]["due"] == d(1).isoformat()


def test_closed_30_days_deletes():
    assert run(acct(last_seen_at=d(-1), closed_at=d(-30)))[0]["action"] == "delete"


def test_earlier_due_wins():
    # closed due later than inactivity due -> inactivity (today) used
    r = run(acct(last_seen_at=d(-730), closed_at=d(-1)))
    assert r[0]["due"] == TODAY.isoformat()
    # closed due sooner
    r = run(acct(last_seen_at=d(-100), closed_at=d(-40)))
    assert r[0]["due"] == d(-10).isoformat()


def test_warn_window_boundaries():
    assert run(acct(last_seen_at=d(14 - 730)))[0]["action"] == "warn"
    assert run(acct(last_seen_at=d(15 - 730))) == []
    r = run(acct(last_seen_at=d(-730)))
    assert [x["action"] for x in r] == ["delete"]


def test_member_closed_no_warn_but_delete():
    assert run(acct(closed_at=d(-30 + 5), closed_by="member")) == []
    assert run(acct(closed_at=d(-30), closed_by="member"))[0]["action"] == "delete"
    assert run(acct(closed_at=d(-30 + 5), closed_by="staff"))[0]["action"] == "warn"


def test_unpaid_invoices():
    assert run(acct(last_seen_at=d(-730), unpaid_invoices=2))[0]["action"] == "anonymise"
    assert run(acct(last_seen_at=d(-730), unpaid_invoices=True))[0]["action"] == "anonymise"
    assert run(acct(last_seen_at=d(-730), unpaid_invoices=None))[0]["action"] == "delete"
    assert run(acct(last_seen_at=d(-725), unpaid_invoices=3))[0]["action"] == "warn"
    assert run(acct(last_seen_at=d(-730), unpaid_invoices=0))[0]["action"] == "delete"


def test_litigation_hold():
    assert run(acct(last_seen_at=d(-730), litigation_hold=True)) == []
    assert run(acct(last_seen_at=d(-730), unpaid_invoices=1, litigation_hold=True)) == []
    assert run(acct(last_seen_at=d(-725), litigation_hold=True)) == []


def test_staff_email():
    old = d(-730)
    assert run(acct(email="A@Tidewater-Klatring.NO", last_seen_at=old)) == []
    assert run(acct(email="a@tidewater-klatring.no  \n", last_seen_at=old)) == []
    assert run(acct(email="x@tidewater-klatring.no.evil.com", last_seen_at=old))[0]["action"] == "delete"
    assert run(acct(email=None, last_seen_at=old))[0]["action"] == "delete"


def test_no_email_and_exact_keys():
    r = run(acct(email="secret@example.com", last_seen_at=d(-730)),
            acct("a2", email="other@example.com", last_seen_at=d(-725)))
    assert "secret@example.com" not in repr(r) and "other@example.com" not in repr(r)
    for x in r:
        assert set(x) == {"account_id", "action", "due", "approved_by"}


def test_approved_by():
    r = run(acct("a", last_seen_at=d(-730)),
            acct("b", last_seen_at=d(-730), unpaid_invoices=1),
            acct("c", last_seen_at=d(-725)))
    assert [x["approved_by"] for x in r] == [DPO, DPO, None]


def _cap_set():
    accts = []
    for i in range(100):
        accts.append(acct(f"c{i:03d}", last_seen_at=None, closed_at=d(-30),
                          unpaid_invoices=i % 2))
    for i in range(150):
        accts.append(acct(f"i{i:03d}", last_seen_at=d(-730 - i),
                          unpaid_invoices=1 if i % 3 == 0 else 0))
    for i in range(5):
        accts.append(acct(f"w{i}", last_seen_at=d(5 - 730)))
    return accts


def test_cap():
    accts = _cap_set()
    r = plan_purge(accts, TODAY)
    purges = [x for x in r if x["action"] != "warn"]
    warns = [x for x in r if x["action"] == "warn"]
    assert len(purges) == 200 and len(warns) == 5
    ids = {x["account_id"] for x in purges}
    assert all(f"c{i:03d}" in ids for i in range(100))
    # kept inactive: earliest due first, i = 149..50
    assert all(f"i{i:03d}" in ids for i in range(50, 150))
    assert not any(f"i{i:03d}" in ids for i in range(50))
    # deferred get no warn
    assert not any(x["account_id"].startswith("i") and x["action"] == "warn" for x in r)
    assert {x["action"] for x in purges} == {"delete", "anonymise"}


def test_sorted_with_shuffle():
    accts = _cap_set()
    random.Random(1).shuffle(accts)
    r = plan_purge(accts, TODAY)
    ids = [x["account_id"] for x in r]
    assert ids == sorted(ids)
    assert len([x for x in r if x["action"] != "warn"]) == 200


def test_missing_last_seen():
    assert run(acct(last_seen_at=None)) == []
    r = run(acct(last_seen_at=None, closed_at=d(-31)))
    assert r[0]["action"] == "delete" and r[0]["due"] == d(-1).isoformat()


def test_future_closed_at():
    assert run(acct(last_seen_at=None, closed_at=d(1))) == []
    assert run(acct(last_seen_at=None, closed_at=d(-30 + 14)))[0]["action"] == "warn"
    assert run(acct(last_seen_at=None, closed_at=d(-30 + 15))) == []
    assert run(acct(last_seen_at=None, closed_at=d(-30 + 14), closed_by="member")) == []


def test_no_mutation_and_empty():
    accts = [acct("b", last_seen_at=d(-730)), acct("a", tenant="x")]
    snap = copy.deepcopy(accts)
    plan_purge(accts, TODAY)
    assert accts == snap
    assert plan_purge([], TODAY) == []


def test_tenant_ignored_and_json():
    a = acct(last_seen_at=d(-730), tenant="t1")
    b = acct("a2", last_seen_at=d(-730))
    assert run(a)[0]["action"] == "delete" and run(b)[0]["action"] == "delete"
    r = run(a)
    assert isinstance(r[0]["due"], str)
    json.dumps(r)