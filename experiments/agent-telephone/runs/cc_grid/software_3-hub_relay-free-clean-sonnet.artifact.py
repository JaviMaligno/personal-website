"""Tidewater Climbing GDPR member-account purge planner (standard library only).

Run the embedded tests with: python purge.py  (split the Tests class into test_purge.py if preferred).

Note: a house rule asked for the email on every action dict, but the task spec
(exactly four keys, email never in output, acceptance criterion 9) forbids it, so
the spec is followed. Support can look accounts up by account_id.

Assumptions: the 200 cap covers deletes only; accounts with no dates get no action;
email, last_seen_at, closed_at, unpaid_invoices, litigation_hold are required keys
(closed_by only when closed_at is set).

Open questions for the client (Mateusz):
 (a) Should the 200 cap also cover anonymise actions (assumed no)?
 (b) What are the possible `status` values / how do we exclude already-processed accounts?
 (c) What is the type of unpaid_invoices (count or list)?
 (d) Is skipping accounts with no last_seen_at desired?
"""
import datetime as dt
import unittest

DPO = "Þórdís Sveinbjörnsdóttir"  # \u00de\u00f3\u00f0... precomposed form
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSURE_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200
_REQUIRED = ("id", "email", "last_seen_at", "closed_at", "unpaid_invoices", "litigation_hold")


def _already_processed(account):
    """Return True if the account was already anonymised or deleted.

    Awaiting client confirmation of the status values; currently nothing is
    treated as processed.
    """
    return False


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _validate(accounts):
    seen = set()
    for a in accounts:
        if "id" not in a:
            raise KeyError("account without 'id' key")
        aid = a["id"]
        for k in _REQUIRED:
            if k not in a:
                raise KeyError(f"account {aid!r}: missing required key {k!r}")
        if a["closed_at"] is not None and "closed_by" not in a:
            raise KeyError(f"account {aid!r}: missing required key 'closed_by'")
        if aid in seen:
            raise ValueError(f"duplicate account id {aid!r}")
        seen.add(aid)


def _action(aid, action, due):
    return {
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO,
    }


def plan_purge(accounts, today):
    _validate(accounts)
    out = []
    candidates = []  # (group, due, id, closed)
    horizon = today + dt.timedelta(days=WARN_DAYS)
    for a in accounts:
        if _already_processed(a) or _is_staff(a["email"]) or a["litigation_hold"]:
            continue
        dues = []
        if a["last_seen_at"] is not None:
            dues.append(a["last_seen_at"] + dt.timedelta(days=INACTIVITY_DAYS))
        closed = a["closed_at"] is not None
        if closed:
            dues.append(a["closed_at"] + dt.timedelta(days=CLOSURE_DAYS))
        if not dues:
            continue
        due = min(dues)
        aid = a["id"]
        if due <= today:
            if a["unpaid_invoices"]:
                out.append(_action(aid, "anonymise", due))
            else:
                candidates.append((0 if closed else 1, due, aid))
        elif due <= horizon:
            if closed and a["closed_by"] == "member":
                continue
            out.append(_action(aid, "warn", due))
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    for _, due, aid in candidates[:DELETE_CAP]:
        out.append(_action(aid, "delete", due))
    out.sort(key=lambda x: x["account_id"])
    return out


# ---------------------------------------------------------------- tests
TODAY = dt.date(2026, 10, 13)
D = dt.date
TD = dt.timedelta
EMAIL = "member@example.com"


def acc(i, **kw):
    a = dict(id=i, email=EMAIL, status="active", last_seen_at=TODAY, last_login=None,
             closed_at=None, closed_by=None, unpaid_invoices=0, litigation_hold=False)
    a.update(kw)
    return a


def run(*accs):
    return plan_purge(list(accs), TODAY)


class Tests(unittest.TestCase):
    def one(self, **kw):
        r = run(acc(1, **kw))
        return r[0] if r else None

    def test_constant(self):
        self.assertEqual(DPO, "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir")

    def test_1_2_3(self):
        r = self.one(last_seen_at=D(2024, 10, 13))
        self.assertEqual((r["action"], r["due"], r["approved_by"]), ("delete", "2026-10-13", DPO))
        r = self.one(last_seen_at=D(2024, 10, 14))
        self.assertEqual((r["action"], r["due"], r["approved_by"]), ("warn", "2026-10-14", None))
        self.assertEqual(self.one(last_seen_at=D(2024, 10, 27))["action"], "warn")
        self.assertIsNone(self.one(last_seen_at=D(2024, 10, 28)))

    def test_4_5(self):
        r = self.one(closed_at=D(2026, 9, 13), closed_by="staff")
        self.assertEqual((r["action"], r["due"]), ("delete", "2026-10-13"))
        r = self.one(closed_at=D(2026, 9, 14), closed_by="staff")
        self.assertEqual((r["action"], r["due"]), ("warn", "2026-10-14"))
        self.assertIsNone(self.one(closed_at=D(2026, 9, 14), closed_by="member"))
        self.assertEqual(self.one(closed_at=D(2026, 9, 13), closed_by="member")["action"], "delete")

    def test_6_inactivity_earlier(self):
        r = self.one(last_seen_at=D(2024, 1, 1), closed_at=D(2026, 9, 1), closed_by="staff")
        self.assertEqual(r["due"], "2025-12-31")

    def test_7_unpaid(self):
        for inv in (2, ["x"]):
            r = self.one(last_seen_at=D(2024, 1, 1), unpaid_invoices=inv)
            self.assertEqual((r["action"], r["due"], r["approved_by"]), ("anonymise", "2025-12-31", DPO))

    def test_8_skips(self):
        old, soon = D(2024, 1, 1), D(2024, 10, 20)
        for ls in (old, soon):
            self.assertIsNone(self.one(last_seen_at=ls, litigation_hold=True))
            for e in ("Anna@Tidewater-Klatring.no", "  a@tidewater-klatring.no "):
                self.assertIsNone(self.one(last_seen_at=ls, email=e))
        self.assertEqual(self.one(last_seen_at=old, email="x@nottidewater-klatring.no")["action"], "delete")
        self.assertEqual(self.one(last_seen_at=old, email=None)["action"], "delete")
        a = acc(1, last_seen_at=old, tenant="x", last_login=TODAY)
        b = acc(1, last_seen_at=old)
        del b["last_login"]
        self.assertEqual(run(a), run(b))

    def test_9_shape(self):
        for r in run(acc(1, last_seen_at=D(2024, 1, 1)), acc(2, last_seen_at=D(2024, 10, 20))):
            self.assertEqual(set(r), {"account_id", "action", "due", "approved_by"})
            self.assertIsInstance(r["due"], str)
            self.assertNotIn(EMAIL, r.values())

    def test_10_cap_priority(self):
        accs = [acc(f"c{i:03}", closed_at=TODAY - TD(days=40 + i), closed_by="staff") for i in range(30)]
        accs += [acc(f"i{i:03}", last_seen_at=D(2023, 1, 1) + TD(days=i)) for i in range(220)]
        r = run(*accs)
        ids = {x["account_id"] for x in r if x["action"] == "delete"}
        self.assertEqual(len(r), 200)
        self.assertEqual(ids, {f"c{i:03}" for i in range(30)} | {f"i{i:03}" for i in range(170)})

    def test_11_closed_only(self):
        accs = [acc(i, closed_at=D(2026, 1, 1) + TD(days=i // 5), closed_by="member") for i in range(205)]
        accs.append(acc(999, last_seen_at=D(2020, 1, 1)))
        r = run(*accs)
        self.assertEqual({x["account_id"] for x in r}, set(range(200)))

    def test_12_anonymise_and_warn(self):
        accs = [acc(i, last_seen_at=D(2023, 1, 1)) for i in range(250)]
        accs += [acc(1000 + i, last_seen_at=D(2023, 1, 1), unpaid_invoices=1) for i in range(40)]
        accs += [acc(2000 + i, last_seen_at=D(2024, 10, 20)) for i in range(5)]
        r = run(*accs)
        n = lambda k: sum(x["action"] == k for x in r)
        self.assertEqual((n("delete"), n("anonymise"), n("warn")), (200, 40, 5))

    def test_13_sorted_pure(self):
        import copy
        import random
        accs = [acc(i, last_seen_at=D(2023, 1, 1) + TD(days=i * 40)) for i in range(30)]
        random.Random(1).shuffle(accs)
        snap = copy.deepcopy(accs)
        r1, r2 = plan_purge(accs, TODAY), plan_purge(accs, TODAY)
        self.assertEqual(r1, r2)
        self.assertEqual(accs, snap)
        self.assertEqual([x["account_id"] for x in r1], sorted(x["account_id"] for x in r1))
        self.assertEqual(plan_purge([], TODAY), [])

    def test_14_validation(self):
        self.assertIsNone(self.one(last_seen_at=None, last_login=D(2020, 1, 1)))
        a = acc("abc")
        del a["litigation_hold"]
        with self.assertRaises(KeyError) as c:
            run(a)
        self.assertIn("abc", str(c.exception))
        self.assertNotIn(EMAIL, str(c.exception))
        with self.assertRaises(ValueError):
            run(acc(1), acc(1))
        b = acc(2, closed_at=TODAY)
        del b["closed_by"]
        with self.assertRaises(KeyError):
            run(b)


if __name__ == "__main__":
    unittest.main()