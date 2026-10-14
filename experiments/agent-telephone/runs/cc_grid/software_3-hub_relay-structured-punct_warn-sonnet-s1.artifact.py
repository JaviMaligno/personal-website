"""Tidewater Climbing GDPR member-account purge planner.

Note: the house rule asking for `email` on every action dict conflicts with
R1/R9 (exactly four keys, never include the email). The explicit client
requirements are followed here; the email is never emitted. Confirm with the
client before changing this.

Tests are included at the bottom (python purge.py or python -m unittest purge).
They were not executed in this environment because no tools were available.
"""
import datetime as _dt
import unittest

MAX_CAP_ACTIONS = 200
APPROVER = "Þórdís Sveinbjörnsdóttir"
_STAFF_SUFFIX = "@tidewater-klatring.no"
_INACTIVITY_DAYS = 730
_CLOSURE_DAYS = 30
_WARN_DAYS = 14


def _counts_toward_cap(action):
    # R17: delete and anonymise both count. If only deletes count, change to
    # `return action == "delete"`.
    return action in ("delete", "anonymise")


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(_STAFF_SUFFIX)


def _due_date(acc):
    candidates = []
    seen = acc.get("last_seen_at")
    if seen is not None:
        candidates.append(seen + _dt.timedelta(days=_INACTIVITY_DAYS))
    closed = acc.get("closed_at")
    if closed is not None:
        candidates.append(closed + _dt.timedelta(days=_CLOSURE_DAYS))
    return min(candidates) if candidates else None


def _action(acc, kind, due):
    return {
        "account_id": acc["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": APPROVER if kind != "warn" else None,
    }


def plan_purge(accounts, today):
    """Return a list of purge actions for the given accounts as of `today`."""
    heavy = []  # (tier, due, id, action dict) for delete/anonymise
    warns = []
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        due = _due_date(acc)
        if due is None:
            continue
        closed = acc.get("closed_at") is not None
        if due <= today:
            kind = "anonymise" if acc.get("unpaid_invoices") else "delete"
            heavy.append((0 if closed else 1, due, acc["id"], _action(acc, kind, due)))
        elif due <= today + _dt.timedelta(days=_WARN_DAYS):
            if closed and acc.get("closed_by") == "member":
                continue
            warns.append(_action(acc, "warn", due))

    heavy.sort(key=lambda t: t[:3])
    selected = []
    count = 0
    for _, _, _, act in heavy:
        if _counts_toward_cap(act["action"]):
            if count >= MAX_CAP_ACTIONS:
                continue
            count += 1
        selected.append(act)

    result = selected + warns
    result.sort(key=lambda a: a["account_id"])
    return result


# ----------------------------- tests -----------------------------

TODAY = _dt.date(2026, 10, 13)
D = _dt.timedelta


def _acc(id=1, **kw):
    base = dict(id=id, email="m@example.com", status="active",
                last_seen_at=TODAY - D(1), last_login=None, closed_at=None,
                closed_by=None, unpaid_invoices=0, litigation_hold=False)
    base.update(kw)
    return base


def _one(**kw):
    r = plan_purge([_acc(**kw)], TODAY)
    return r[0] if r else None


class PurgeTests(unittest.TestCase):
    def test_inactivity_boundaries(self):
        self.assertEqual(_one(last_seen_at=TODAY - D(730))["action"], "delete")
        self.assertEqual(_one(last_seen_at=TODAY - D(729))["action"], "warn")
        self.assertEqual(_one(last_seen_at=TODAY - D(716))["action"], "warn")  # +14
        self.assertIsNone(_one(last_seen_at=TODAY - D(715)))  # +15
        self.assertEqual(_one(last_seen_at=TODAY - D(1000))["action"], "delete")

    def test_closed_boundaries_and_min(self):
        self.assertEqual(_one(closed_at=TODAY - D(30), closed_by="staff")["action"], "delete")
        self.assertEqual(_one(closed_at=TODAY - D(29), closed_by="staff")["action"], "warn")
        a = _one(closed_at=TODAY - D(30), last_seen_at=TODAY - D(10))
        self.assertEqual(a["action"], "delete")
        a = _one(closed_at=TODAY, last_seen_at=TODAY - D(729), closed_by="staff")
        self.assertEqual(a["due"], (TODAY + D(1)).isoformat())
        self.assertEqual(_one(closed_at=TODAY + D(100), last_seen_at=TODAY - D(730))["action"], "delete")

    def test_member_vs_staff_closed_warn(self):
        self.assertIsNone(_one(closed_at=TODAY - D(20), closed_by="member"))
        self.assertEqual(_one(closed_at=TODAY - D(20), closed_by="staff")["action"], "warn")
        self.assertEqual(_one(closed_by="member", last_seen_at=TODAY - D(729))["action"], "warn")

    def test_unpaid(self):
        self.assertEqual(_one(last_seen_at=TODAY - D(800), unpaid_invoices=2)["action"], "anonymise")
        self.assertEqual(_one(last_seen_at=TODAY - D(800), unpaid_invoices=["x"])["action"], "anonymise")
        self.assertEqual(_one(last_seen_at=TODAY - D(729), unpaid_invoices=2)["action"], "warn")

    def test_exclusions(self):
        old = TODAY - D(900)
        self.assertIsNone(_one(last_seen_at=old, litigation_hold=True))
        for e in ["a@tidewater-klatring.no", "  A@Tidewater-Klatring.NO ", "b@TIDEWATER-KLATRING.no"]:
            self.assertIsNone(_one(last_seen_at=old, email=e))
        for e in ["a@sub.tidewater-klatring.no", "a@tidewater-klatring.no.evil.com",
                  "a@xtidewater-klatring.no", "tidewater-klatring.no", None, ""]:
            self.assertEqual(_one(last_seen_at=old, email=e)["action"], "delete")

    def test_output_shape(self):
        a = _one(last_seen_at=TODAY - D(800), email="secret@example.com")
        self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
        self.assertNotIn("secret", repr(a))
        self.assertIsInstance(a["due"], str)
        import json
        json.dumps(plan_purge([_acc(last_seen_at=TODAY - D(800))], TODAY))

    def test_approver(self):
        self.assertEqual(_one(last_seen_at=TODAY - D(800))["approved_by"], "Þórdís Sveinbjörnsdóttir")
        self.assertEqual(_one(last_seen_at=TODAY - D(800), unpaid_invoices=1)["approved_by"],
                         "Þórdís Sveinbjörnsdóttir")
        self.assertIsNone(_one(last_seen_at=TODAY - D(729))["approved_by"])

    def test_ignored_fields(self):
        self.assertIsNone(_one(last_seen_at=TODAY - D(1), last_login=TODAY - D(2000)))
        self.assertIsNone(_one(last_seen_at=None, last_login=TODAY - D(2000)))
        self.assertEqual(_one(last_seen_at=None, closed_at=TODAY - D(40))["action"], "delete")
        self.assertEqual(_one(tenant="x", last_seen_at=TODAY - D(800))["action"], "delete")
        self.assertEqual(_one(status="closed", last_seen_at=TODAY - D(800))["action"], "delete")
        self.assertIsNone(_one(status="closed"))

    def test_cap(self):
        accs = []
        for i in range(120):  # closed, various due dates
            accs.append(_acc(id=1000 + i, closed_at=TODAY - D(30 + i % 10),
                             unpaid_invoices=i % 2, closed_by="staff"))
        for i in range(130):  # inactivity only
            accs.append(_acc(id=i, last_seen_at=TODAY - D(730 + i)))
        warn = [_acc(id=5000 + i, last_seen_at=TODAY - D(729)) for i in range(5)]
        res = plan_purge(accs + warn, TODAY)
        heavy = [a for a in res if a["action"] != "warn"]
        self.assertEqual(len(heavy), 200)
        self.assertEqual(len([a for a in res if a["action"] == "warn"]), 5)
        ids = {a["account_id"] for a in heavy}
        self.assertTrue(all(1000 + i in ids for i in range(120)))
        # 80 inactivity slots go to the earliest due = largest inactivity = highest i
        self.assertEqual({i for i in ids if i < 1000}, set(range(50, 130)))
        self.assertEqual([a["account_id"] for a in res], sorted(a["account_id"] for a in res))

    def test_cap_tiebreak_by_id(self):
        accs = [_acc(id=i, last_seen_at=TODAY - D(800)) for i in range(250, 0, -1)]
        res = plan_purge(accs, TODAY)
        self.assertEqual([a["account_id"] for a in res], list(range(1, 201)))

    def test_excluded_before_cap(self):
        accs = [_acc(id=i, last_seen_at=TODAY - D(900), litigation_hold=True) for i in range(300)]
        accs.append(_acc(id=999, last_seen_at=TODAY - D(731)))
        self.assertEqual([a["account_id"] for a in plan_purge(accs, TODAY)], [999])

    def test_no_mutation(self):
        import copy
        accs = [_acc(id=2, last_seen_at=TODAY - D(800)), _acc(id=1, last_seen_at=TODAY - D(729))]
        snap = copy.deepcopy(accs)
        plan_purge(accs, TODAY)
        self.assertEqual(accs, snap)


if __name__ == "__main__":
    unittest.main()