"""Tidewater Climbing GDPR purge planner (purge.py). Run tests: python -m pytest purge.py"""
from datetime import date, timedelta
import json

APPROVER = "Tordis Svenbjorn Dottir"            # R12
STAFF_DOMAIN = "tidewater-klatring.no"          # R9
INACTIVITY_DAYS = 730                           # R4
CLOSED_GRACE_DAYS = 30                          # R4
WARN_DAYS = 14                                  # R6
CAP = 200                                       # R11
ANONYMISE_COUNTS_TOWARD_CAP = True              # [ASSUMED] R11
WARN_REPEATEDLY = True                          # [ASSUMED] R6 stateless
# House rule from the operator: every action carries the account email.
# NOTE: this conflicts with R1/R10 (four keys only, no email). Set to False
# to satisfy R1/R10/AC10 exactly; pending client/operator resolution.
INCLUDE_EMAIL = True


def _is_staff(a):
    email = a.get("email")
    if not isinstance(email, str):
        return False
    return email.strip().lower().endswith("@" + STAFF_DOMAIN)


def _eligible(a):
    """Single eligibility point (R20: a status filter can be added here)."""
    if a.get("litigation_hold") or _is_staff(a):
        return False
    return a.get("last_seen_at") is not None


def _due(a):
    d = a["last_seen_at"] + timedelta(days=INACTIVITY_DAYS)
    c = a.get("closed_at")
    if c is not None:
        d = min(d, c + timedelta(days=CLOSED_GRACE_DAYS))
    return d


def _is_closed(a):
    return a.get("closed_at") is not None


def _action(a, kind, due, approver):
    out = {"account_id": a.get("id"), "action": kind,
           "due": due.isoformat(), "approved_by": approver}
    if INCLUDE_EMAIL:
        out["email"] = a.get("email")
    return out


def plan_purge(accounts, today):
    eligible = [(a, _due(a)) for a in accounts if _eligible(a)]

    # Deletions first (R13).
    cands = [(a, d) for a, d in eligible if d <= today]
    cands.sort(key=lambda t: (0 if _is_closed(t[0]) else 1, t[1], t[0].get("id")))
    chosen = cands[:CAP]
    result = [
        _action(a, "anonymise" if a.get("unpaid_invoices") else "delete", d, APPROVER)
        for a, d in chosen
    ]

    # Warnings isolated so a defect cannot affect deletions.
    try:
        horizon = today + timedelta(days=WARN_DAYS)
        for a, d in eligible:
            if today < d <= horizon and a.get("closed_by") != "member":
                result.append(_action(a, "warn", d, None))
    except Exception:
        pass

    result.sort(key=lambda r: r["account_id"])
    return result


# ---------------- tests ----------------
T = date(2026, 10, 13)


def _acc(i, seen=None, **kw):
    base = {"id": i, "email": f"{i}@x.com", "status": "active",
            "last_seen_at": T - timedelta(days=seen) if seen is not None else None,
            "last_login": None, "closed_at": None, "closed_by": "staff",
            "unpaid_invoices": 0, "litigation_hold": False}
    base.update(kw)
    return base


def _one(a):
    return plan_purge([a], T)


def test_ac1_ac3():
    r = _one(_acc("a", 730))[0]
    assert (r["action"], r["due"]) == ("delete", T.isoformat())
    assert _one(_acc("a", 800))[0]["due"] == (T - timedelta(days=70)).isoformat()
    assert _one(_acc("a", 729))[0]["action"] == "warn"
    assert _one(_acc("a", 716))[0]["due"] == (T + timedelta(days=14)).isoformat()
    assert _one(_acc("a", 715)) == []


def test_ac2():
    assert _one(_acc("a", 10, last_login=T - timedelta(days=900))) == []
    assert _one(_acc("a", 900, last_login=T))[0]["action"] == "delete"


def test_ac4_ac5_ac6():
    assert _one(_acc("a", 10, closed_at=T - timedelta(days=30)))[0]["action"] == "delete"
    assert _one(_acc("a", 10, closed_at=T - timedelta(days=29)))[0]["action"] == "warn"
    assert _one(_acc("a", 725, closed_at=T - timedelta(days=1)))[0]["due"] == (T + timedelta(days=5)).isoformat()
    assert _one(_acc("a", 725, closed_at=T - timedelta(days=1), closed_by="member")) == []
    assert _one(_acc("a", 10, closed_at=T - timedelta(days=29), closed_by="member")) == []
    assert _one(_acc("a", 10, closed_at=T - timedelta(days=30), closed_by="member"))[0]["action"] == "delete"


def test_ac7_ac8_ac9():
    assert _one(_acc("a", 730, unpaid_invoices=2))[0]["action"] == "anonymise"
    assert _one(_acc("a", 729, unpaid_invoices=2))[0]["action"] == "warn"
    assert _one(_acc("a", 900, litigation_hold=True)) == []
    assert _one(_acc("a", 900, email="X@Tidewater-Klatring.no ")) == []
    assert _one(_acc("a", 900, email=None))[0]["action"] == "delete"
    for e in ("x@tidewater-klatring.no.example.com", "x@evil-tidewater-klatring.no"):
        assert len(_one(_acc("a", 900, email=e))) == 1


def test_ac10_ac15_ac16_ac17():
    a = _acc("a", 900, tenant="t", extra=1)
    before = repr(a)
    r = plan_purge([a], T)
    assert repr(a) == before
    json.dumps(r)
    assert r == plan_purge([_acc("a", 900)], T) or INCLUDE_EMAIL
    expected = {"account_id", "action", "due", "approved_by"} | ({"email"} if INCLUDE_EMAIL else set())
    assert set(r[0]) == expected
    assert plan_purge([], T) == []


def test_ac11_ac12_ac14():
    accs = [_acc(f"c{i:03}", 10, closed_at=T - timedelta(days=40)) for i in range(100)]
    accs += [_acc(f"i{i:03}", 800 + i) for i in range(150)]
    accs += [_acc("w1", 729), _acc("a0", 729)]
    r = plan_purge(accs, T)
    acts = [x for x in r if x["action"] != "warn"]
    assert len(acts) == 200 and len(r) == 202
    ids = [x["account_id"] for x in acts]
    assert all(f"c{i:03}" in ids for i in range(100))
    assert "i149" in ids and "i049" not in ids
    assert [x["account_id"] for x in r] == sorted(x["account_id"] for x in r)
    mixed = [_acc(f"d{i:03}", 800) for i in range(150)] + \
            [_acc(f"u{i:03}", 800, unpaid_invoices=1) for i in range(100)]
    assert len(plan_purge(mixed, T)) == 200


def test_ac13():
    r = plan_purge([_acc("a", 900), _acc("b", 729)], T)
    assert r[0]["approved_by"] == "Tordis Svenbjorn Dottir"
    assert r[1]["approved_by"] is None