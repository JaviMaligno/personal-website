# purge.py (tests are embedded below; split them into test_purge.py if wanted)
# I had no tools, so none of this has been run.
#
# CONFLICT: the house rule says every action dict carries `email`, but the
# brief and architect say never to put the email in an action (the audit log
# is shared with the climbing federation). I followed the house rule. Set
# INCLUDE_EMAIL = False to match the brief; confirm with Mateusz first.
#
# Other assumptions and ambiguities:
# - "Closed group" means closed_at is set, even if the inactivity date is the earlier one.
# - Warn stays warn even with unpaid_invoices. closed_by "staff" still warns.
#   Only closed_by == "member" suppresses warnings.
# - unpaid_invoices is treated as any truthy value (a number, a list or a bool).
# - The cap counts only "delete". Anonymise and warn are uncapped. Overflow deletes are omitted, not deferred.
# - The status field is unused.
# - Ids sort natively, so mixed int/str ids would raise TypeError.
# - Missing or None email is treated as non-staff. Missing closed_at is None.
# - last_seen_at is assumed present and a datetime.date.
from datetime import date, timedelta

INACTIVE_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "Þórdís Sveinbjörnsdóttir"
INCLUDE_EMAIL = True


def _due(a):
    due = a["last_seen_at"] + timedelta(days=INACTIVE_DAYS)
    closed = a.get("closed_at")
    if closed is not None:
        due = min(due, closed + timedelta(days=CLOSED_DAYS))
    return due


def plan_purge(accounts, today):
    deletes, others = [], []
    for a in accounts:
        if a.get("litigation_hold"):
            continue
        email = (a.get("email") or "").strip().lower()
        if email.endswith(STAFF_DOMAIN):
            continue
        due = _due(a)
        if due <= today:
            act = "anonymise" if a.get("unpaid_invoices") else "delete"
        elif due <= today + timedelta(days=WARN_DAYS):
            if a.get("closed_by") == "member":
                continue
            act = "warn"
        else:
            continue
        closed = a.get("closed_at") is not None
        out = {
            "account_id": a["id"],
            "action": act,
            "due": due.isoformat(),
            "approved_by": None if act == "warn" else APPROVER,
        }
        if INCLUDE_EMAIL:
            out["email"] = a.get("email")
        if act == "delete":
            deletes.append((0 if closed else 1, due, a["id"], out))
        else:
            others.append(out)
    deletes.sort(key=lambda t: t[:3])
    result = others + [t[3] for t in deletes[:CAP]]
    result.sort(key=lambda o: o["account_id"])
    return result


# ---- tests (test_purge.py) ----
import unittest
import copy

T = date(2026, 10, 13)


def acc(i, seen=None, **kw):
    d = {"id": i, "email": f"u{i}@x.com", "status": "active",
         "last_seen_at": seen or T, "last_login": date(2000, 1, 1),
         "closed_at": None, "closed_by": None, "unpaid_invoices": 0,
         "litigation_hold": False, "tenant": "t"}
    d.update(kw)
    return d


def ago(n):
    return T - timedelta(days=n)


class PurgeTests(unittest.TestCase):
    def one(self, a):
        r = plan_purge([a], T)
        return r[0] if r else None

    def test_inactivity_boundaries(self):
        self.assertEqual(self.one(acc(1, ago(730)))["action"], "delete")
        self.assertEqual(self.one(acc(1, ago(731)))["action"], "delete")
        r = self.one(acc(1, ago(729)))
        self.assertEqual(r["action"], "warn")
        self.assertEqual(r["due"], T.isoformat() and (T + timedelta(days=1)).isoformat())

    def test_warn_window(self):
        self.assertEqual(self.one(acc(1, ago(730 - 14)))["action"], "warn")
        self.assertIsNone(self.one(acc(1, ago(730 - 15))))

    def test_closed(self):
        self.assertEqual(self.one(acc(1, closed_at=ago(30)))["action"], "delete")
        self.assertIsNone(self.one(acc(1, closed_at=ago(30 - 15))))
        self.assertEqual(self.one(acc(1, closed_at=ago(30 - 14)))["action"], "warn")

    def test_member_closed_no_warn_but_delete(self):
        self.assertIsNone(self.one(acc(1, closed_at=ago(20), closed_by="member")))
        self.assertEqual(self.one(acc(1, closed_at=ago(30), closed_by="member"))["action"], "delete")
        self.assertEqual(self.one(acc(1, closed_at=ago(20), closed_by="staff"))["action"], "warn")

    def test_precedence(self):
        self.assertIsNone(self.one(acc(1, ago(800), litigation_hold=True, unpaid_invoices=1)))
        self.assertIsNone(self.one(acc(1, ago(800), email=" A@Tidewater-Klatring.no ")))
        self.assertEqual(self.one(acc(1, ago(800), unpaid_invoices=5))["action"], "anonymise")
        self.assertEqual(self.one(acc(1, ago(720), unpaid_invoices=5))["action"], "warn")
        self.assertEqual(self.one(acc(1, ago(800), email=None))["action"], "delete")

    def test_approver(self):
        self.assertEqual(self.one(acc(1, ago(800)))["approved_by"], APPROVER)
        self.assertIsNone(self.one(acc(1, ago(720)))["approved_by"])

    def test_cap(self):
        accts = [acc(i, ago(800)) for i in range(1000, 1200)]
        accts += [acc(i, ago(800), closed_at=ago(40)) for i in range(50)]
        accts += [acc(5000 + i, ago(800), unpaid_invoices=1) for i in range(10)]
        r = plan_purge(accts, T)
        dels = [x for x in r if x["action"] == "delete"]
        self.assertEqual(len(dels), CAP)
        self.assertEqual(sum(x["action"] == "anonymise" for x in r), 10)
        ids = {x["account_id"] for x in dels}
        self.assertTrue(all(i in ids for i in range(50)))
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))

    def test_no_mutation_and_missing_keys(self):
        a = acc(1, ago(800))
        del a["closed_at"]
        b = copy.deepcopy(a)
        self.assertEqual(self.one(a)["action"], "delete")
        self.assertEqual(a, b)

    def test_ignores_last_login(self):
        self.assertIsNone(self.one(acc(1, T, last_login=ago(5000))))


if __name__ == "__main__":
    unittest.main()