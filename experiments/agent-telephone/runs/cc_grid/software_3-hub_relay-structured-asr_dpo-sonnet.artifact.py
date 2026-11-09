"""Tidewater Climbing GDPR purge planner (stdlib only), with unittest tests.

House rule applied: every action dict also carries the account's `email` so
support can follow up. This extends the four-key shape in R1 and departs from
R9 (no email in output). Remove EMAIL handling in `plan_purge` if the client
wants the strict four-key shape.
"""
import json
import logging
import unittest
from copy import deepcopy
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

MAX_DELETIONS_PER_RUN = 200
COUNT_ANONYMISE_IN_CAP = True  # one-line switch: False => cap counts deletes only
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
APPROVER = "Tordis Svenbjorn Dottir"
STAFF_SUFFIX = "@tidewater-klatring.no"
PROCESSED_STATUSES = frozenset({"anonymised", "deleted"})
REQUIRED_KEYS = ("id", "email", "status", "last_seen_at", "closed_at",
                 "closed_by", "unpaid_invoices", "litigation_hold")


class _Malformed(Exception):
    pass


def _is_date(v):
    return isinstance(v, date) and not isinstance(v, datetime)


def _has_unpaid(v):
    if isinstance(v, bool) or v is None:
        raise _Malformed
    if isinstance(v, (int, float)):
        return v > 0
    if isinstance(v, (list, tuple, set, frozenset, dict)):
        return len(v) > 0
    raise _Malformed


def _due_date(acc):
    """Earlier of applicable due dates, or None if no rule applies."""
    seen, closed = acc["last_seen_at"], acc["closed_at"]
    if (seen is not None and not _is_date(seen)) or \
            (closed is not None and not _is_date(closed)):
        raise _Malformed
    dues = []
    try:
        if seen is not None:
            dues.append(seen + timedelta(days=INACTIVITY_DAYS))
        if closed is not None:
            dues.append(closed + timedelta(days=CLOSED_DAYS))
    except OverflowError:
        raise _Malformed
    return min(dues) if dues else None


def _is_warning(due, today, closed_by):
    """Warning logic, isolated from destructive logic."""
    if closed_by == "member":
        return False
    return today < due <= today + timedelta(days=WARN_DAYS)


def _is_destructive(due, today):
    return due <= today


def plan_purge(accounts, today):
    candidates = []  # (account, due, action)
    warnings = []
    for acc in accounts or []:
        aid = acc.get("id") if isinstance(acc, dict) else None
        try:
            if not isinstance(acc, dict) or aid is None:
                raise _Malformed
            if any(k not in acc for k in REQUIRED_KEYS):
                raise _Malformed
            if acc["litigation_hold"]:
                continue
            email = acc["email"]
            if not isinstance(email, str):
                raise _Malformed
            if email.strip().lower().endswith(STAFF_SUFFIX):
                continue
            if acc["status"] in PROCESSED_STATUSES:
                continue
            due = _due_date(acc)
            unpaid = _has_unpaid(acc["unpaid_invoices"])
        except (_Malformed, TypeError):
            logger.warning("purge: skipping malformed account id=%r", aid)
            continue
        if due is None:
            logger.info("purge: no applicable rule for account id=%r", aid)
            continue
        if _is_destructive(due, today):
            candidates.append((acc, due, "anonymise" if unpaid else "delete"))
        elif _is_warning(due, today, acc["closed_by"]):
            warnings.append((acc, due, "warn"))

    def key(c):
        a = c[0]
        return (a["closed_at"] is None, c[1], a["id"])

    pool = candidates if COUNT_ANONYMISE_IN_CAP else \
        [c for c in candidates if c[2] == "delete"]
    if len(pool) > MAX_DELETIONS_PER_RUN:
        keep = sorted(pool, key=key)[:MAX_DELETIONS_PER_RUN]
        logger.warning("purge: cap applied, candidates=%d cap=%d dropped=%d",
                       len(pool), MAX_DELETIONS_PER_RUN,
                       len(pool) - len(keep))
        kept_ids = {id(c[0]) for c in keep}
        candidates = [c for c in candidates
                      if id(c[0]) in kept_ids or c not in pool]

    out = []
    for acc, due, action in candidates + warnings:
        out.append({
            "account_id": acc["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": None if action == "warn" else APPROVER,
            "email": acc["email"],
        })
    out.sort(key=lambda d: d["account_id"])
    return out


# ----------------------------- tests ---------------------------------------
TODAY = date(2026, 10, 13)


def acct(**kw):
    a = {"id": 1, "email": "m@example.com", "status": "active",
         "last_seen_at": TODAY - timedelta(days=10), "last_login": None,
         "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
         "litigation_hold": False}
    a.update(kw)
    return a


def seen(offset_due):
    """last_seen_at giving inactivity due = TODAY + offset_due days."""
    return TODAY + timedelta(days=offset_due - INACTIVITY_DAYS)


def run(*accs):
    return plan_purge(list(accs), TODAY)


class PurgeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_boundaries(self):
        for off, action in [(0, "delete"), (-1, "delete"), (1, "warn"),
                            (14, "warn"), (15, None)]:
            r = run(acct(last_seen_at=seen(off)))
            if action is None:
                self.assertEqual(r, [], off)
            else:
                self.assertEqual(r[0]["action"], action, off)
                self.assertEqual(r[0]["due"],
                                 (TODAY + timedelta(days=off)).isoformat())

    def test_closed_vs_inactivity(self):
        r = run(acct(closed_at=TODAY - timedelta(days=30), closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")
        r = run(acct(last_seen_at=seen(-1),
                     closed_at=TODAY - timedelta(days=5), closed_by="staff"))
        self.assertEqual(r[0]["due"], (TODAY - timedelta(days=1)).isoformat())
        r = run(acct(last_seen_at=None, closed_at=TODAY - timedelta(days=40),
                     closed_by="member"))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(run(acct(last_seen_at=None)), [])

    def test_member_vs_staff_closed_warn(self):
        c = TODAY - timedelta(days=20)
        self.assertEqual(run(acct(closed_at=c, closed_by="member")), [])
        r = run(acct(closed_at=c, closed_by="staff"))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])

    def test_unpaid(self):
        for u in (3, [1], {"a": 1}):
            self.assertEqual(
                run(acct(last_seen_at=seen(0), unpaid_invoices=u))[0]["action"],
                "anonymise")
        for u in (0, []):
            self.assertEqual(
                run(acct(last_seen_at=seen(0), unpaid_invoices=u))[0]["action"],
                "delete")
        self.assertEqual(
            run(acct(last_seen_at=seen(5), unpaid_invoices=2))[0]["action"],
            "warn")

    def test_hold_and_staff(self):
        for off in (-5, 0, 7):
            self.assertEqual(
                run(acct(last_seen_at=seen(off), litigation_hold=True)), [])
            self.assertEqual(
                run(acct(last_seen_at=seen(off),
                         email="  Bob@Tidewater-Klatring.NO ")), [])
        r = run(acct(last_seen_at=seen(0), email="x@evil-tidewater-klatring.no"))
        self.assertEqual(r[0]["action"], "delete")

    def test_processed_status(self):
        for s in PROCESSED_STATUSES:
            self.assertEqual(run(acct(last_seen_at=seen(-3), status=s)), [])

    def test_last_login_and_tenant_ignored(self):
        self.assertEqual(run(acct(last_seen_at=None, last_login=seen(-5))), [])
        old = acct(last_seen_at=seen(-5))
        a = run(old)
        b = run(acct(last_seen_at=seen(-5), last_login=TODAY, tenant="x"))
        self.assertEqual(a, b)
        self.assertEqual(a[0]["action"], "delete")

    def test_cap(self):
        accs = []
        for i in range(1, 201):  # inactivity only, due = TODAY - i
            accs.append(acct(id=i, last_seen_at=seen(-i),
                             unpaid_invoices=i % 2))
        for i in range(201, 251):  # closed, due = TODAY - 5
            accs.append(acct(id=i, closed_at=TODAY - timedelta(days=35),
                             closed_by="member"))
        accs.append(acct(id=300, last_seen_at=seen(-900), litigation_hold=True))
        accs.append(acct(id=301, last_seen_at=seen(-900),
                         email="a@tidewater-klatring.no"))
        accs.append(acct(id=302, last_seen_at=seen(3)))
        r = run(*accs)
        destructive = [x for x in r if x["action"] != "warn"]
        self.assertEqual(len(destructive), MAX_DELETIONS_PER_RUN)
        ids = {x["account_id"] for x in destructive}
        self.assertTrue(set(range(201, 251)) <= ids)
        self.assertEqual(ids - set(range(201, 251)), set(range(51, 201)))
        self.assertNotIn(300, ids)
        self.assertNotIn(301, ids)
        self.assertEqual([x["account_id"] for x in r if x["action"] == "warn"],
                         [302])

    def test_output_shape(self):
        accs = [acct(id=3, last_seen_at=seen(0)),
                acct(id=1, last_seen_at=seen(4)),
                acct(id=2, last_seen_at=seen(-9), unpaid_invoices=1)]
        before = deepcopy(accs)
        r = plan_purge(accs, TODAY)
        self.assertEqual(accs, before)
        self.assertEqual([x["account_id"] for x in r], [1, 2, 3])
        json.dumps(r)
        for x in r:
            self.assertEqual(set(x), {"account_id", "action", "due",
                                      "approved_by", "email"})
            self.assertIsInstance(x["due"], str)
            self.assertEqual(x["approved_by"],
                             None if x["action"] == "warn" else APPROVER)

    def test_malformed_skipped(self):
        bad1 = acct(id=10)
        del bad1["closed_by"]
        bad2 = acct(id=11, last_seen_at="2024-01-01")
        bad3 = acct(id=12, unpaid_invoices=None, last_seen_at=seen(-1))
        bad4 = acct(id=None, last_seen_at=seen(-1))
        good = acct(id=13, last_seen_at=seen(-1))
        r = plan_purge([bad1, bad2, bad3, bad4, "junk", good], TODAY)
        self.assertEqual([x["account_id"] for x in r], [13])


if __name__ == "__main__":
    unittest.main()