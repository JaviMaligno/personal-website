"""Retention purge planner for Tidewater Climbing.

Single entry point: plan_purge(accounts, today) -> list of action dicts with
exactly four keys: account_id, action, due (ISO string), approved_by.
Tests are included at the bottom (run: python -m unittest purge).

Rules and defaults:
- Staff accounts (email stripped and casefolded ends with STAFF_DOMAIN) get no
  action, checked first. Missing email means non-staff.
- Litigation hold (truthy) means no action at all.
- Inactivity uses last_seen_at only. last_login and status are never read.
- due = last_seen_at + 730 days; if closed_at is not None,
  due = min(due, closed_at + 30 days). A future closed_at gets no special
  handling. Closed means closed_at is not None only.
- last_seen_at None/missing: a closed account uses closed_at + 30; an open
  account is skipped. There is never a fallback to last_login.
- due <= today: "delete", or "anonymise" if there are unpaid invoices
  (truthy; numbers > 0; lists/tuples non-empty).
- Not yet due and due <= today + 14: "warn", except closed_by == "member".
- Cap: at most MAX_DELETIONS_PER_RUN deletes. Anonymise is not counted unless
  CAP_COUNTS_ANONYMISE is True (then delete and anonymise share the cap).
  Over cap, winners are chosen by (closed first, earliest due, id); deferred
  accounts get no action, not even a warn. Output is then sorted by id
  (mixed int/str ids sort by (type name, value)).
- Records with a missing id, an invalid date field, or date overflow are
  skipped. Duplicate ids are processed as given, not deduplicated.
- Stateless: already-processed accounts are the caller's responsibility.
- Inputs are never mutated. Datetime values in date fields are converted via
  .date(). A non-date `today` raises TypeError.
- Note: a house rule asked for the email on every action dict, but the task
  spec requires exactly four keys and no email in the output. The spec is
  followed; the account_id lets support look up the member's email.
"""
import datetime as _dt
from datetime import date, timedelta

INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
MAX_DELETIONS_PER_RUN = 200
CAP_COUNTS_ANONYMISE = False
STAFF_DOMAIN = "@tidewater-klatring.no"
APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"


def _as_date(v):
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, date):
        return v
    raise ValueError("not a date")


def _has_unpaid(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v > 0
    return bool(v)


def _idkey(i):
    return (type(i).__name__, i if isinstance(i, (int, str)) else repr(i))


def plan_purge(accounts, today):
    if isinstance(today, _dt.datetime):
        today = today.date()
    if not isinstance(today, date):
        raise TypeError("today must be a datetime.date")
    try:
        horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    except OverflowError:
        horizon = date.max

    items = []  # (action, id, due, closed)
    for acc in accounts:
        aid = acc.get("id")
        if aid is None:
            continue
        email = acc.get("email")
        if isinstance(email, str) and email.strip().casefold().endswith(STAFF_DOMAIN):
            continue
        if acc.get("litigation_hold"):
            continue
        try:
            seen = _as_date(acc.get("last_seen_at"))
            closed_at = _as_date(acc.get("closed_at"))
            cands = []
            if seen is not None:
                cands.append(seen + timedelta(days=INACTIVITY_DAYS))
            if closed_at is not None:
                cands.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
        except (ValueError, OverflowError):
            continue
        if not cands:
            continue
        due = min(cands)
        if due <= today:
            kind = "anonymise" if _has_unpaid(acc.get("unpaid_invoices")) else "delete"
        elif due <= horizon and acc.get("closed_by") != "member":
            kind = "warn"
        else:
            continue
        items.append((kind, aid, due, closed_at is not None))

    def counted(it):
        return it[0] == "delete" or (CAP_COUNTS_ANONYMISE and it[0] == "anonymise")

    capped = sorted((it for it in items if counted(it)),
                    key=lambda it: (not it[3], it[2], _idkey(it[1])))
    losers = {id(it) for it in capped[MAX_DELETIONS_PER_RUN:]}
    kept = [it for it in items if id(it) not in losers]
    kept.sort(key=lambda it: _idkey(it[1]))
    return [{"account_id": aid, "action": kind, "due": due.isoformat(),
             "approved_by": None if kind == "warn" else APPROVER}
            for kind, aid, due, _ in kept]


# ---------------------------------------------------------------- tests
import copy
import json
import sys
import unittest
from unittest import mock

T = date(2026, 10, 13)
D = timedelta


def acc(**kw):
    base = dict(id=1, email="a@example.com", status="active",
                last_seen_at=T - D(days=100), last_login=T, closed_at=None,
                closed_by=None, unpaid_invoices=0, litigation_hold=False,
                tenant="legacy")
    base.update(kw)
    return base


def one(**kw):
    return plan_purge([acc(**kw)], T)


class PurgeTests(unittest.TestCase):
    def test_last_seen_not_login(self):
        self.assertEqual(one(last_seen_at=T - D(days=800), last_login=T)[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=T, last_login=T - D(days=900)), [])

    def test_status_ignored(self):
        self.assertEqual(one(status="deleted"), [])

    def test_boundaries(self):
        r = one(last_seen_at=T - D(days=730))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        r = one(last_seen_at=T - D(days=729))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", "2026-10-14"))

    def test_warn_window(self):
        self.assertEqual(one(last_seen_at=T - D(days=730 - 14))[0]["action"], "warn")
        self.assertEqual(one(last_seen_at=T - D(days=730 - 15)), [])

    def test_closed_earlier_due(self):
        r = one(last_seen_at=T - D(days=10), closed_at=T - D(days=40))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", (T - D(days=10)).isoformat()))
        r = one(last_seen_at=T - D(days=10), closed_at=T - D(days=20))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", (T + D(days=10)).isoformat()))

    def test_closed_by(self):
        kw = dict(last_seen_at=T - D(days=10), closed_at=T - D(days=20))
        self.assertEqual(one(closed_by="member", **kw), [])
        self.assertEqual(one(closed_by="staff", **kw)[0]["action"], "warn")
        self.assertEqual(one(closed_by=None, **kw)[0]["action"], "warn")
        kw = dict(last_seen_at=T - D(days=10), closed_at=T - D(days=40))
        self.assertEqual(one(closed_by="member", **kw)[0]["action"], "delete")

    def test_unpaid(self):
        old = T - D(days=800)
        self.assertEqual(one(last_seen_at=old, unpaid_invoices=3)[0]["action"], "anonymise")
        self.assertEqual(one(last_seen_at=old, unpaid_invoices=[1])[0]["action"], "anonymise")
        self.assertEqual(one(last_seen_at=old, unpaid_invoices=0)[0]["action"], "delete")
        self.assertEqual(one(last_seen_at=old, unpaid_invoices=[])[0]["action"], "delete")

    def test_litigation_hold(self):
        for ls in (800, 720, 100):
            self.assertEqual(one(last_seen_at=T - D(days=ls), litigation_hold=True), [])

    def test_staff(self):
        for e in ("x@tidewater-klatring.no", "X@TIDEWATER-KLATRING.NO", "  x@Tidewater-Klatring.no \n"):
            self.assertEqual(one(email=e, last_seen_at=T - D(days=900)), [])
        self.assertEqual(one(email=None, last_seen_at=T - D(days=900))[0]["action"], "delete")
        self.assertEqual(len(one(email="x@tidewater-klatring.no.evil.com", last_seen_at=T - D(days=900))), 1)

    def test_keys_and_no_email(self):
        r = plan_purge([acc(id=1, last_seen_at=T - D(days=900), email="secret@example.com"),
                        acc(id=2, last_seen_at=T - D(days=725))], T)
        for a in r:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
        self.assertNotIn("secret", json.dumps(r))
        self.assertNotIn("@", json.dumps(r))

    def test_cap(self):
        accs = [acc(id=i, last_seen_at=T - D(days=730), closed_at=T - D(days=30)) for i in range(1, 151)]
        accs += [acc(id=i, last_seen_at=T - D(days=1000)) for i in range(151, 251)]
        accs.reverse()
        r = plan_purge(accs, T)
        ids = [a["account_id"] for a in r]
        self.assertEqual(ids, list(range(1, 201)))
        self.assertTrue(all(a["action"] == "delete" for a in r))

    def test_anonymise_cap(self):
        accs = [acc(id=i, last_seen_at=T - D(days=900)) for i in range(1, 251)]
        accs += [acc(id=i, last_seen_at=T - D(days=900), unpaid_invoices=1) for i in range(251, 301)]
        r = plan_purge(accs, T)
        self.assertEqual(sum(a["action"] == "delete" for a in r), 200)
        self.assertEqual(sum(a["action"] == "anonymise" for a in r), 50)
        with mock.patch.dict(globals(), {"CAP_COUNTS_ANONYMISE": True}):
            r = plan_purge(accs, T)
        self.assertEqual(len(r), 200)

    def test_approver(self):
        self.assertEqual(APPROVER, "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir")
        self.assertEqual(one(last_seen_at=T - D(days=800))[0]["approved_by"], APPROVER)
        w = one(last_seen_at=T - D(days=725))[0]
        self.assertIn("approved_by", w)
        self.assertIsNone(w["approved_by"])

    def test_no_mutation(self):
        accs = [acc(id=2, last_seen_at=T - D(days=900)), acc(id=1, last_seen_at=T - D(days=725))]
        before = copy.deepcopy(accs)
        plan_purge(accs, T)
        self.assertEqual(accs, before)

    def test_tenant_ignored(self):
        a = one(last_seen_at=T - D(days=800), tenant="x")
        b = one(last_seen_at=T - D(days=800), tenant="y")
        self.assertEqual(a, b)

    def test_json_and_sorting(self):
        r = plan_purge([acc(id=10, last_seen_at=T - D(days=900)),
                        acc(id=2, last_seen_at=T - D(days=900)),
                        acc(id="b", last_seen_at=T - D(days=900)),
                        acc(id="a", last_seen_at=T - D(days=900))], T)
        self.assertEqual([a["account_id"] for a in r], [2, 10, "a", "b"])
        s = json.dumps(r, ensure_ascii=False)
        self.assertIn("\u00de\u00f3rd\u00eds", s)

    def test_none_last_seen(self):
        self.assertEqual(one(last_seen_at=None), [])
        self.assertEqual(one(last_seen_at=None, last_login=T - D(days=900)), [])
        r = one(last_seen_at=None, closed_at=T - D(days=30))
        self.assertEqual((r[0]["action"], r[0]["due"]), ("delete", "2026-10-13"))
        r = one(last_seen_at=None, closed_at=T - D(days=20), closed_by="staff")
        self.assertEqual(r[0]["action"], "warn")

    def test_misc(self):
        with self.assertRaises(TypeError):
            plan_purge([], "2026-10-13")
        self.assertEqual(plan_purge([{"email": None, "last_seen_at": T - D(days=900)}], T), [])
        self.assertEqual(one(last_seen_at=date.max), [])
        self.assertEqual(one(last_seen_at=_dt.datetime(2020, 1, 1))[0]["action"], "delete")


if __name__ == "__main__":
    unittest.main()