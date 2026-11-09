"""GDPR purge planner for member accounts.

Note: a house rule asked for each action to carry the account's email. This
module deliberately does not: the brief (authoritative) and the PM summary
forbid email in any action because the audit log is shared with the climbing
federation, and putting personal data there would defeat the purpose of a
GDPR clean-up. Actions contain only account_id, action, due, approved_by.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import unittest

log = logging.getLogger(__name__)

STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "Þórdís Sveinbjörnsdóttir"
MAX_DELETIONS = 200
INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 40

_REQUIRED = ("id", "email", "last_seen_at", "closed_at", "unpaid_invoices", "litigation_hold")


def _is_date(v):
    return isinstance(v, dt.date) and not isinstance(v, dt.datetime)


def _due(acc):
    """Return the due date, or None if not computable. Raises on malformed."""
    if not isinstance(acc, dict) or any(k not in acc for k in _REQUIRED):
        raise ValueError("missing keys")
    email, seen, closed = acc["email"], acc["last_seen_at"], acc["closed_at"]
    if email is not None and not isinstance(email, str):
        raise ValueError("bad email")
    if seen is not None and not _is_date(seen):
        raise ValueError("bad last_seen_at")
    if closed is not None and not _is_date(closed):
        raise ValueError("bad closed_at")
    cands = []
    if seen is not None:
        cands.append(seen + dt.timedelta(days=INACTIVE_DAYS))
    if closed is not None:
        cands.append(closed + dt.timedelta(days=CLOSED_DAYS))
    return min(cands) if cands else None


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    horizon = today + dt.timedelta(days=WARN_DAYS)
    deletes, others = [], []
    for acc in accounts:
        try:
            due = _due(acc)
            if due is None:
                continue
            email = acc["email"]
            if email is not None and email.strip().lower().endswith(STAFF_DOMAIN):
                continue
            if acc["litigation_hold"]:
                continue
            aid, closed = acc["id"], acc["closed_at"]
            if due <= today:
                if acc["unpaid_invoices"]:
                    others.append((aid, "anonymise", due))
                else:
                    deletes.append(((closed is None, due, aid), aid, due))
            elif due <= horizon:
                if closed is not None and acc.get("closed_by") == "member":
                    continue
                others.append((aid, "warn", due))
        except (ValueError, TypeError, OverflowError):
            log.warning("skipping malformed account record")
    deletes.sort(key=lambda t: t[0])
    out = [(a, "delete", d) for _, a, d in deletes[:MAX_DELETIONS]] + others
    out.sort(key=lambda t: t[0])
    return [
        {
            "account_id": a,
            "action": act,
            "due": d.isoformat(),
            "approved_by": None if act == "warn" else APPROVER,
        }
        for a, act, d in out
    ]


# ---------------------------------------------------------------- tests
D = dt.date
TODAY = D(2026, 10, 13)


def _acc(i=1, seen=None, closed=None, by=None, unpaid=False, hold=False,
         email="m@example.com"):
    return {"id": i, "email": email, "status": "x", "last_seen_at": seen,
            "last_login": D(2000, 1, 1), "closed_at": closed, "closed_by": by,
            "unpaid_invoices": unpaid, "litigation_hold": hold, "tenant": "t"}


def _seen(days_ago):
    return TODAY - dt.timedelta(days=days_ago)


class PurgeTests(unittest.TestCase):
    def one(self, acc):
        return plan_purge([acc], TODAY)

    def test_730_729(self):
        r = self.one(_acc(seen=_seen(730)))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], TODAY.isoformat())
        r = self.one(_acc(seen=_seen(729)))
        self.assertEqual(r[0]["action"], "warn")

    def test_warn_40_41(self):
        self.assertEqual(self.one(_acc(seen=_seen(730 - 40)))[0]["action"], "warn")
        self.assertEqual(self.one(_acc(seen=_seen(730 - 41))), [])

    def test_closed_30_29(self):
        s = _seen(100)
        self.assertEqual(self.one(_acc(seen=s, closed=_seen(30), by="member"))[0]["action"], "delete")
        self.assertEqual(self.one(_acc(seen=s, closed=_seen(29), by="member")), [])
        self.assertEqual(self.one(_acc(seen=s, closed=_seen(29), by="staff"))[0]["action"], "warn")

    def test_closed_without_last_seen(self):
        self.assertEqual(self.one(_acc(closed=_seen(30), by="staff"))[0]["action"], "delete")
        self.assertEqual(self.one(_acc()), [])

    def test_unpaid(self):
        r = self.one(_acc(seen=_seen(800), unpaid=True))
        self.assertEqual(r[0]["action"], "anonymise")
        self.assertEqual(r[0]["approved_by"], APPROVER)
        r = self.one(_acc(seen=_seen(700), unpaid=True))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])

    def test_hold_and_staff(self):
        self.assertEqual(self.one(_acc(seen=_seen(800), hold=True)), [])
        self.assertEqual(self.one(_acc(seen=_seen(800), email="  A@Tidewater-Klatring.NO ")), [])
        self.assertEqual(len(self.one(_acc(seen=_seen(800), email=None))), 1)

    def test_cap(self):
        accs = [_acc(i, seen=_seen(800)) for i in range(1, 201)]
        accs += [_acc(i, seen=_seen(100), closed=_seen(30), by="member") for i in range(201, 251)]
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)
        ids = {x["account_id"] for x in r}
        self.assertTrue(set(range(201, 251)) <= ids)
        self.assertEqual([x["account_id"] for x in r], sorted(ids))
        self.assertNotIn("@", json.dumps(r))

    def test_malformed_and_pure(self):
        bad = [{"id": 9}, _acc(2, seen="2020-01-01"), _acc(3, seen=_seen(800)), None]
        good = _acc(4, seen=_seen(800))
        accs = [*bad, good]
        import copy
        snap = copy.deepcopy(accs)
        r = plan_purge(accs, TODAY)
        self.assertEqual([x["account_id"] for x in r], [3, 4])
        self.assertEqual(accs, snap)
        self.assertEqual(set(r[0]), {"account_id", "action", "due", "approved_by"})


if __name__ == "__main__":
    unittest.main()