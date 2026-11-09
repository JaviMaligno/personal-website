"""Tidewater Klatring GDPR clean-up planner.

Assumptions (for client confirmation):
- The cap (MAX_DELETES_PER_RUN = 200) applies to deletes only, not anonymise.
- The status field is ignored. The legacy tenant key is never read.
- approved_by is None for warnings.
- The cap is applied first, then output is sorted by id. Mixed-type ids sort by (type name, value).
- Deferred deletes are omitted, with no warn.
- The warn window is inclusive of day 14.
- The staff-email match is a case-insensitive suffix on the stripped email. A None or non-str email is treated as non-staff.
- unpaid_invoices is judged by truthiness (True or a nonzero count means anonymise).
- Missing last_seen_at uses the closed-based due only. If there is neither, the account is skipped.
- A future closed_at simply gives a future due.
- last_login is never used.
- closed_by other than "member" (including missing) allows a warn.

DEVIATION: the house rule says every action dict also carries the account's
`email`, so actions have five keys (account_id, action, due, approved_by,
email). The brief asked for four keys and no email. This must be confirmed
with the client, since it conflicts with their GDPR-minimisation intent.
Dropping the email means removing one line in _action and adjusting the tests.

Client questions:
- Confirm the cap excludes anonymise.
- What should status (e.g. already-deleted or suspended) mean?
- Should already-anonymised or deleted accounts be re-emitted each run? Nothing in the input marks them as processed, so they will be re-emitted daily.
- Should deferred deletes warn?
- Is the warn window inclusive of day 14?
- How should a missing or unusual closed_by be treated?
- What should a future closed_at do?
- Can closed_at be set while closed_by is None?
- Confirm the email-in-action house rule against the four-key brief.
"""
import copy
import datetime as dt
import json
import unittest

MAX_DELETES_PER_RUN = 200
APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14


def _idkey(x):
    return (type(x).__name__, x)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _due(a):
    cands = []
    seen = a.get("last_seen_at")
    if seen is not None:
        cands.append(seen + dt.timedelta(days=INACTIVITY_DAYS))
    closed = a.get("closed_at")
    if closed is not None:
        cands.append(closed + dt.timedelta(days=CLOSED_DAYS))
    return min(cands) if cands else None


def _action(a, action, due, approved):
    return {
        "account_id": a.get("id"),
        "action": action,
        "due": due.isoformat(),
        "approved_by": approved,
        "email": a.get("email"),
    }


def plan_purge(accounts, today):
    """Return the list of purge actions for `today`; inputs are not mutated."""
    out, deletes = [], []
    horizon = today + dt.timedelta(days=WARN_DAYS)
    for a in accounts:
        if a.get("litigation_hold") or _is_staff(a.get("email")):
            continue
        due = _due(a)
        if due is None:
            continue
        if due <= today:
            if a.get("unpaid_invoices"):
                out.append(_action(a, "anonymise", due, APPROVER))
            else:
                deletes.append((a, due))
        elif due <= horizon and a.get("closed_by") != "member":
            out.append(_action(a, "warn", due, None))
    deletes.sort(key=lambda t: (t[0].get("closed_at") is None, t[1], _idkey(t[0].get("id"))))
    for a, due in deletes[:MAX_DELETES_PER_RUN]:
        out.append(_action(a, "delete", due, APPROVER))
    out.sort(key=lambda x: _idkey(x["account_id"]))
    return out


# ---------------------------------------------------------------- tests
TODAY = dt.date(2026, 10, 13)


def D(n):
    return dt.timedelta(days=n)


def acct(i=1, seen=None, **kw):
    a = {"id": i, "email": f"u{i}@example.com", "status": "active",
         "last_seen_at": TODAY - D(10) if seen is None else seen,
         "last_login": TODAY, "closed_at": None, "closed_by": None,
         "unpaid_invoices": 0, "litigation_hold": False}
    a.update(kw)
    return a


class PurgeTests(unittest.TestCase):
    def one(self, a):
        return plan_purge([a], TODAY)

    def test_inactivity_boundary(self):
        r = self.one(acct(seen=TODAY - D(730)))
        self.assertEqual(r[0]["action"], "delete")
        r = self.one(acct(seen=TODAY - D(729)))
        self.assertEqual((r[0]["action"], r[0]["due"]),
                         ("warn", (TODAY + D(1)).isoformat()))

    def test_warn_window(self):
        self.assertEqual(self.one(acct(seen=TODAY - D(716)))[0]["action"], "warn")
        self.assertEqual(self.one(acct(seen=TODAY - D(715))), [])

    def test_closed(self):
        self.assertEqual(self.one(acct(closed_at=TODAY - D(30), closed_by="member"))[0]["action"], "delete")
        self.assertEqual(self.one(acct(closed_at=TODAY - D(29), closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(self.one(acct(closed_at=TODAY - D(29), closed_by="member")), [])

    def test_closed_due_used(self):
        r = self.one(acct(closed_at=TODAY - D(25), closed_by="staff"))
        self.assertEqual(r[0]["due"], (TODAY + D(5)).isoformat())

    def test_last_login_ignored(self):
        self.assertEqual(self.one(acct(seen=TODAY - D(800), last_login=TODAY))[0]["action"], "delete")

    def test_unpaid(self):
        for v, exp in ((True, "anonymise"), (3, "anonymise"), (0, "delete")):
            r = self.one(acct(seen=TODAY - D(800), unpaid_invoices=v))
            self.assertEqual(r[0]["action"], exp)
            self.assertEqual(r[0]["approved_by"], APPROVER)

    def test_holds_and_staff(self):
        self.assertEqual(self.one(acct(seen=TODAY - D(800), litigation_hold=True)), [])
        self.assertEqual(self.one(acct(seen=TODAY - D(725), litigation_hold=True)), [])
        self.assertEqual(self.one(acct(seen=TODAY - D(800), email="Foo@Tidewater-Klatring.NO")), [])
        self.assertEqual(len(self.one(acct(seen=TODAY - D(800), email=None))), 1)

    def test_shape(self):
        r = self.one(acct(seen=TODAY - D(800)))[0]
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by", "email"})
        self.assertIsInstance(r["due"], str)
        w = self.one(acct(seen=TODAY - D(729)))[0]
        self.assertIsNone(w["approved_by"])
        json.dumps(r)

    def test_cap(self):
        old = TODAY - D(900)
        accts = [acct(i, seen=old + D(i % 7)) for i in range(1000, 1200)]
        accts += [acct(i, seen=TODAY, closed_at=TODAY - D(40), closed_by="staff") for i in range(50)]
        accts += [acct(i, seen=old, unpaid_invoices=1) for i in range(2000, 2010)]
        r = plan_purge(accts, TODAY)
        dels = [x for x in r if x["action"] == "delete"]
        self.assertEqual(len(dels), MAX_DELETES_PER_RUN)
        self.assertTrue(set(range(50)) <= {x["account_id"] for x in dels})
        self.assertEqual(sum(x["action"] == "anonymise" for x in r), 10)
        ids = [x["account_id"] for x in r]
        self.assertEqual(ids, sorted(ids))

    def test_tenant_and_mutation(self):
        base = acct(seen=TODAY - D(800))
        res = [self.one(dict(base)), self.one({**base, "tenant": "x"}), self.one({**base, "tenant": object()})]
        self.assertEqual(res[0], res[1])
        self.assertEqual(res[0], res[2])
        accts = [acct(3, seen=TODAY - D(800)), acct(1, seen=TODAY - D(800))]
        before = copy.deepcopy(accts)
        plan_purge(accts, TODAY)
        self.assertEqual(accts, before)

    def test_defensive(self):
        self.assertEqual(self.one(acct(last_seen_at=None, seen=None) | {"last_seen_at": None}), [])
        a = acct(); a.pop("last_seen_at")
        self.assertEqual(self.one(a), [])
        self.assertEqual(self.one(acct(closed_at=TODAY + D(5), closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(self.one(acct(seen=TODAY - D(800), status="deleted"))[0]["action"], "delete")


if __name__ == "__main__":
    unittest.main()