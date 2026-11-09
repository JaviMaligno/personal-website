"""GDPR purge planner: plan_purge(accounts, today).

Ambiguity resolutions applied:
- "If the member closed the account themselves, don't. Warn them" is read as
  "don't warn them": closed_by == "member" with closed_at set => no warn.
- Inactivity uses last_seen_at only; last_login, status and tenant are ignored.
- Missing last_seen_at means no inactivity due date; with no closed_at either,
  there is no action.
- Due = min(last_seen_at + 730d, closed_at + 30d when closed_at is set).
- Exclusions first: litigation_hold, and staff emails (case-insensitive,
  trimmed) ending in @tidewater-klatring.no.
- due <= today => delete, or anonymise when unpaid_invoices is truthy.
- today < due <= today + 14 => warn (also for unpaid-invoice accounts).
- The 200 cap applies to deletes only. Order: closed first, then earliest due,
  then id. Capped-out accounts get no action and no warning.
  Anonymise and warn are not counted.
- Output is sorted by account_id. Duplicate ids raise ValueError.

CONFLICT TO RESOLVE: the brief and the PM spec say the member email must NOT
appear in any action (the audit log is shared with the climbing federation).
The house rule given to the developer says every action dict carries `email`.
This module follows the house rule (EMAIL_IN_ACTIONS = True). Set it to False
to satisfy the brief's privacy requirement; confirm with Mateusz and the DPO
before shipping, since the shared log would otherwise expose personal data.
"""
from datetime import date, timedelta
import unittest

EMAIL_IN_ACTIONS = True
APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
MAX_DELETES = 200


def _action(acc, kind, due, approver):
    d = {
        "account_id": acc["id"],
        "action": kind,
        "due": due.isoformat(),
        "approved_by": approver,
    }
    if EMAIL_IN_ACTIONS:
        d["email"] = acc.get("email")
    return d


def plan_purge(accounts, today):
    seen = set()
    for a in accounts:
        if a["id"] in seen:
            raise ValueError(f"duplicate account id: {a['id']!r}")
        seen.add(a["id"])

    deletes = []  # (sort key, action)
    others = []
    for a in accounts:
        if a.get("litigation_hold"):
            continue
        if (a.get("email") or "").strip().lower().endswith(STAFF_SUFFIX):
            continue
        dues = []
        if a.get("last_seen_at") is not None:
            dues.append(a["last_seen_at"] + INACTIVITY)
        closed_at = a.get("closed_at")
        if closed_at is not None:
            dues.append(closed_at + CLOSED_GRACE)
        if not dues:
            continue
        due = min(dues)
        if due <= today:
            if a.get("unpaid_invoices"):
                others.append(_action(a, "anonymise", due, APPROVER))
            else:
                key = (closed_at is None, due, a["id"])
                deletes.append((key, _action(a, "delete", due, APPROVER)))
        elif due <= today + WARN_WINDOW:
            if a.get("closed_by") == "member" and closed_at is not None:
                continue
            others.append(_action(a, "warn", due, None))

    deletes.sort(key=lambda t: t[0])
    result = others + [act for _, act in deletes[:MAX_DELETES]]
    result.sort(key=lambda x: x["account_id"])
    return result


class PlanPurgeTests(unittest.TestCase):
    T = date(2026, 10, 13)

    def acc(self, id_="a", **kw):
        d = dict(id=id_, email="m@example.com", status="active",
                 last_seen_at=self.T, last_login=None, closed_at=None,
                 closed_by=None, unpaid_invoices=False, litigation_hold=False)
        d.update(kw)
        return d

    def one(self, **kw):
        return plan_purge([self.acc(**kw)], self.T)

    def test_delete_at_730(self):
        r = self.one(last_seen_at=self.T - timedelta(days=730))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], self.T.isoformat())
        self.assertEqual(r[0]["approved_by"], APPROVER)

    def test_warn_window(self):
        r = self.one(last_seen_at=self.T - timedelta(days=730 - 14))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])
        self.assertEqual(self.one(last_seen_at=self.T - timedelta(days=730 - 15)), [])

    def test_closed_sooner(self):
        r = self.one(last_seen_at=self.T - timedelta(days=400),
                     closed_at=self.T - timedelta(days=100), closed_by="staff")
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[0]["due"], (self.T - timedelta(days=70)).isoformat())

    def test_member_closed_no_warn(self):
        self.assertEqual(self.one(closed_at=self.T - timedelta(days=20),
                                  closed_by="member"), [])
        r = self.one(closed_at=self.T - timedelta(days=20), closed_by="staff")
        self.assertEqual(r[0]["action"], "warn")

    def test_anonymise_and_warn_unpaid(self):
        r = self.one(last_seen_at=self.T - timedelta(days=800), unpaid_invoices=True)
        self.assertEqual(r[0]["action"], "anonymise")
        r = self.one(last_seen_at=self.T - timedelta(days=720), unpaid_invoices=True)
        self.assertEqual(r[0]["action"], "warn")

    def test_exclusions(self):
        old = self.T - timedelta(days=900)
        self.assertEqual(self.one(last_seen_at=old, litigation_hold=True), [])
        self.assertEqual(self.one(last_seen_at=old,
                                  email=" X@Tidewater-Klatring.NO "), [])

    def test_missing_last_seen(self):
        self.assertEqual(self.one(last_seen_at=None), [])
        r = self.one(last_seen_at=None, closed_at=self.T - timedelta(days=40))
        self.assertEqual(r[0]["action"], "delete")

    def test_cap_closed_first(self):
        accs = [self.acc(f"o{i:03d}", last_seen_at=self.T - timedelta(days=900))
                for i in range(220)]
        accs += [self.acc(f"z{i:03d}", closed_at=self.T - timedelta(days=31),
                          closed_by="staff") for i in range(30)]
        r = plan_purge(accs, self.T)
        self.assertEqual(len(r), 200)
        self.assertEqual(sum(x["account_id"].startswith("z") for x in r), 30)
        self.assertEqual([x["account_id"] for x in r],
                         sorted(x["account_id"] for x in r))

    def test_duplicates_and_no_mutation(self):
        with self.assertRaises(ValueError):
            plan_purge([self.acc("a"), self.acc("a")], self.T)
        a = self.acc(last_seen_at=self.T - timedelta(days=900))
        before = dict(a)
        plan_purge([a], self.T)
        self.assertEqual(a, before)


if __name__ == "__main__":
    unittest.main()