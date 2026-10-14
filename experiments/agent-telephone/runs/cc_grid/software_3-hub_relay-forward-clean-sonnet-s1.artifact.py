"""GDPR purge planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today) -> list[dict].

Each action has the keys account_id, action, due (ISO string), approved_by and
email. approved_by is the DPO for delete/anonymise and None for warn.

Assumptions (from the PM spec):
- The house rule says every action carries the account's `email`. The client
  brief says the shared audit log must not contain member emails. These
  conflict. The house rule is followed via INCLUDE_EMAIL; set it to False to
  get the brief's behaviour. This needs a decision before the log is shared
  with the climbing federation.
- `tenant`, `last_login` and `status` are ignored. _already_anonymised() is
  the single hook for skipping already-anonymised accounts (currently never).
- Skipped entirely: litigation_hold truthy, or email (stripped,
  case-insensitive) ending with "@tidewater-klatring.no".
- Fail safe, no action and the run continues: account is not a dict, id is
  missing/None/empty, or litigation_hold/email/unpaid_invoices keys are
  missing, or the data is unusable.
- due = min(last_seen_at + 730d, closed_at + 30d if closed_at set). With
  neither date, no action.
- due <= today: anonymise if unpaid_invoices else delete.
  today < due <= today + 14: warn, unless closed_at is set and
  closed_by == "member". Otherwise nothing.
- Cap: at most MAX_DELETES deletes. Anonymise is neither counted nor dropped,
  and warns are uncapped. Over the cap, deletes are ordered closed first, then
  earliest due, then lowest id, and truncated. The cap is applied before the
  final sort by account_id.
- Input is not mutated.
"""
import json
import unittest
from datetime import date, timedelta

MAX_DELETES = 200
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
STAFF_SUFFIX = "@tidewater-klatring.no"
DPO = "Þórdís Sveinbjörnsdóttir"
INCLUDE_EMAIL = True  # house rule; see docstring

_REQUIRED = ("litigation_hold", "email", "unpaid_invoices")


def _already_anonymised(account):
    """HOOK (open question): skip accounts already anonymised, e.g. by status."""
    return False


def _idkey(i):
    return (0, i, "") if isinstance(i, int) and not isinstance(i, bool) else (1, 0, str(i))


def _plan_one(acc, today):
    if not isinstance(acc, dict):
        return None
    aid = acc.get("id")
    if aid is None or aid == "" or isinstance(aid, (dict, list, set)):
        return None
    if any(k not in acc for k in _REQUIRED):
        return None
    email = acc["email"]
    if not isinstance(email, str):
        return None
    if acc["litigation_hold"]:
        return None
    if email.strip().lower().endswith(STAFF_SUFFIX):
        return None
    if _already_anonymised(acc):
        return None

    seen, closed = acc.get("last_seen_at"), acc.get("closed_at")
    cands = []
    if seen is not None:
        cands.append(seen + timedelta(days=INACTIVITY_DAYS))
    if closed is not None:
        cands.append(closed + timedelta(days=CLOSED_DAYS))
    if not cands:
        return None
    due = min(cands)

    if due <= today:
        action = "anonymise" if acc["unpaid_invoices"] else "delete"
    elif due <= today + timedelta(days=WARN_DAYS):
        if closed is not None and acc.get("closed_by") == "member":
            return None
        action = "warn"
    else:
        return None

    out = {
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO,
    }
    if INCLUDE_EMAIL:
        out["email"] = email
    return out, due, closed is not None


def plan_purge(accounts, today):
    deletes, others = [], []
    for acc in accounts:
        try:
            r = _plan_one(acc, today)
        except Exception:
            r = None  # fail safe, keep going
        if r is None:
            continue
        out, due, is_closed = r
        (deletes if out["action"] == "delete" else others).append((out, due, is_closed))

    deletes.sort(key=lambda t: (not t[2], t[1], _idkey(t[0]["account_id"])))
    kept = deletes[:MAX_DELETES]
    result = [t[0] for t in kept + others]
    result.sort(key=lambda a: _idkey(a["account_id"]))
    return result


class PlanPurgeTests(unittest.TestCase):
    T = date(2026, 10, 13)

    def acc(self, id=1, **kw):
        d = dict(id=id, email="m@example.com", status="active",
                 last_seen_at=self.T - timedelta(days=10), last_login=None,
                 closed_at=None, closed_by=None, unpaid_invoices=False,
                 litigation_hold=False, tenant="x")
        d.update(kw)
        return d

    def plan(self, *a):
        return plan_purge(list(a), self.T)

    def seen(self, n, **kw):
        return self.acc(last_seen_at=self.T - timedelta(days=n), **kw)

    def test_boundaries(self):
        self.assertEqual(self.plan(self.seen(730))[0]["action"], "delete")
        self.assertEqual(self.plan(self.seen(729))[0]["action"], "warn")
        self.assertEqual(self.plan(self.seen(716))[0]["action"], "warn")
        self.assertEqual(self.plan(self.seen(715)), [])
        self.assertEqual(self.plan(self.seen(731))[0]["action"], "delete")

    def test_due_iso_and_approver(self):
        r = self.plan(self.seen(730))[0]
        self.assertEqual(r["due"], self.T.isoformat())
        self.assertEqual(r["approved_by"], DPO)
        self.assertIsNone(self.plan(self.seen(729))[0]["approved_by"])

    def test_closed_30(self):
        r = self.plan(self.acc(closed_at=self.T - timedelta(days=30), closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")

    def test_closed_d20_staff_vs_member(self):
        c = self.T - timedelta(days=20)
        self.assertEqual(self.plan(self.acc(closed_at=c, closed_by="staff"))[0]["action"], "warn")
        self.assertEqual(self.plan(self.acc(closed_at=c, closed_by="member")), [])

    def test_unpaid(self):
        self.assertEqual(self.plan(self.seen(800, unpaid_invoices=True))[0]["action"], "anonymise")
        self.assertEqual(self.plan(self.seen(729, unpaid_invoices=True))[0]["action"], "warn")

    def test_staff_and_lookalikes(self):
        self.assertEqual(self.plan(self.seen(800, email="  A@Tidewater-Klatring.NO ")), [])
        for e in ("a@tidewater-klatring.no.evil.com", "a@x.tidewater-klatring.no",
                  "a@eviltidewater-klatring.no"):
            self.assertEqual(len(self.plan(self.seen(800, email=e))), 1, e)

    def test_litigation_hold(self):
        self.assertEqual(self.plan(self.seen(800, litigation_hold=True)), [])

    def test_fail_safe(self):
        bad = self.seen(800)
        del bad["litigation_hold"]
        nid = self.seen(800, id=None)
        noemail = self.seen(800)
        del noemail["email"]
        good = self.seen(800, id=5)
        r = self.plan(bad, nid, noemail, "junk", good)
        self.assertEqual([a["account_id"] for a in r], [5])

    def test_no_dates(self):
        self.assertEqual(self.plan(self.acc(last_seen_at=None)), [])

    def test_cap_closed_first_and_sorting(self):
        accs = [self.seen(900, id=i) for i in range(1, MAX_DELETES + 1)]
        accs.append(self.acc(id=999, last_seen_at=None,
                             closed_at=self.T - timedelta(days=30), closed_by="staff"))
        accs.append(self.seen(900, id=0, unpaid_invoices=True))
        accs.append(self.seen(729, id=5000))
        r = plan_purge(accs, self.T)
        dels = [a for a in r if a["action"] == "delete"]
        self.assertEqual(len(dels), MAX_DELETES)
        ids = [a["account_id"] for a in dels]
        self.assertIn(999, ids)
        self.assertNotIn(MAX_DELETES, ids)  # highest-id open one dropped
        self.assertEqual(len([a for a in r if a["action"] == "anonymise"]), 1)
        self.assertEqual(len([a for a in r if a["action"] == "warn"]), 1)
        all_ids = [a["account_id"] for a in r]
        self.assertEqual(all_ids, sorted(all_ids))

    def test_json_and_no_input_mutation(self):
        a = self.seen(800)
        import copy
        before = copy.deepcopy(a)
        r = self.plan(a)
        json.dumps(r)
        self.assertEqual(a, before)

    def test_keys_and_email_only_under_email_key(self):
        r = self.plan(self.seen(800, email="secret@example.com"))[0]
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by", "email"})
        self.assertNotIn("tenant", r)
        rest = {k: v for k, v in r.items() if k != "email"}
        self.assertNotIn("secret@example.com", json.dumps(rest))


if __name__ == "__main__":
    unittest.main()