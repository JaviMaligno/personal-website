import datetime as _dt
from datetime import date, timedelta

# NOTE (house rule from operator): every action dict carries the account's
# `email` in addition to the four spec keys. This deliberately deviates from
# R1/R9 ("exactly four keys", "email never in output"); the email appears only
# under the `email` key and never in exception messages. Confirm with the client.
#
# Open points (defaults used): unpaid_invoices judged by truthiness; bad data
# raises ValueError (not skipped); a single warning per window is implied by
# stateless output (the account is reported on every run inside the window);
# retention of paid invoices elsewhere is out of scope; anonymise does not
# count toward the 200 cap; id is int or str (bool rejected); "already
# processed" statuses are not handled (status ignored, caller excludes them).

APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 40
DELETE_CAP = 200


def _is_date(v):
    return isinstance(v, date) and not isinstance(v, _dt.datetime)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def plan_purge(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a date")
    cands = []
    for acc in accounts:
        aid = acc.get("id") if isinstance(acc, dict) else None
        if aid is None or isinstance(aid, bool) or not isinstance(aid, (int, str)):
            raise ValueError("invalid or missing account id")
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        seen = acc.get("last_seen_at")
        closed = acc.get("closed_at")
        if (seen is not None and not _is_date(seen)) or (
            closed is not None and not _is_date(closed)
        ):
            raise ValueError(f"invalid date field on account {aid!r}")
        dues = []
        if seen is not None:
            dues.append(seen + timedelta(days=INACTIVITY_DAYS))
        if closed is not None:
            dues.append(closed + timedelta(days=CLOSURE_DAYS))
        if not dues:
            continue
        due = min(dues)
        member_closed = closed is not None and acc.get("closed_by") == "member"
        if due <= today:
            kind = "anonymise" if acc.get("unpaid_invoices") else "delete"
        elif due <= today + timedelta(days=WARN_DAYS) and not member_closed:
            kind = "warn"
        else:
            continue
        cands.append((aid, kind, due, closed is not None, acc.get("email")))

    if len({type(c[0]) for c in cands}) > 1:
        raise ValueError("mixed account id types")

    deletes = sorted((c for c in cands if c[1] == "delete"),
                     key=lambda c: (not c[3], c[2], c[0]))
    keep = {c[0] for c in deletes[:DELETE_CAP]}
    out = []
    for aid, kind, due, _c, email in sorted(cands, key=lambda c: c[0]):
        if kind == "delete" and aid not in keep:
            continue
        out.append({
            "account_id": aid,
            "action": kind,
            "due": due.isoformat(),
            "approved_by": None if kind == "warn" else APPROVER,
            "email": email,
        })
    return out


# ----------------------------- tests -----------------------------
import copy
import json
import random
import unittest

TODAY = date(2026, 10, 13)
D = date


def mk(aid=1, **kw):
    a = {"id": aid, "email": f"user{aid}@example.com", "status": "x",
         "last_seen_at": None, "last_login": D(2026, 10, 1), "closed_at": None,
         "closed_by": "member", "unpaid_invoices": 0, "litigation_hold": False,
         "tenant": "t"}
    a.update(kw)
    return a


def one(**kw):
    return plan_purge([mk(**kw)], TODAY)


class PurgeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_inactivity_boundary(self):
        r = one(last_seen_at=D(2024, 10, 13))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        self.assertEqual(r[0]["approved_by"], APPROVER)
        r = one(last_seen_at=D(2024, 10, 14))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])

    def test_closure_boundary(self):
        self.assertEqual(one(closed_at=D(2026, 9, 13))[0]["action"], "delete")
        r = one(closed_at=D(2026, 9, 14), closed_by="staff")
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(one(closed_at=D(2026, 9, 14)), [])

    def test_earlier_due(self):
        r = one(closed_at=D(2026, 9, 1), last_seen_at=D(2026, 8, 1))
        self.assertEqual(r[0]["due"], "2026-10-01")
        r = one(closed_at=D(2026, 10, 1), last_seen_at=D(2024, 9, 1))
        self.assertEqual(r[0]["due"], "2026-09-01")

    def test_last_login_ignored_and_none_seen(self):
        self.assertEqual(one(last_login=D(2000, 1, 1)), [])

    def test_warn_window(self):
        r = one(last_seen_at=D(2024, 11, 22))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-11-22"))
        self.assertEqual(one(last_seen_at=D(2024, 11, 23)), [])
        self.assertEqual(one(closed_at=D(2026, 10, 23), closed_by="staff")[0]["action"], "warn")
        self.assertEqual(one(closed_at=D(2026, 10, 24), closed_by="staff"), [])
        self.assertEqual(one(closed_at=D(2026, 10, 23), closed_by="member"), [])

    def test_non_member_closer_warned(self):
        self.assertEqual(one(closed_at=D(2026, 10, 23), closed_by=None)[0]["action"], "warn")

    def test_member_closed_but_inactive_due_still_purged(self):
        self.assertEqual(one(closed_at=D(2026, 10, 1), last_seen_at=D(2024, 9, 1))[0]["action"], "delete")

    def test_unpaid_anonymise(self):
        r = one(last_seen_at=D(2024, 10, 13), unpaid_invoices=2)
        self.assertEqual((r[0]["action"], r[0]["due"]), ("anonymise", "2026-10-13"))
        self.assertEqual(one(last_seen_at=D(2024, 11, 1), unpaid_invoices=1)[0]["action"], "warn")

    def test_hold(self):
        self.assertEqual(one(last_seen_at=D(2020, 1, 1), litigation_hold=1), [])

    def test_staff_email(self):
        old = D(2020, 1, 1)
        for e in ["a@tidewater-klatring.no", "  A@Tidewater-Klatring.NO \n"]:
            self.assertEqual(one(last_seen_at=old, email=e), [])
        for e in ["x@mail.tidewater-klatring.no", "x@tidewater-klatring.no.evil.com", None]:
            self.assertEqual(len(one(last_seen_at=old, email=e)), 1)
        a = mk(last_seen_at=old)
        del a["email"]
        self.assertEqual(len(plan_purge([a], TODAY)), 1)
        self.assertEqual(len(one(last_seen_at=old, closed_by="staff")), 1)

    def test_cap_mixed(self):
        accs = [mk(i, closed_at=D(2026, 8, 1)) for i in range(100)]
        accs += [mk(i, last_seen_at=D(2020, 1, 1)) for i in range(100, 250)]
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)
        ids = {x["account_id"] for x in r}
        self.assertTrue(set(range(100)) <= ids)
        self.assertEqual(ids, set(range(200)))

    def test_cap_closed_only_and_not_for_others(self):
        accs = [mk(i, closed_at=D(2026, 8, 1)) for i in range(201)]
        accs += [mk(1000 + i, closed_at=D(2026, 8, 1), unpaid_invoices=1) for i in range(5)]
        accs += [mk(2000, last_seen_at=D(2024, 11, 1))]
        r = plan_purge(accs, TODAY)
        dels = [x for x in r if x["action"] == "delete"]
        self.assertEqual(len(dels), 200)
        self.assertNotIn(200, {x["account_id"] for x in dels})
        self.assertEqual(len(r), 206)

    def test_cap_due_then_id_and_held_not_counted(self):
        accs = [mk(i, last_seen_at=D(2020, 1, 1) + timedelta(days=i % 2)) for i in range(202)]
        accs += [mk(5000 + i, last_seen_at=D(2020, 1, 1), litigation_hold=True) for i in range(50)]
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)

    def test_sort_and_types(self):
        r = plan_purge([mk(10, closed_at=D(2026, 8, 1)), mk(9, closed_at=D(2026, 8, 1))], TODAY)
        self.assertEqual([x["account_id"] for x in r], [9, 10])
        r = plan_purge([mk("b", closed_at=D(2026, 8, 1)), mk("a", closed_at=D(2026, 8, 1))], TODAY)
        self.assertEqual([x["account_id"] for x in r], ["a", "b"])
        with self.assertRaises(ValueError):
            plan_purge([mk(1, closed_at=D(2026, 8, 1)), mk("a", closed_at=D(2026, 8, 1))], TODAY)

    def test_errors_do_not_leak_email(self):
        bad = mk(7, email="secret@example.com", last_seen_at="2020-01-01")
        with self.assertRaises(ValueError) as cm:
            plan_purge([bad], TODAY)
        self.assertIn("7", str(cm.exception))
        self.assertNotIn("secret@example.com", str(cm.exception))
        with self.assertRaises(ValueError):
            plan_purge([{"email": "secret@example.com"}], TODAY)
        with self.assertRaises(ValueError):
            plan_purge([mk(1, closed_at="x")], TODAY)

    def test_email_only_under_email_key(self):
        r = one(aid=3, email="secret@example.com", last_seen_at=D(2020, 1, 1))
        for x in r:
            self.assertEqual(set(x), {"account_id", "action", "due", "approved_by", "email"})
            self.assertNotIn("secret@example.com",
                             json.dumps({k: v for k, v in x.items() if k != "email"}))

    def test_pure_and_deterministic(self):
        accs = [mk(i, last_seen_at=D(2024, 10, 1) + timedelta(days=i * 3), unpaid_invoices=i % 2)
                for i in range(30)]
        snap = copy.deepcopy(accs)
        base = plan_purge(accs, TODAY)
        self.assertEqual(accs, snap)
        sh = accs[:]
        random.Random(1).shuffle(sh)
        self.assertEqual(plan_purge(sh, TODAY), base)

    def test_approver_constant(self):
        self.assertEqual(APPROVER, "Þórdís Sveinbjörnsdóttir")


if __name__ == "__main__":
    unittest.main()