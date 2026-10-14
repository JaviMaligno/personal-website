"""Purge planner for member accounts (GDPR clean-up).

Assumptions to raise with the client:
- Anonymise is not idempotent: an anonymised account keeps its last_seen_at and
  closed_at, so it stays due and is returned as "anonymise" on every run until
  the caller marks it done or removes it. The planner has no state to tell.
- The 200 cap counts only deletes. Anonymise and warn actions are uncapped.
  Deferred deletes get no action (not even a warning) and reappear next run.
- unpaid_invoices is treated as truthy/positive; litigation_hold as truthy.
- A closed account with a missing or unknown closed_by is never warned.
- CONFLICT: the client brief says no email in any action (audit log is shared
  with the climbing federation), but the house rule for this team requires
  `email` in every action dict. This module follows the house rule. To meet
  the client brief, remove the "email" line in _action. Needs a decision
  before the audit log is shared; it is personal data going to a third party.
"""
import unicodedata
from datetime import date, datetime, timedelta

MAX_DELETES = 200
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
STAFF_SUFFIX = "@tidewater-klatring.no"
APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")


def _d(v):
    if v is None:
        return None
    return v.date() if isinstance(v, datetime) else v


def _action(a, action, due):
    return {
        "account_id": a["id"],
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else APPROVER,
        "email": a.get("email"),
    }


def plan_purge(accounts, today):
    today = _d(today)
    warn_limit = today + timedelta(days=WARN_DAYS)
    out, deletes = [], []
    for a in accounts:
        email = (a.get("email") or "").strip().lower()
        if email.endswith(STAFF_SUFFIX) or a.get("litigation_hold"):
            continue
        seen, closed = _d(a.get("last_seen_at")), _d(a.get("closed_at"))
        if seen is None:
            if closed is None:
                continue
            due = closed + timedelta(days=CLOSED_DAYS)
        else:
            due = seen + timedelta(days=INACTIVITY_DAYS)
            if closed is not None:
                due = min(due, closed + timedelta(days=CLOSED_DAYS))
        if due <= today:
            if a.get("unpaid_invoices"):
                out.append(_action(a, "anonymise", due))
            else:
                deletes.append((closed is None, due, a["id"], a))
        elif due <= warn_limit:
            if closed is None or a.get("closed_by") == "staff":
                out.append(_action(a, "warn", due))
    deletes.sort(key=lambda t: t[:3])
    for _, due, _, a in deletes[:MAX_DELETES]:
        out.append(_action(a, "delete", due))
    out.sort(key=lambda x: x["account_id"])
    return out


if __name__ == "__main__":
    import json
    import unittest

    T = date(2026, 10, 13)

    def acc(i, seen=date(2020, 1, 1), **kw):
        d = dict(id=i, email=f"u{i}@x.no", status="active", last_seen_at=seen,
                 last_login=None, closed_at=None, closed_by=None,
                 unpaid_invoices=0, litigation_hold=False, tenant="t")
        d.update(kw)
        return d

    class Tests(unittest.TestCase):
        def test_boundaries(self):
            r = plan_purge([acc(1, date(2024, 10, 13)), acc(2, date(2024, 10, 14)),
                            acc(3, date(2024, 10, 27)), acc(4, date(2024, 10, 28))], T)
            self.assertEqual([(x["account_id"], x["action"]) for x in r],
                             [(1, "delete"), (2, "warn"), (3, "warn")][:3])
            self.assertEqual(r[0]["due"], "2026-10-13")
            self.assertIsNone(r[1]["approved_by"])
            json.dumps(r)

        def test_exclusions_and_anonymise(self):
            r = plan_purge([acc(1, email=" A@Tidewater-Klatring.NO "), acc(2, litigation_hold=True),
                            acc(3, unpaid_invoices=2), acc(4, email=None)], T)
            self.assertEqual([(x["account_id"], x["action"]) for x in r],
                             [(3, "anonymise"), (4, "delete")])

        def test_closed_warn_rules(self):
            c = date(2026, 10, 20)
            r = plan_purge([acc(1, closed_at=date(2026, 9, 25), closed_by="member"),
                            acc(2, closed_at=date(2026, 9, 25), closed_by="staff"),
                            acc(3, closed_at=date(2026, 9, 25))], T)
            self.assertEqual([x["account_id"] for x in r], [2])

        def test_cap(self):
            accs = [acc(i) for i in range(1, 251)]
            accs += [acc(1000 + i, closed_at=date(2026, 1, 1)) for i in range(30)]
            r = plan_purge(accs, T)
            self.assertEqual(len(r), 200)
            ids = [x["account_id"] for x in r]
            self.assertEqual(ids, sorted(ids))
            self.assertTrue(all(1000 + i in ids for i in range(30)))

        def test_no_mutation_and_last_seen_none(self):
            a = acc(1, None, closed_at=date(2026, 9, 1))
            before = dict(a)
            r = plan_purge([a, acc(2, None)], T)
            self.assertEqual(a, before)
            self.assertEqual([x["account_id"] for x in r], [1])

    unittest.main()