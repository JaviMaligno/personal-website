"""GDPR purge planner for Tidewater Climbing member accounts.

Entry point: plan_purge(accounts, today) -> list of action dicts with exactly the
keys account_id, action, due, approved_by. Pure function: inputs are not mutated,
and there is at most one action per account.

PM resolutions (each is a module constant or a small helper, so easy to change):
- Exclusions come first. These accounts never get an action:
    * litigation_hold truthy. Ambiguous strings such as "false" count as held
      (fail safe). A missing key means not held.
    * staff email (stripped, case-insensitive, ends with STAFF_SUFFIX).
    * status "anonymised" or "deleted".
  The `tenant` column is ignored.
- Malformed accounts are skipped and never deleted. Malformed means: not a dict,
  id missing or not str/int, email or status not a str, last_seen_at or closed_at
  neither a date nor None (datetime is rejected), or today not a date.
- due = last_seen_at + 730d. If closed_at is set, due = min(due, closed_at + 30d).
  If last_seen_at is None, a closed account is due at closed_at + 30d and an
  open account gets no action.
- due <= today gives "delete", or "anonymise" if unpaid_invoices is truthy.
- "warn" when 1 <= (due - today).days <= 40, but only if the account is open or
  closed_by == "staff". Member-closed accounts, and closed accounts with a
  missing or unexpected closed_by, are not warned. Accounts with unpaid invoices
  are still warned.
- due is an ISO string. approved_by is the DPO name for delete/anonymise and
  None for warn (key present).
- Cap: at most MAX_DELETES deletes per run (anonymise and warn are uncapped).
  Over the cap, closed accounts come first, then oldest due, then id. Take the
  first MAX_DELETES, then sort the whole output by account_id. Deletes cut by
  the cap are simply not emitted and come up again on the next run.
- Duplicate ids raise ValueError, because deleting the wrong row is worse than
  failing.

Assumptions needing client confirmation:
- CONFLICT: an internal house rule says every action should also carry the
  account's `email`. The client brief and the PM resolutions explicitly forbid
  email in any action, because the audit log is shared with the climbing
  federation. This module follows the brief (no email). Confirm with the client
  before any change.
- "Within the next forty days" is read as 1..40 days inclusive.
- Accounts with unpaid invoices are anonymised on the same due date as a delete
  (the 5-year invoice retention is not modelled further).
- Truthy unpaid_invoices (a count, a list, or any non-empty string) means unpaid.
- A staff check on a non-string email is treated as malformed, so the account is
  skipped.
"""
from collections import Counter
from datetime import date, datetime, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 40
MAX_DELETES = 200
APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
SKIP_STATUSES = frozenset({"anonymised", "deleted"})


def _is_date(v):
    return isinstance(v, date) and not isinstance(v, datetime)


def _valid_id(v):
    return isinstance(v, (str, int)) and not isinstance(v, bool)


def _plan_one(a, today):
    """Return (action_dict, closed) or None."""
    if not isinstance(a, dict) or not _valid_id(a.get("id")):
        return None
    if a.get("litigation_hold"):  # fail safe: any truthy value means held
        return None
    email, status = a.get("email"), a.get("status")
    if not isinstance(email, str) or not isinstance(status, str):
        return None
    if email.strip().lower().endswith(STAFF_SUFFIX):
        return None
    if status.strip().lower() in SKIP_STATUSES:
        return None
    seen, closed = a.get("last_seen_at"), a.get("closed_at")
    if seen is not None and not _is_date(seen):
        return None
    if closed is not None and not _is_date(closed):
        return None

    grace = closed + timedelta(days=CLOSED_GRACE_DAYS) if closed else None
    inactive = seen + timedelta(days=INACTIVITY_DAYS) if seen else None
    candidates = [d for d in (inactive, grace) if d is not None]
    if not candidates:
        return None
    due = min(candidates)

    if due <= today:
        kind = "anonymise" if a.get("unpaid_invoices") else "delete"
    elif 1 <= (due - today).days <= WARN_DAYS and (
        closed is None or a.get("closed_by") == "staff"
    ):
        kind = "warn"
    else:
        return None
    action = {
        "account_id": a["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": None if kind == "warn" else APPROVER,
    }
    return action, closed is not None, due


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    ids = [a["id"] for a in accounts
           if isinstance(a, dict) and _valid_id(a.get("id"))]
    dupes = sorted((i for i, n in Counter(ids).items() if n > 1), key=str)
    if dupes:
        raise ValueError(f"duplicate account ids: {dupes}")

    planned = [p for p in (_plan_one(a, today) for a in accounts) if p]
    deletes = [p for p in planned if p[0]["action"] == "delete"]
    others = [p[0] for p in planned if p[0]["action"] != "delete"]
    deletes.sort(key=lambda p: (not p[1], p[2], p[0]["account_id"]))
    out = others + [p[0] for p in deletes[:MAX_DELETES]]
    out.sort(key=lambda x: x["account_id"])
    return out


# ---------------------------------------------------------------- tests
import unittest  # noqa: E402

T = date(2026, 10, 13)


def acc(id, **kw):
    base = dict(id=id, email=f"u{id}@example.com", status="active",
                last_seen_at=T, last_login=None, closed_at=None,
                closed_by=None, unpaid_invoices=False, litigation_hold=False)
    base.update(kw)
    return base


class PlanTests(unittest.TestCase):
    def test_delete_and_due_boundary(self):
        r = plan_purge([acc(1, last_seen_at=T - timedelta(days=730)),
                        acc(2, last_seen_at=T - timedelta(days=729))], T)
        self.assertEqual([(x["account_id"], x["action"]) for x in r],
                         [(1, "delete"), (2, "warn")])
        self.assertEqual(r[0]["due"], T.isoformat())
        self.assertEqual(r[0]["approved_by"], APPROVER)
        self.assertIsNone(r[1]["approved_by"])
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by"})

    def test_closed_sooner_and_unpaid(self):
        a = acc(1, closed_at=T - timedelta(days=30), closed_by="member",
                unpaid_invoices=2)
        self.assertEqual(plan_purge([a], T)[0]["action"], "anonymise")

    def test_warn_rules(self):
        far = T - timedelta(days=730 - 40)
        self.assertEqual(plan_purge([acc(1, last_seen_at=far)], T)[0]["action"], "warn")
        self.assertEqual(plan_purge([acc(1, last_seen_at=far - timedelta(days=1))], T)[0]["action"], "warn")
        self.assertEqual(plan_purge([acc(1, last_seen_at=far + timedelta(days=1))], T)[0]["action"], "warn")
        self.assertEqual(plan_purge([acc(1, last_seen_at=far + timedelta(days=-1 - 1))], T)[0]["action"], "warn")
        self.assertEqual(plan_purge([acc(1, last_seen_at=T - timedelta(days=600))], T), [])
        c = T - timedelta(days=10)  # closed, due in 20 days
        self.assertEqual(plan_purge([acc(1, closed_at=c, closed_by="member")], T), [])
        self.assertEqual(plan_purge([acc(1, closed_at=c, closed_by=None)], T), [])
        self.assertEqual(plan_purge([acc(1, closed_at=c, closed_by="staff")], T)[0]["action"], "warn")

    def test_exclusions(self):
        old = T - timedelta(days=900)
        accs = [acc(1, last_seen_at=old, litigation_hold="false"),
                acc(2, last_seen_at=old, email=" X@Tidewater-Klatring.NO "),
                acc(3, last_seen_at=old, status="anonymised"),
                acc(4, last_seen_at=old, litigation_hold=None),
                acc(5, last_seen_at="2020-01-01"),
                acc(6, last_seen_at=None)]
        self.assertEqual([x["account_id"] for x in plan_purge(accs, T)], [4])

    def test_none_last_seen_closed(self):
        a = acc(1, last_seen_at=None, closed_at=T - timedelta(days=31))
        self.assertEqual(plan_purge([a], T)[0]["action"], "delete")

    def test_cap_prefers_closed_then_oldest(self):
        accs = [acc(i, last_seen_at=T - timedelta(days=800 + i)) for i in range(1, 201)]
        accs.append(acc(999, closed_at=T - timedelta(days=31), closed_by="staff"))
        accs.append(acc(0, last_seen_at=T - timedelta(days=731)))
        r = plan_purge(accs, T)
        ids = [x["account_id"] for x in r]
        self.assertEqual(len(r), 200)
        self.assertEqual(ids, sorted(ids))
        self.assertIn(999, ids)
        self.assertNotIn(0, ids)

    def test_no_mutation_and_duplicates(self):
        accs = [acc(1, last_seen_at=T - timedelta(days=800))]
        import copy
        before = copy.deepcopy(accs)
        plan_purge(accs, T)
        self.assertEqual(accs, before)
        with self.assertRaises(ValueError):
            plan_purge([acc(1), acc(1)], T)


if __name__ == "__main__":
    unittest.main()