"""Purge planner (R1-R16), standard library only.

Tests are embedded at the bottom as pytest functions (run: pytest purge.py).
They were NOT executed: this agent has no tools, so no test results exist.

Conflict: the house rule says every action dict also carries `email`, but
R1/R10 say exactly four keys and never email. The house rule wins here, so
the output has five keys. Set INCLUDE_EMAIL = False to restore the strict
R1/R10 shape (the tests follow the flag).

Assumptions and ambiguities:
- DELETE_CAP (R11) applies to "delete" only. Anonymise is uncapped.
- Cap order: closed first, then earliest due, then id. Cut accounts get no action.
- last_seen_at None and closed_at None: no action. last_login is never used.
- closed_by "member" suppresses warn only when closed_at is set.
- Duplicate ids are not deduped. Input is not mutated.
- Staff email check: strip + casefold, endswith the domain.
- Unpaid invoices: any truthy value (bool, int, non-empty list).
- Output sorted by account_id, assuming ids are mutually comparable.
"""
import unicodedata
from datetime import date, timedelta

INCLUDE_EMAIL = True  # house rule; see module docstring
DELETE_CAP = 200
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = unicodedata.normalize("NFC", "DPO Þórdís Sveinbjörnsdóttir")


def _action(a, kind, due, approver):
    d = {"account_id": a["id"], "action": kind, "due": due.isoformat(),
         "approved_by": approver}
    if INCLUDE_EMAIL:
        d["email"] = a.get("email")
    return d


def plan_purge(accounts, today):
    """R1: return the list of purge actions for `accounts` as of `today`."""
    deletes, others = [], []
    for a in accounts:
        email = (a.get("email") or "").strip().casefold()
        if email.endswith(STAFF_DOMAIN) or a.get("litigation_hold"):  # R9, R8
            continue
        seen, closed = a.get("last_seen_at"), a.get("closed_at")  # R3
        dues = []
        if seen is not None:
            dues.append(seen + timedelta(days=INACTIVITY_DAYS))
        if closed is not None:
            dues.append(closed + timedelta(days=CLOSED_DAYS))
        if not dues:
            continue
        due = min(dues)  # R4
        if due <= today:
            kind = "anonymise" if a.get("unpaid_invoices") else "delete"  # R7
            act = _action(a, kind, due, APPROVER)
            if kind == "delete":
                deletes.append(((closed is None, due, a["id"]), act))
            else:
                others.append(act)
        elif due <= today + timedelta(days=WARN_DAYS):  # R5
            if closed is not None and a.get("closed_by") == "member":  # R6
                continue
            others.append(_action(a, "warn", due, None))
    deletes.sort(key=lambda t: t[0])  # R11
    result = others + [act for _, act in deletes[:DELETE_CAP]]
    result.sort(key=lambda d: d["account_id"])  # R14
    return result


# ---------------------------- tests ----------------------------
T = date(2026, 10, 13)
D = timedelta


def acc(id="a", **kw):
    base = dict(id=id, email=f"{id}@example.com", status="active",
                last_seen_at=T, last_login=T, closed_at=None, closed_by=None,
                unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


def one(**kw):
    r = plan_purge([acc(**kw)], T)
    return r[0] if r else None


def test_r1_r15_shape_and_iso_due():
    r = one(last_seen_at=T - D(730))
    keys = {"account_id", "action", "due", "approved_by"}
    assert set(r) == keys | ({"email"} if INCLUDE_EMAIL else set())
    assert r["due"] == T.isoformat() and r["action"] == "delete"


def test_r3_boundaries_730_729():
    assert one(last_seen_at=T - D(730))["action"] == "delete"
    assert one(last_seen_at=T - D(729))["action"] == "warn"


def test_r3_last_login_ignored():
    assert one(last_seen_at=T, last_login=T - D(5000)) is None
    assert one(last_seen_at=T - D(800), last_login=T)["action"] == "delete"


def test_r4_closed_30_days_and_earlier_wins():
    assert one(closed_at=T - D(30))["action"] == "delete"
    assert one(closed_at=T - D(29), closed_by="staff")["action"] == "warn"
    r = one(last_seen_at=T - D(740), closed_at=T - D(1))  # inactivity sooner
    assert r["due"] == (T - D(10)).isoformat()
    r = one(last_seen_at=T - D(100), closed_at=T - D(40))  # closed sooner
    assert r["due"] == (T - D(10)).isoformat() and r["action"] == "delete"


def test_r5_warn_window():
    assert one(last_seen_at=T - D(730) + D(14))["action"] == "warn"
    assert one(last_seen_at=T - D(730) + D(15)) is None
    assert one(last_seen_at=T - D(730) + D(1))["approved_by"] is None


def test_r6_member_closed_no_warn():
    assert one(closed_at=T - D(20), closed_by="member") is None
    assert one(closed_at=T - D(20), closed_by="staff")["action"] == "warn"
    assert one(closed_at=T - D(30), closed_by="member")["action"] == "delete"
    # member with no closed_at: no special effect
    assert one(last_seen_at=T - D(725), closed_by="member")["action"] == "warn"


def test_r7_unpaid_variants():
    for v in (True, 2, ["inv1"]):
        assert one(last_seen_at=T - D(730), unpaid_invoices=v)["action"] == "anonymise"
    for v in (False, 0, []):
        assert one(last_seen_at=T - D(730), unpaid_invoices=v)["action"] == "delete"
    assert one(last_seen_at=T - D(725), unpaid_invoices=1)["action"] == "warn"


def test_r8_litigation_hold():
    assert one(last_seen_at=T - D(900), litigation_hold=True) is None
    assert one(last_seen_at=T - D(725), litigation_hold=1) is None


def test_r9_staff_case_insensitive():
    for e in ("x@tidewater-klatring.no", "  X@Tidewater-Klatring.NO \n"):
        assert one(email=e, last_seen_at=T - D(900)) is None
    assert one(email="x@tidewater-klatring.no.evil.com",
               last_seen_at=T - D(900)) is not None


def test_r10_email_handling():
    r = one(last_seen_at=T - D(900), email="secret@example.com")
    assert ("email" in r) == INCLUDE_EMAIL
    if INCLUDE_EMAIL:
        assert r["email"] == "secret@example.com"
    assert "secret" not in str({k: v for k, v in r.items() if k != "email"})


def test_r11_cap_ordering_and_r13():
    accs = [acc(f"c{i:03}", last_seen_at=T, closed_at=T - D(31)) for i in range(50)]
    accs += [acc(f"i{i:03}", last_seen_at=T - D(731 + i % 5)) for i in range(160)]
    accs.append(acc("w", last_seen_at=T - D(725)))
    r = plan_purge(accs, T)
    dels = [x for x in r if x["action"] == "delete"]
    assert len(dels) == DELETE_CAP == 200
    ids = {x["account_id"] for x in dels}
    assert all(f"c{i:03}" in ids for i in range(50))  # closed first
    assert sum(i.startswith("i") for i in ids) == 150
    # cut ones are the latest due (smallest overage); no action for them
    cut = [x for x in accs if x["id"].startswith("i") and x["id"] not in ids]
    assert len(cut) == 10
    assert all(x["last_seen_at"] >= T - D(731) for x in cut)
    assert all(x["account_id"] not in {c["id"] for c in cut} for x in r)
    assert any(x["action"] == "warn" for x in r)  # warns unaffected


def test_r11_anonymise_not_capped():
    accs = [acc(f"u{i}", last_seen_at=T - D(800), unpaid_invoices=1)
            for i in range(250)]
    accs += [acc(f"d{i}", last_seen_at=T - D(800)) for i in range(205)]
    r = plan_purge(accs, T)
    assert sum(x["action"] == "anonymise" for x in r) == 250
    assert sum(x["action"] == "delete" for x in r) == 200


def test_r12_approver_exact():
    exp = "DPO \u00de\u00f3rd\u00eds".replace(" \u00de", " \u00de")  # sanity
    assert APPROVER == unicodedata.normalize("NFC", APPROVER)
    assert APPROVER == "DPO Þórdís Sveinbjörnsdóttir"
    assert one(last_seen_at=T - D(800))["approved_by"] == APPROVER
    assert one(last_seen_at=T - D(800), unpaid_invoices=1)["approved_by"] == APPROVER


def test_r14_sorted():
    r = plan_purge([acc("z", last_seen_at=T - D(800)), acc("b", last_seen_at=T - D(725)),
                    acc("m", last_seen_at=T - D(900))], T)
    assert [x["account_id"] for x in r] == ["b", "m", "z"]


def test_r15_overdue_due_is_effective_due():
    assert one(last_seen_at=T - D(1000))["due"] == (T - D(270)).isoformat()


def test_r16_tenant_ignored():
    assert one(last_seen_at=T - D(800), tenant="x")["action"] == "delete"
    assert one(last_seen_at=T - D(800))["action"] == "delete"


def test_none_dates():
    assert one(last_seen_at=None) is None
    r = one(last_seen_at=None, closed_at=T - D(30))
    assert r["action"] == "delete"


def test_input_not_mutated():
    import copy
    accs = [acc("a", last_seen_at=T - D(800)), acc("b", unpaid_invoices=["x"])]
    before = copy.deepcopy(accs)
    plan_purge(accs, T)
    assert accs == before


def test_one_action_per_account():
    r = plan_purge([acc("a", last_seen_at=T - D(800), closed_at=T - D(40))], T)
    assert len(r) == 1