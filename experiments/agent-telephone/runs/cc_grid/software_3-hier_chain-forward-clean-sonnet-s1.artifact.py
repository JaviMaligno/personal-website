"""Purge planner for Tidewater Climbing (GDPR clean-up).

Entry point: plan_purge(accounts, today). Standard library only.
The tests are at the bottom, so the module runs standalone with `python purge.py`.
They have NOT been run: this agent had no execution tool.

CONFLICT (needs a human answer): the house rule says every action should carry
the account's `email`. The client brief says never to put the email in any
action, because the audit log is shared with the climbing federation. Putting
personal data there would be a GDPR leak, so actions contain exactly
account_id, action, due and approved_by. No agent message can waive the
client's requirement.

DECISIONS
1. Precedence: litigation_hold (truthy) skips the account; then a staff email
   skips it; then due date; then action.
2. Staff match: email.strip().lower().endswith("@tidewater-klatring.no").
   A missing or non-string email is treated as non-staff (flagged below).
3. due = min(last_seen_at + 730d, closed_at + 30d if closed). due <= today gives
   delete, or anonymise if unpaid_invoices is truthy (count, list or bool; a
   negative or odd value is just truthiness).
4. Warn when today < due <= today + 14 (inclusive), except when
   closed_by == "member" and closed_at is set. A missing closed_by counts as
   not-member, so the member is warned. Anonymise-bound accounts are warned too.
5. Cap of 200 applies to deletes only; anonymise is uncapped. Over the cap the
   order is closed accounts first, then earliest due, then id. Dropped deletes
   are omitted (not warned, not downgraded) and reappear on the next run.
6. Output is sorted by id (stable). Mixed int/str ids raise TypeError.
   Duplicate ids are not deduplicated. Inputs are not mutated.
   tenant and last_login are ignored.
7. Validation raises ValueError/TypeError naming the account id. A missing id,
   a bad `today`, or a non-date or datetime last_seen_at/closed_at all raise.
   datetime.datetime is rejected explicitly. Dates are validated only for
   accounts not skipped by hold or staff.

OPEN QUESTIONS for Mateusz
- The house rule (email in actions) conflicts with your brief (no email). We
  followed the brief. Please confirm that support should follow up some other way.
- Should anonymise count towards the 200 cap? The brief says "deletions"; we
  assumed no.
- Should anonymise-bound accounts get a warning? We assumed yes.
- Is warning when closed_by is missing right? We assumed yes.
- Should accounts with a missing or None email be treated as non-staff? We assumed yes.
- Should deletions dropped by the cap get a warning or be downgraded? We assumed neither.
- Do invoices need to be kept five years only for unpaid invoices, or should all
  invoices be kept? We followed the brief: only unpaid ones trigger anonymise.
- Should a closed account with an unpaid invoice still be anonymised after 30
  days? We assumed yes.
"""
import copy
import datetime as dt
import unittest

APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"  # NFC
STAFF_SUFFIX = "@tidewater-klatring.no"
CAP = 200


def _is_date(v):
    return isinstance(v, dt.date) and not isinstance(v, dt.datetime)


def plan_purge(accounts, today):
    if not _is_date(today):
        raise TypeError(f"today must be a datetime.date, got {today!r}")
    deletes, others = [], []
    for a in accounts:
        if "id" not in a:
            raise ValueError("account without id")
        aid = a["id"]
        if a.get("litigation_hold"):
            continue
        email = a.get("email")
        if isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX):
            continue
        seen, closed = a.get("last_seen_at"), a.get("closed_at")
        if not _is_date(seen):
            raise ValueError(f"account {aid!r}: last_seen_at must be a date, got {seen!r}")
        if closed is not None and not _is_date(closed):
            raise ValueError(f"account {aid!r}: closed_at must be None or a date, got {closed!r}")
        due = seen + dt.timedelta(days=730)
        if closed is not None:
            due = min(due, closed + dt.timedelta(days=30))
        if due <= today:
            if a.get("unpaid_invoices"):
                others.append(_act(aid, "anonymise", due))
            else:
                deletes.append(((closed is None, due, aid), _act(aid, "delete", due)))
        elif due <= today + dt.timedelta(days=14):
            if not (a.get("closed_by") == "member" and closed is not None):
                others.append(_act(aid, "warn", due))
    deletes.sort(key=lambda t: t[0])
    result = others + [act for _, act in deletes[:CAP]]
    result.sort(key=lambda r: r["account_id"])
    return result


def _act(aid, action, due):
    return {"account_id": aid, "action": action, "due": due.isoformat(),
            "approved_by": None if action == "warn" else APPROVER}


# ---------------------------------------------------------------- tests
T = dt.date(2026, 10, 13)
D = dt.timedelta


def acc(**kw):
    base = dict(id=1, email="m@example.com", status="active", last_seen_at=T,
                last_login=None, closed_at=None, closed_by=None,
                unpaid_invoices=0, litigation_hold=False, tenant="x")
    base.update(kw)
    return base


def one(**kw):
    return plan_purge([acc(**kw)], T)


class PurgeTests(unittest.TestCase):
    def test_due_today_deleted_not_warned(self):
        r = one(last_seen_at=T - D(730))
        self.assertEqual([x["action"] for x in r], ["delete"])
        self.assertEqual(r[0]["due"], T.isoformat())

    def test_warn_window(self):
        r = one(last_seen_at=T - D(730) + D(14))
        self.assertEqual(r[0]["action"], "warn")
        self.assertIsNone(r[0]["approved_by"])
        self.assertIn("approved_by", r[0])
        self.assertEqual(one(last_seen_at=T - D(730) + D(15)), [])

    def test_member_vs_staff_closed(self):
        self.assertEqual(one(closed_at=T - D(10), closed_by="member"), [])
        self.assertEqual(one(closed_at=T - D(30), closed_by="member")[0]["action"], "delete")
        r = one(closed_at=T - D(20), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", (T + D(10)).isoformat()))
        self.assertEqual(one(closed_at=T - D(20))[0]["action"], "warn")

    def test_closed_long_ago_recent_seen(self):
        self.assertEqual(one(closed_at=T - D(500))[0]["action"], "delete")

    def test_closed_earlier_than_inactivity(self):
        r = one(last_seen_at=T - D(700), closed_at=T - D(17), closed_by="staff")
        self.assertEqual((r[0]["action"], r[0]["due"]), ("warn", (T + D(13)).isoformat()))

    def test_hold_and_staff(self):
        self.assertEqual(one(last_seen_at=T - D(900), unpaid_invoices=3, litigation_hold=True), [])
        for e in ("A@Tidewater-Klatring.NO", "  a@tidewater-klatring.no \n"):
            self.assertEqual(one(email=e, last_seen_at=T - D(900)), [])

    def test_missing_email_is_member(self):
        a = acc(last_seen_at=T - D(900)); del a["email"]
        self.assertEqual(plan_purge([a], T)[0]["action"], "delete")

    def test_unpaid(self):
        self.assertEqual(one(last_seen_at=T - D(900), unpaid_invoices=2)[0]["action"], "anonymise")
        self.assertEqual(one(last_seen_at=T - D(725), unpaid_invoices=[1])[0]["action"], "warn")

    def test_cap(self):
        accs = [acc(id=i, last_seen_at=T - D(731 + i)) for i in range(1, 201)]
        accs += [acc(id=1000 + i, closed_at=T - D(30)) for i in range(5)]
        accs += [acc(id=2000 + i, last_seen_at=T - D(900), unpaid_invoices=1) for i in range(10)]
        r = plan_purge(accounts=accs, today=T)
        dels = {x["account_id"] for x in r if x["action"] == "delete"}
        self.assertEqual(len(dels), 200)
        self.assertEqual(dels, set(range(6, 201)) | {1000 + i for i in range(5)})
        self.assertEqual(sum(x["action"] == "anonymise" for x in r), 10)
        self.assertEqual([x["account_id"] for x in r], sorted(x["account_id"] for x in r))

    def test_cap_tie_by_id(self):
        accs = [acc(id=i, last_seen_at=T - D(800)) for i in range(250)]
        ids = [x["account_id"] for x in plan_purge(accs, T)]
        self.assertEqual(ids, list(range(200)))

    def test_exactly_200(self):
        accs = [acc(id=i, last_seen_at=T - D(800)) for i in range(200)]
        self.assertEqual(len(plan_purge(accs, T)), 200)

    def test_sorted_no_mutation_empty(self):
        accs = [acc(id=3, last_seen_at=T - D(800)), acc(id=1, last_seen_at=T - D(800))]
        before = copy.deepcopy(accs)
        r = plan_purge(accs, T)
        self.assertEqual([x["account_id"] for x in r], [1, 3])
        self.assertEqual(accs, before)
        self.assertEqual(plan_purge([], T), [])

    def test_last_login_ignored(self):
        a = acc(last_seen_at=T - D(800)); del a["last_login"]
        b = acc(last_seen_at=T - D(800), last_login=T - D(5000))
        c = acc(last_seen_at=T, last_login=T - D(5000))
        self.assertEqual(plan_purge([a], T), plan_purge([b], T))
        self.assertEqual(plan_purge([c], T), [])

    def test_output_shape(self):
        r = one(last_seen_at=T - D(800), email="secret@example.com")[0]
        self.assertEqual(set(r), {"account_id", "action", "due", "approved_by"})
        self.assertIsInstance(r["due"], str)
        self.assertNotIn("secret", repr(r))
        import unicodedata
        self.assertEqual(r["approved_by"], unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir"))

    def test_malformed(self):
        for kw in (dict(last_seen_at=None), dict(last_seen_at="2020-01-01"),
                   dict(closed_at="2020-01-01"),
                   dict(last_seen_at=dt.datetime(2020, 1, 1)),
                   dict(closed_at=dt.datetime(2020, 1, 1))):
            with self.assertRaises((ValueError, TypeError)):
                one(**kw)
        a = acc(); del a["last_seen_at"]
        with self.assertRaises(ValueError):
            plan_purge([a], T)
        with self.assertRaises(TypeError):
            plan_purge([], "2026-10-13")
        with self.assertRaises(TypeError):
            plan_purge([], dt.datetime(2026, 10, 13))

    def test_skipped_not_validated(self):
        self.assertEqual(one(litigation_hold=True, last_seen_at=None), [])


if __name__ == "__main__":
    unittest.main()