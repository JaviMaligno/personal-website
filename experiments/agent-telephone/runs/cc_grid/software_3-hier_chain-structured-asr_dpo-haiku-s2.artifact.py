# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-mqjfr5v2/purge_plan.py
"""Daily retention purge planner for Tidewater Climbing.

Open points for client confirmation (implemented as stated):
- OP-a/OP-b: anonymise actions are not counted against the delete cap.
- OP-c: accounts over the cap get no action and reappear next run (stateless).
- OP-d: a warned account with unpaid invoices still gets a warn.
- R17: staff suffix match is case-insensitive and ignores surrounding whitespace.
- R18: cap tie-break after due date is account_id ascending.
- R22: last_seen_at None or missing raises ValueError naming the account id.
- R23: status has no effect on any rule.
- R24: boundaries as specified; at most one action per account per run.
- R27: duplicate account ids raise ValueError (architect choice).
- R28: any closed account (any closed_by value) is treated as closed for cap ordering.
"""

from datetime import date, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVE_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due_date(account):
    last_seen = account.get("last_seen_at")
    if last_seen is None:
        raise ValueError(f"account {account.get('id')!r} has no last_seen_at")
    due = last_seen + timedelta(days=INACTIVE_DAYS)
    closed_at = account.get("closed_at")
    if closed_at is not None:
        closed_due = closed_at + timedelta(days=CLOSED_GRACE_DAYS)
        if closed_due < due:
            due = closed_due
    return due


def _action(account_id, action, due):
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
    }


def plan_purge(accounts, today):
    # Step 1: validate every account before producing any output.
    seen = set()
    prepared = []
    for account in accounts:
        account_id = account.get("id")
        if account_id in seen:
            raise ValueError(f"duplicate account id {account_id!r}")
        seen.add(account_id)
        prepared.append((account, _due_date(account)))

    # Step 2: classify each account. Staff and litigation-hold accounts are skipped.
    actions = []
    deletions = []
    warn_limit = today + timedelta(days=WARN_WINDOW_DAYS)
    for account, due in prepared:
        if _is_staff(account.get("email")) or account.get("litigation_hold"):
            continue
        account_id = account.get("id")
        if due <= today:
            if account.get("unpaid_invoices"):
                actions.append(_action(account_id, "anonymise", due))
            else:
                deletions.append((account, due))
        elif due <= warn_limit:
            if account.get("closed_by") != "member":
                actions.append(_action(account_id, "warn", due))

    # Step 3: apply the delete cap. Closed accounts first, then due date, then account_id.
    deletions.sort(
        key=lambda item: (item[0].get("closed_at") is None, item[1], item[0].get("id"))
    )
    for account, due in deletions[:DELETE_CAP]:
        actions.append(_action(account.get("id"), "delete", due))

    # Step 4: deterministic output order.
    actions.sort(key=lambda a: a["account_id"])
    return actions

# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-mqjfr5v2/test_purge_plan.py
# Run from the directory containing purge_plan.py: python3 -m unittest test_purge_plan
# Note: these tests have NOT been executed in this session.
import copy
import random
import unittest
from datetime import date, timedelta

from purge_plan import APPROVER, plan_purge

T = date(2026, 10, 13)


def d(offset):
    return T + timedelta(days=offset)


def ls(offset):
    """last_seen_at such that the R2 due date is T + offset."""
    return d(offset - 730)


def acct(aid, **kw):
    base = {
        "id": aid,
        "email": f"{aid}@example.com",
        "status": "active",
        "last_seen_at": d(-100),
        "last_login": None,
        "closed_at": None,
        "closed_by": None,
        "unpaid_invoices": False,
        "litigation_hold": False,
    }
    base.update(kw)
    return base


def by_id(actions):
    return {a["account_id"]: a for a in actions}


class PurgePlanTests(unittest.TestCase):
    def test_r2_due_today_is_delete_one_day_later_is_not(self):
        out = by_id(plan_purge([acct("a", last_seen_at=ls(0)), acct("b", last_seen_at=ls(1))], T))
        self.assertEqual(out["a"]["action"], "delete")
        self.assertEqual(out["b"]["action"], "warn")  # due T+1 is not yet due

    def test_r3_closed_date_used_when_earlier(self):
        a = acct("a", last_seen_at=ls(200), closed_at=d(-25), closed_by="staff")
        out = by_id(plan_purge([a], T))
        self.assertEqual(
            out["a"],
            {"account_id": "a", "action": "warn", "due": "2026-10-18", "approved_by": None},
        )

    def test_r3_r2_date_used_when_closed_date_later(self):
        a = acct("a", last_seen_at=ls(1), closed_at=d(0), closed_by="staff")
        out = plan_purge([a], T)
        self.assertEqual(out[0]["due"], "2026-10-14")

    def test_r4_due_today_is_delete(self):
        out = plan_purge([acct("a", last_seen_at=ls(0))], T)
        self.assertEqual(out, [{"account_id": "a", "action": "delete", "due": "2026-10-13", "approved_by": APPROVER}])

    def test_r5_warn_window_boundary(self):
        out = by_id(plan_purge([acct("w14", last_seen_at=ls(14)), acct("w15", last_seen_at=ls(15))], T))
        self.assertEqual(out["w14"]["action"], "warn")
        self.assertNotIn("w15", out)

    def test_r6_member_closed_no_warn_staff_closed_warn(self):
        m = acct("m", last_seen_at=ls(200), closed_at=d(-25), closed_by="member")
        s = acct("s", last_seen_at=ls(200), closed_at=d(-25), closed_by="staff")
        out = by_id(plan_purge([m, s], T))
        self.assertNotIn("m", out)
        self.assertEqual(out["s"]["action"], "warn")

    def test_r7_unpaid_due_is_anonymise(self):
        out = plan_purge([acct("u", last_seen_at=ls(0), unpaid_invoices=True)], T)
        self.assertEqual(
            out,
            [{"account_id": "u", "action": "anonymise", "due": "2026-10-13", "approved_by": APPROVER}],
        )

    def test_r8_litigation_hold_never_acts(self):
        accts = [
            acct("h1", last_seen_at=ls(0), litigation_hold=True),
            acct("h2", last_seen_at=ls(5), litigation_hold=True),
            acct("h3", last_seen_at=ls(0), unpaid_invoices=True, litigation_hold=True),
            acct("h4", last_seen_at=ls(0), closed_at=d(-40), closed_by="staff", litigation_hold=True),
        ]
        self.assertEqual(plan_purge(accts, T), [])

    def test_r8_litigation_hold_capped_account_gets_nothing(self):
        accts = [acct(f"n{i:03d}", last_seen_at=ls(0)) for i in range(201)]
        accts.append(acct("h5", last_seen_at=ls(0), litigation_hold=True))
        out = by_id(plan_purge(accts, T))
        self.assertNotIn("h5", out)
        self.assertNotIn("n200", out)  # over cap
        self.assertEqual(sum(1 for a in out.values() if a["action"] == "delete"), 200)

    def test_r9_staff_emails(self):
        accts = [
            acct("s1", email="x@TIDEWATER-KLATRING.NO", last_seen_at=ls(0)),
            acct("s2", email="x@tidewater-klatring.no", last_seen_at=ls(0)),
            acct("s3", email="x@tidewater-klatring.no.example.com", last_seen_at=ls(0)),
        ]
        out = by_id(plan_purge(accts, T))
        self.assertNotIn("s1", out)
        self.assertNotIn("s2", out)
        self.assertEqual(out["s3"]["action"], "delete")

    def test_r10_exact_keys_and_no_email_value(self):
        accts = [
            acct("a", last_seen_at=ls(0)),
            acct("b", last_seen_at=ls(3)),
            acct("c", last_seen_at=ls(0), unpaid_invoices=True),
        ]
        emails = {x["email"] for x in accts}
        out = plan_purge(accts, T)
        self.assertEqual(len(out), 3)
        for act in out:
            self.assertEqual(set(act), {"account_id", "action", "due", "approved_by"})
            for value in act.values():
                self.assertNotIn(value, emails)

    def test_r11_cap_closed_first_then_due_then_id(self):
        accts = [acct(f"c{j:03d}", closed_at=d(-30 - j), closed_by="member") for j in range(105)]
        accts += [acct(f"i{i:03d}", last_seen_at=ls(-i)) for i in range(100)]
        out = by_id(plan_purge(accts, T))
        deletes = [a for a in out.values() if a["action"] == "delete"]
        self.assertEqual(len(deletes), 200)
        for j in range(105):
            self.assertEqual(out[f"c{j:03d}"]["action"], "delete")
        for i in range(5):
            self.assertNotIn(f"i{i:03d}", out)  # latest due dates are excluded
        for i in range(5, 100):
            self.assertEqual(out[f"i{i:03d}"]["action"], "delete")

    def test_r12_approved_by_values(self):
        accts = [
            acct("del", last_seen_at=ls(0)),
            acct("ano", last_seen_at=ls(0), unpaid_invoices=True),
            acct("wrn", last_seen_at=ls(5)),
        ]
        out = by_id(plan_purge(accts, T))
        self.assertEqual(out["del"]["approved_by"], APPROVER)
        self.assertEqual(out["ano"]["approved_by"], APPROVER)
        self.assertIsNone(out["wrn"]["approved_by"])

    def test_r13_sorted_by_account_id_when_shuffled(self):
        accts = [acct(f"s{i:02d}", last_seen_at=ls(-i)) for i in range(20)]
        shuffled = accts[:]
        random.Random(7).shuffle(shuffled)
        ids = [a["account_id"] for a in plan_purge(shuffled, T)]
        self.assertEqual(ids, sorted(ids))

    def test_r14_due_is_iso_string(self):
        out = plan_purge([acct("a", last_seen_at=ls(0))], T)
        self.assertIsInstance(out[0]["due"], str)
        self.assertEqual(out[0]["due"], "2026-10-13")

    def test_r15_tenant_ignored(self):
        base = [acct("a", last_seen_at=ls(0)), acct("b", last_seen_at=ls(5))]
        expected = plan_purge(copy.deepcopy(base), T)
        for value in ("tidewater", None, 42):
            with_tenant = [dict(x, tenant=value) for x in base]
            self.assertEqual(plan_purge(with_tenant, T), expected)

    def test_r1_only_last_seen_counts(self):
        old_login = acct("ol", last_seen_at=d(-1), last_login=date(2000, 1, 1))
        recent_login = acct("rl", last_seen_at=ls(0), last_login=d(0))
        out = by_id(plan_purge([old_login, recent_login], T))
        self.assertNotIn("ol", out)
        self.assertEqual(out["rl"]["action"], "delete")

    def test_r17_staff_email_case_and_whitespace(self):
        out = plan_purge([acct("s", email="  Y@Tidewater-Klatring.NO  ", last_seen_at=ls(0))], T)
        self.assertEqual(out, [])

    def test_r18_cap_tie_break_by_account_id(self):
        accts = [acct(f"t{i:03d}", last_seen_at=ls(0)) for i in range(201)]
        out = by_id(plan_purge(accts, T))
        self.assertNotIn("t200", out)  # same due date, largest id is over cap
        self.assertEqual(out["t199"]["action"], "delete")

    def test_r19_anonymise_does_not_use_cap_slot(self):
        accts = [acct(f"t{i:03d}", last_seen_at=ls(0)) for i in range(201)]
        accts.append(acct("z", last_seen_at=ls(0), unpaid_invoices=True))
        out = by_id(plan_purge(accts, T))
        self.assertEqual(out["z"]["action"], "anonymise")
        self.assertEqual(sum(1 for a in out.values() if a["action"] == "delete"), 200)

    def test_r20_over_cap_accounts_absent(self):
        accts = [acct(f"t{i:03d}", last_seen_at=ls(0)) for i in range(201)]
        out = by_id(plan_purge(accts, T))
        self.assertNotIn("t200", out)
        self.assertEqual(len(out), 200)

    def test_r21_warn_window_with_unpaid_gets_warn(self):
        out = plan_purge([acct("w", last_seen_at=ls(5), unpaid_invoices=True)], T)
        self.assertEqual(out[0]["action"], "warn")
        self.assertIsNone(out[0]["approved_by"])

    def test_r22_missing_last_seen_raises_with_id(self):
        good = acct("ok", last_seen_at=ls(0))
        bad = acct("x9", last_seen_at=None)
        with self.assertRaises(ValueError) as ctx:
            plan_purge([good, bad], T)
        self.assertIn("x9", str(ctx.exception))

        missing = acct("x8")
        del missing["last_seen_at"]
        with self.assertRaises(ValueError) as ctx2:
            plan_purge([missing], T)
        self.assertIn("x8", str(ctx2.exception))

    def test_r23_status_has_no_effect(self):
        results = []
        for status in ("active", "closed", "suspended", None):
            results.append(plan_purge([
                acct("a", last_seen_at=ls(0), status=status),
                acct("b", last_seen_at=ls(5), status=status),
            ], T))
        for r in results[1:]:
            self.assertEqual(r, results[0])

    def test_r24_at_most_one_action_per_account(self):
        accts = [
            acct("p", last_seen_at=ls(0), closed_at=d(-40), closed_by="staff"),
            acct("q", last_seen_at=ls(5), closed_at=d(-25), closed_by="staff"),
            acct("r", last_seen_at=ls(0), unpaid_invoices=True, closed_at=d(-40)),
            acct("s", last_seen_at=ls(14), closed_at=d(-16), closed_by="staff"),
        ]
        out = plan_purge(accts, T)
        ids = [a["account_id"] for a in out]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(by_id(out)["p"]["action"], "delete")

    def test_r25_input_not_mutated(self):
        accts = [
            acct("a", last_seen_at=ls(0), closed_at=d(-25), closed_by="staff"),
            acct("b", last_seen_at=ls(5)),
        ]
        before = copy.deepcopy(accts)
        plan_purge(accts, T)
        self.assertEqual(accts, before)

    def test_r26_empty_input(self):
        self.assertEqual(plan_purge([], T), [])

    def test_r27_duplicate_id_raises(self):
        with self.assertRaises(ValueError) as ctx:
            plan_purge([acct("dup", last_seen_at=ls(0)), acct("dup", last_seen_at=ls(5))], T)
        self.assertIn("dup", str(ctx.exception))

    def test_r28_any_closed_counts_as_closed_for_cap(self):
        accts = [acct(f"i{i:03d}", last_seen_at=ls(-i)) for i in range(200)]
        accts.append(acct("sys", closed_at=d(-40), closed_by="system"))
        out = by_id(plan_purge(accts, T))
        self.assertEqual(out["sys"]["action"], "delete")
        self.assertNotIn("i000", out)  # latest-due inactive account is over cap
        self.assertEqual(sum(1 for a in out.values() if a["action"] == "delete"), 200)


if __name__ == "__main__":
    unittest.main()