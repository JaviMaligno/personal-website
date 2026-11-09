"""Tidewater Climbing GDPR member-account purge planner.

plan_purge(accounts, today) returns a list of action dicts, one per account at
most, sorted ascending by account_id. Pure: no clock, no input mutation.

Action keys: account_id, action ("delete" | "anonymise" | "warn"), due (ISO
date string), approved_by (DPO name for delete/anonymise, None for warn), and
email. NOTE: the email key is a deployment house rule (support follow-up). It
deviates from the original spec items R1 (exactly four keys) and R9 (email
never in any action); confirm with the client. The email is never put in
errors or logs.

Rules in brief:
- Inactivity due = last_seen_at + INACTIVITY_DAYS (last_login is never read).
- Closure due = closed_at + CLOSED_DAYS (only when closed_at is not None).
- due = the earlier applicable date. Due when due <= today; the original due
  date is kept even if long past.
- Warn when today < due <= today + WARN_DAYS, unless closed_at is set and
  closed_by == "member". Warns are stateless (may repeat daily) and uncapped.
- Unpaid invoices: a number > 0, or a non-empty collection. Such due accounts
  are "anonymise" instead of "delete".
- Truthy litigation_hold or a staff email (exact suffix STAFF_DOMAIN,
  case-insensitive, whitespace stripped) -> no action at all.
- At most DELETE_CAP deletes per run; closed accounts first, then others;
  within each group earliest due, then lowest id. Anonymise/warn are uncapped.
- `status` and `tenant` are ignored; closure is determined by closed_at only.
  Already-anonymised accounts are re-returned as "anonymise" on every run
  unless the caller filters them out.
- last_seen_at None: closed accounts use closed_at + CLOSED_DAYS alone;
  non-closed accounts get no action (never delete on a guess).
- Missing required keys raise ValueError naming the account id and key.
"""
import datetime
import json
import logging
import unittest

DELETE_CAP = 200
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
DPO_NAME = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"

REQUIRED_KEYS = ("id", "email", "last_seen_at", "closed_at",
                 "unpaid_invoices", "litigation_hold")

log = logging.getLogger(__name__)


def _validate(acc):
    aid = acc.get("id", "<unknown>") if isinstance(acc, dict) else "<unknown>"
    for key in REQUIRED_KEYS:
        if key not in acc:
            raise ValueError(f"account {aid!r}: missing required key {key!r}")
    if acc["closed_at"] is not None and "closed_by" not in acc:
        raise ValueError(f"account {aid!r}: missing required key 'closed_by'")


def _is_staff(email):
    if not isinstance(email, str) or not email.strip():
        return False
    return email.strip().lower().endswith(STAFF_DOMAIN)


def _has_unpaid(value):
    if isinstance(value, (int, float)):
        return value > 0
    try:
        return len(value) > 0
    except TypeError:
        return bool(value)


def plan_purge(accounts, today):
    deletes, others = [], []
    for acc in accounts:
        _validate(acc)
        aid = acc["id"]
        if _is_staff(acc["email"]):
            continue
        if acc["litigation_hold"]:
            continue
        closed_at = acc["closed_at"]
        last_seen = acc["last_seen_at"]
        candidates = []
        if last_seen is not None:
            candidates.append(last_seen + datetime.timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            candidates.append(closed_at + datetime.timedelta(days=CLOSED_DAYS))
        if not candidates:
            log.info("account %r skipped: never seen and not closed", aid)
            continue
        due = min(candidates)
        if due <= today:
            if _has_unpaid(acc["unpaid_invoices"]):
                others.append((aid, "anonymise", due, acc["email"]))
            else:
                deletes.append((closed_at is None, due, aid, acc["email"]))
        elif due <= today + datetime.timedelta(days=WARN_DAYS):
            if closed_at is not None and acc["closed_by"] == "member":
                continue
            others.append((aid, "warn", due, acc["email"]))

    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    if len(deletes) > DELETE_CAP:
        log.info("delete cap reached: %d deletions deferred",
                 len(deletes) - DELETE_CAP)
        deletes = deletes[:DELETE_CAP]
    entries = others + [(aid, "delete", due, email)
                        for _, due, aid, email in deletes]

    result = [{
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_NAME,
        "email": email,
    } for aid, action, due, email in entries]
    result.sort(key=lambda a: a["account_id"])
    return result


# ---------------------------------------------------------------- tests
TODAY = datetime.date(2026, 10, 13)
D = datetime.timedelta


def mk(id=1, email="m@example.com", last_seen=None, closed_at=None,
       closed_by="staff", unpaid=0, hold=False, **extra):
    a = {"id": id, "email": email,
         "last_seen_at": last_seen if last_seen is not None else TODAY,
         "closed_at": closed_at, "closed_by": closed_by,
         "unpaid_invoices": unpaid, "litigation_hold": hold}
    a.update(extra)
    return a


def acts(*accs):
    return plan_purge(list(accs), TODAY)


class DeleteTests(unittest.TestCase):
    def test_inactivity_boundary(self):
        r = acts(mk(1, last_seen=TODAY - D(730)), mk(2, last_seen=TODAY - D(729)))
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(1, "delete"), (2, "warn")])
        self.assertEqual(r[0]["due"], TODAY.isoformat())

    def test_closed_boundary(self):
        r = acts(mk(1, closed_at=TODAY - D(30)), mk(2, closed_at=TODAY - D(29)))
        self.assertEqual(r[0]["action"], "delete")
        self.assertEqual(r[1]["action"], "warn")

    def test_overdue_keeps_original_due(self):
        ls = TODAY - D(1000)
        r = acts(mk(1, last_seen=ls))
        self.assertEqual(r[0]["due"], (ls + D(730)).isoformat())
        self.assertEqual(r[0]["action"], "delete")

    def test_approved_by_and_keys(self):
        a = acts(mk(1, last_seen=TODAY - D(800)))[0]
        self.assertEqual(a["approved_by"], "Tordis Svenbjorn Dottir")
        self.assertEqual(set(a), {"account_id", "action", "due",
                                  "approved_by", "email"})

    def test_unpaid_anonymise(self):
        for unpaid in (2, [1], {"x": 1}):
            a = acts(mk(1, last_seen=TODAY - D(800), unpaid=unpaid))[0]
            self.assertEqual(a["action"], "anonymise")
            self.assertEqual(a["approved_by"], DPO_NAME)
        for unpaid in (0, [], None):
            self.assertEqual(
                acts(mk(1, last_seen=TODAY - D(800), unpaid=unpaid))[0]["action"],
                "delete")

    def test_hold_and_staff_skipped(self):
        old = TODAY - D(900)
        self.assertEqual(acts(mk(1, last_seen=old, hold=True),
                              mk(2, last_seen=old, hold=1)), [])
        for e in ("a@tidewater-klatring.no", "  A@Tidewater-Klatring.NO \n"):
            self.assertEqual(acts(mk(1, email=e, last_seen=old)), [])
        self.assertEqual(len(acts(mk(1, email="a@x.tidewater-klatring.no", last_seen=old))), 1)
        self.assertEqual(len(acts(mk(1, email=None, last_seen=old))), 1)
        self.assertEqual(len(acts(mk(1, email="", last_seen=old))), 1)

    def test_closed_earlier_due(self):
        a = acts(mk(1, last_seen=TODAY - D(700), closed_at=TODAY - D(40)))[0]
        self.assertEqual(a["due"], (TODAY - D(10)).isoformat())
        self.assertEqual(a["action"], "delete")

    def test_closed_last_seen_none(self):
        a = acts(dict(mk(1, closed_at=TODAY - D(30)), last_seen_at=None))[0]
        self.assertEqual(a["action"], "delete")
        self.assertEqual(a["due"], TODAY.isoformat())

    def test_never_seen_not_closed_skipped(self):
        with self.assertLogs(__name__, "INFO") as cm:
            r = acts(dict(mk(1, email="secret@example.com"), last_seen_at=None))
        self.assertEqual(r, [])
        self.assertNotIn("secret@example.com", "".join(cm.output))

    def test_future_dates(self):
        self.assertEqual(acts(mk(1, last_seen=TODAY + D(5))), [])
        r = acts(mk(1, closed_at=TODAY + D(5)))
        self.assertEqual(r, [])
        r = acts(mk(1, closed_at=TODAY - D(20)))
        self.assertEqual(r[0]["action"], "warn")

    def test_last_login_ignored(self):
        old, new = TODAY - D(2000), TODAY
        self.assertEqual(acts(mk(1, last_login=old)), [])
        self.assertEqual(acts(mk(1, last_seen=TODAY - D(800), last_login=new))[0]["action"], "delete")

    def test_tenant_and_status_ignored(self):
        old = TODAY - D(800)
        base = acts(mk(1, last_seen=old))
        self.assertEqual(acts(mk(1, last_seen=old, tenant="x", status="active")), base)
        self.assertEqual(acts(mk(1, last_seen=old, status="anonymised"))[0]["action"], "delete")


class WarnTests(unittest.TestCase):
    def test_window(self):
        r = acts(mk(1, last_seen=TODAY - D(730 - 14)),
                 mk(2, last_seen=TODAY - D(730 - 15)),
                 mk(3, last_seen=TODAY - D(730 - 1)))
        self.assertEqual([a["account_id"] for a in r], [1, 3])
        self.assertTrue(all(a["action"] == "warn" and a["approved_by"] is None for a in r))
        self.assertEqual(r[0]["due"], (TODAY + D(14)).isoformat())

    def test_member_vs_staff_closed(self):
        c = TODAY - D(20)
        self.assertEqual(acts(mk(1, closed_at=c, closed_by="member")), [])
        self.assertEqual(acts(mk(1, closed_at=c, closed_by="staff"))[0]["action"], "warn")

    def test_closed_by_ignored_when_open(self):
        r = acts(mk(1, last_seen=TODAY - D(720), closed_by="member"))
        self.assertEqual(r[0]["action"], "warn")

    def test_unpaid_member_closed_no_warn(self):
        self.assertEqual(acts(mk(1, closed_at=TODAY - D(20), closed_by="member", unpaid=3)), [])

    def test_unpaid_still_warned(self):
        self.assertEqual(acts(mk(1, last_seen=TODAY - D(720), unpaid=3))[0]["action"], "warn")


class CapTests(unittest.TestCase):
    def test_closed_priority(self):
        accs = [mk(i, last_seen=TODAY - D(2000)) for i in range(240)]
        accs += [mk(1000 + i, closed_at=TODAY - D(30)) for i in range(10)]
        r = plan_purge(accs, TODAY)
        self.assertEqual(len(r), 200)
        ids = {a["account_id"] for a in r}
        self.assertTrue(all(1000 + i in ids for i in range(10)))

    def test_within_group_order(self):
        accs = [mk(i, last_seen=TODAY - D(1000 + i)) for i in range(201)]
        ids = {a["account_id"] for a in plan_purge(accs, TODAY)}
        self.assertNotIn(0, ids)
        self.assertEqual(len(ids), 200)
        accs = [mk(i, last_seen=TODAY - D(900)) for i in range(201)]
        ids = {a["account_id"] for a in plan_purge(accs, TODAY)}
        self.assertNotIn(200, ids)

    def test_counts(self):
        mkd = lambda n, start, **kw: [mk(start + i, last_seen=TODAY - D(900), **kw) for i in range(n)]
        self.assertEqual(len(plan_purge(mkd(200, 0), TODAY)), 200)
        self.assertEqual(len(plan_purge(mkd(201, 0), TODAY)), 200)
        self.assertEqual(len(plan_purge(mkd(150, 0) + mkd(100, 1000, unpaid=1), TODAY)), 250)

    def test_held_staff_not_counted(self):
        accs = [mk(i, last_seen=TODAY - D(900)) for i in range(200)]
        accs += [mk(500 + i, last_seen=TODAY - D(900), hold=True) for i in range(20)]
        accs += [mk(700 + i, email="s@tidewater-klatring.no", last_seen=TODAY - D(900)) for i in range(20)]
        self.assertEqual(len(plan_purge(accs, TODAY)), 200)

    def test_warns_uncapped(self):
        accs = [mk(i, last_seen=TODAY - D(900)) for i in range(200)]
        accs += [mk(1000 + i, last_seen=TODAY - D(720)) for i in range(50)]
        self.assertEqual(len(plan_purge(accs, TODAY)), 250)

    def test_deferred_log_aggregate(self):
        accs = [mk(i, email=f"p{i}@example.com", last_seen=TODAY - D(900)) for i in range(205)]
        with self.assertLogs(__name__, "INFO") as cm:
            plan_purge(accs, TODAY)
        out = "".join(cm.output)
        self.assertIn("5", out)
        self.assertNotIn("@example.com", out)


class GeneralTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(plan_purge([], TODAY), [])

    def test_sorted_and_shuffle_stable(self):
        accs = [mk(i, last_seen=TODAY - D(800 + i % 3)) for i in (5, 3, 9, 1, 7)]
        r = plan_purge(accs, TODAY)
        self.assertEqual([a["account_id"] for a in r], [1, 3, 5, 7, 9])
        self.assertEqual(plan_purge(accs[::-1], TODAY), r)

    def test_string_ids_sorted(self):
        r = plan_purge([mk("b", last_seen=TODAY - D(900)), mk("a", last_seen=TODAY - D(900))], TODAY)
        self.assertEqual([a["account_id"] for a in r], ["a", "b"])

    def test_json_and_no_mutation(self):
        accs = [mk(1, last_seen=TODAY - D(900)), mk(2, last_seen=TODAY - D(720))]
        import copy
        snap = copy.deepcopy(accs)
        r = plan_purge(accs, TODAY)
        self.assertEqual(accs, snap)
        json.dumps(r)

    def test_errors_validate(self):
        for key in REQUIRED_KEYS:
            a = mk(7, email="leak@example.com")
            del a[key]
            with self.assertRaises(ValueError) as cm:
                plan_purge([a], TODAY)
            self.assertIn(key, str(cm.exception))
            self.assertNotIn("leak@example.com", str(cm.exception))
            if key != "id":
                self.assertIn("7", str(cm.exception))

    def test_missing_hold_fails_closed(self):
        a = mk(1, last_seen=TODAY - D(900))
        del a["litigation_hold"]
        with self.assertRaises(ValueError):
            plan_purge([a], TODAY)

    def test_closed_by_required_only_when_closed(self):
        a = mk(1, closed_at=TODAY - D(5))
        del a["closed_by"]
        with self.assertRaises(ValueError):
            plan_purge([a], TODAY)
        b = mk(1)
        del b["closed_by"]
        self.assertEqual(plan_purge([b], TODAY), [])


if __name__ == "__main__":
    unittest.main()