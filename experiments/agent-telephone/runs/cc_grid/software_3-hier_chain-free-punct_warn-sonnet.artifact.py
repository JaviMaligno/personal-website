# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-azxjbm1t/gdpr_purge.py =====
"""GDPR purge planner for Tidewater Climbing (Tidewater Klatring) member accounts.

Rule numbers (a-g) below refer to the client's per-account precedence list.

NOT VERIFIED: I had no tool access, so neither file was executed. The intended
command is `python3 -m unittest -v` from the working directory. Run it before
relying on this.

Assumptions:
- Actions carry exactly four keys and never the email. The deployment's house
  rule says every action should also carry `email`, but the task spec and the
  GDPR purpose say otherwise. I followed the spec; please confirm.
- Dates must be exactly datetime.date (datetime.datetime is rejected).
- The warn window is evaluated with day arithmetic: 0 < (due - today) <= 14.
- Unpaid invoices are only evaluated for accounts that are due for deletion.
- Missing "id" raises ValueError; duplicate ids raise ValueError (id only).

Open points for the client:
- Should the cap also cover anonymise? Anonymise is a row-level UPDATE that
  holds locks, so if the lock-up is about write volume it should be counted.
  Implemented: anonymise is uncapped.
- Real status vocabulary for already-anonymised accounts (ANONYMISED_STATUSES).
- Should accounts with unpaid invoices be warned? Implemented: yes.
- Should closed_by == "member" suppress the warn when closed_at is not set?
  Implemented: yes, regardless.
- Missing last_seen_at: implemented as no inactivity-based due date.
- Rejecting datetime.datetime values: deliberate; confirm.
- approved_by is None for warn (key present) versus omitting the key.
- "Closed" cap priority is defined as closed_at is not None.
- Skatteetaten five-year invoice retention: this module only flags anonymise;
  it does not enforce retention.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)

RETENTION_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"
DPO = "Þórdís Sveinbjörnsdóttir"
# Rule c: statuses meaning "already anonymised or deleted" (vocabulary unconfirmed).
ANONYMISED_STATUSES = frozenset({"anonymised", "anonymized", "deleted"})


@dataclass(frozen=True)
class PurgeReport:
    """Result of a planning run: actions plus ids deferred by the delete cap."""

    actions: list[dict[str, Any]]
    deferred_ids: list[Any]

    @property
    def deferred_count(self) -> int:
        return len(self.deferred_ids)


def _validate_date(value: Any, field_name: str, allow_none: bool) -> dt.date | None:
    """Accept exactly datetime.date (datetimes and strings rejected)."""
    if value is None:
        if allow_none:
            return None
        raise TypeError(f"{field_name} must be datetime.date, got NoneType")
    if type(value) is not dt.date:
        raise TypeError(f"{field_name} must be datetime.date, got {type(value).__name__}")
    return value


def _is_staff(email: Any) -> bool:
    """Rule b: staff email suffix match, case/whitespace-insensitive."""
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_EMAIL_SUFFIX)


def _has_unpaid(value: Any) -> bool:
    """Interpret unpaid_invoices; unsupported types raise TypeError."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    raise TypeError(f"unpaid_invoices has unsupported type {type(value).__name__}")


def _is_already_anonymised(status: Any) -> bool:
    """Rule c: status shows account is already anonymised or deleted."""
    return isinstance(status, str) and status.strip().casefold() in ANONYMISED_STATUSES


def _effective_due(account: Mapping[str, Any]) -> dt.date | None:
    """Rule d: earlier of last_seen_at+730d and closed_at+30d; never last_login."""
    acc_id = account.get("id")
    last_seen = _validate_date(account.get("last_seen_at"), f"last_seen_at (account {acc_id!r})", True)
    closed = _validate_date(account.get("closed_at"), f"closed_at (account {acc_id!r})", True)
    candidates: list[dt.date] = []
    for base, days in ((last_seen, RETENTION_DAYS), (closed, CLOSED_GRACE_DAYS)):
        if base is None:
            continue
        try:
            candidates.append(base + dt.timedelta(days=days))
        except OverflowError:
            pass
    return min(candidates) if candidates else None


def _action(account_id: Any, action: str, due: dt.date) -> dict[str, Any]:
    return {
        "account_id": account_id,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO,
    }


def plan_purge_report(accounts: list[Mapping[str, Any]], today: dt.date) -> PurgeReport:
    """Plan actions (rules a-g) and apply the delete cap; input is not mutated."""
    _validate_date(today, "today", False)

    seen: set[Any] = set()
    for acc in accounts:
        if "id" not in acc:
            raise ValueError("account is missing 'id'")
        acc_id = acc["id"]
        if acc_id in seen:
            raise ValueError(f"duplicate account id {acc_id!r}")
        seen.add(acc_id)

    actions: list[dict[str, Any]] = []
    candidates: list[tuple[int, dt.date, Any]] = []  # (group, due, id)

    for acc in accounts:
        if acc.get("litigation_hold", False):  # rule a
            continue
        if _is_staff(acc.get("email")):  # rule b
            continue
        if _is_already_anonymised(acc.get("status")):  # rule c
            continue
        due = _effective_due(acc)  # rule d
        if due is None:
            continue
        acc_id = acc["id"]
        if due <= today:  # rule e
            if _has_unpaid(acc.get("unpaid_invoices")):
                actions.append(_action(acc_id, "anonymise", due))
            else:
                group = 0 if acc.get("closed_at") is not None else 1
                candidates.append((group, due, acc_id))
        elif (due - today).days <= WARN_WINDOW_DAYS:  # rule f
            if acc.get("closed_by") != "member":
                actions.append(_action(acc_id, "warn", due))

    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    kept = candidates[:DELETE_CAP]
    deferred = candidates[DELETE_CAP:]
    actions.extend(_action(i, "delete", d) for _, d, i in kept)
    actions.sort(key=lambda a: a["account_id"])
    return PurgeReport(actions=actions, deferred_ids=sorted(i for _, _, i in deferred))


def plan_purge(accounts: list[Mapping[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    """Return the action list; logs the deferred-delete count (ids only)."""
    report = plan_purge_report(accounts, today)
    if report.deferred_count > 0:
        logger.warning(
            "Deferred %d deletes due to cap of %d; account ids: %s",
            report.deferred_count, DELETE_CAP, report.deferred_ids,
        )
    return report.actions


# ===== FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-azxjbm1t/test_gdpr_purge.py =====
import copy
import datetime as dt
import json
import random
import unittest

import gdpr_purge as g
from gdpr_purge import plan_purge, plan_purge_report

TODAY = dt.date(2026, 10, 13)


def D(n):
    """TODAY shifted by n days."""
    return TODAY + dt.timedelta(days=n)


def make(i, **kw):
    acc = {
        "id": i, "email": "member@example.com", "status": "active",
        "last_seen_at": D(-10), "last_login": D(-10), "closed_at": None,
        "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False,
    }
    acc.update(kw)
    return acc


def acts(accounts, today=TODAY):
    return plan_purge(accounts, today)


def kinds(accounts):
    return {a["account_id"]: a["action"] for a in acts(accounts)}


class Spy(dict):
    accessed: list

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.accessed = []

    def __getitem__(self, key):
        self.accessed.append(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self.accessed.append(key)
        return super().get(key, default)

    def __contains__(self, key):
        self.accessed.append(key)
        return super().__contains__(key)


class TestConstantsAndHelpers(unittest.TestCase):
    def test_dpo_code_points(self):
        self.assertEqual(g.DPO, "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir")

    def test_constants(self):
        self.assertEqual(
            (g.RETENTION_DAYS, g.CLOSED_GRACE_DAYS, g.WARN_WINDOW_DAYS, g.DELETE_CAP, g.STAFF_EMAIL_SUFFIX),
            (730, 30, 14, 200, "@tidewater-klatring.no"))

    def test_has_unpaid(self):
        for v in (3, True, [1], 0.5, {"a": 1}, (1,), {1}):
            self.assertTrue(g._has_unpaid(v), v)
        for v in (0, False, [], None, 0.0, {}, ()):
            self.assertFalse(g._has_unpaid(v), v)
        with self.assertRaises(TypeError):
            g._has_unpaid("yes")

    def test_is_staff(self):
        for e in ("a@tidewater-klatring.no", "A@TIDEWATER-KLATRING.NO", "  a@Tidewater-Klatring.no \n"):
            self.assertTrue(g._is_staff(e))
        for e in ("x@tidewater-klatring.no.evil.com", "x@sub.tidewater-klatring.no",
                  "x@notidewater-klatring.no", None, 5, ""):
            self.assertFalse(g._is_staff(e), e)

    def test_already_anonymised(self):
        for s in ("anonymised", " Anonymized ", "DELETED"):
            self.assertTrue(g._is_already_anonymised(s))
        for s in ("active", None, "", 3):
            self.assertFalse(g._is_already_anonymised(s))

    def test_validate_date(self):
        self.assertEqual(g._validate_date(TODAY, "f", False), TODAY)
        self.assertIsNone(g._validate_date(None, "f", True))
        for bad in (None, "2026-01-01", dt.datetime(2026, 1, 1)):
            with self.assertRaises(TypeError):
                g._validate_date(bad, "f", False)

    def test_effective_due(self):
        self.assertEqual(g._effective_due(make(1, last_seen_at=D(-100))), D(630))
        self.assertIsNone(g._effective_due(make(1, last_seen_at=None)))
        self.assertEqual(g._effective_due({"id": 1, "last_seen_at": None, "closed_at": D(-5)}), D(25))

    def test_effective_due_overflow(self):
        acc = make(1, last_seen_at=dt.date.max, closed_at=D(-1))
        self.assertEqual(g._effective_due(acc), D(29))
        self.assertIsNone(g._effective_due(make(1, last_seen_at=dt.date.max)))


class TestInactivity(unittest.TestCase):
    def test_exact_730_deletes(self):
        r = acts([make(1, last_seen_at=D(-730))])
        self.assertEqual(r, [{"account_id": 1, "action": "delete", "due": TODAY.isoformat(),
                              "approved_by": g.DPO}])

    def test_729_warns(self):
        r = acts([make(1, last_seen_at=D(-729))])
        self.assertEqual(r[0]["action"], "warn")
        self.assertEqual(r[0]["due"], D(1).isoformat())
        self.assertIsNone(r[0]["approved_by"])

    def test_last_login_irrelevant(self):
        self.assertEqual(acts([make(1, last_login=D(-5000), last_seen_at=D(-10))]), [])
        self.assertEqual(kinds([make(1, last_login=D(0), last_seen_at=D(-900))]), {1: "delete"})

    def test_missing_last_seen(self):
        acc = make(1, last_seen_at=None)
        self.assertEqual(acts([acc]), [])
        del acc["last_seen_at"]
        self.assertEqual(acts([acc]), [])

    def test_past_due_iso(self):
        r = acts([make(1, last_seen_at=D(-800))])
        self.assertEqual(r[0]["due"], D(-70).isoformat())


class TestClosed(unittest.TestCase):
    def test_30_days_deletes(self):
        self.assertEqual(kinds([make(1, closed_at=D(-30), closed_by="member")]), {1: "delete"})

    def test_29_days(self):
        self.assertEqual(kinds([make(1, closed_at=D(-29), closed_by="staff")]), {1: "warn"})
        self.assertEqual(kinds([make(1, closed_at=D(-29), closed_by="member")]), {})

    def test_member_suppression_without_closed_at(self):
        acc = make(1, last_seen_at=D(-720), closed_by="member")
        self.assertEqual(acts([acc]), [])
        acc["closed_by"] = "staff"
        self.assertEqual(kinds([acc]), {1: "warn"})

    def test_inactivity_sooner(self):
        r = acts([make(1, last_seen_at=D(-740), closed_at=D(-31))])
        self.assertEqual(r[0]["due"], D(-10).isoformat())

    def test_closed_without_last_seen(self):
        self.assertEqual(kinds([make(1, last_seen_at=None, closed_at=D(-40))]), {1: "delete"})


class TestWarnWindow(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(kinds([make(1, last_seen_at=D(-716))]), {1: "warn"})   # due +14
        self.assertEqual(kinds([make(1, last_seen_at=D(-715))]), {})            # due +15
        self.assertEqual(kinds([make(1, last_seen_at=D(-730))]), {1: "delete"})  # due 0
        self.assertEqual(kinds([make(1, last_seen_at=D(-729))]), {1: "warn"})   # due +1

    def test_warn_due_future(self):
        r = acts([make(1, last_seen_at=D(-716))])
        self.assertEqual(r[0]["due"], D(14).isoformat())


class TestUnpaid(unittest.TestCase):
    def test_anonymise_forms(self):
        for v in (3, True, [1]):
            r = acts([make(1, last_seen_at=D(-800), unpaid_invoices=v)])
            self.assertEqual(r[0]["action"], "anonymise")
            self.assertEqual(r[0]["approved_by"], g.DPO)

    def test_not_unpaid(self):
        for v in (0, False, [], None):
            self.assertEqual(kinds([make(1, last_seen_at=D(-800), unpaid_invoices=v)]), {1: "delete"})

    def test_missing_key(self):
        acc = make(1, last_seen_at=D(-800))
        del acc["unpaid_invoices"]
        self.assertEqual(kinds([acc]), {1: "delete"})

    def test_warn_with_unpaid(self):
        self.assertEqual(kinds([make(1, last_seen_at=D(-720), unpaid_invoices=2)]), {1: "warn"})

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            acts([make(1, last_seen_at=D(-800), unpaid_invoices="x")])


class TestSkips(unittest.TestCase):
    def test_hold_all_cases(self):
        old = D(-800)
        cases = [
            make(1, last_seen_at=old, litigation_hold=True),
            make(2, last_seen_at=old, unpaid_invoices=1, litigation_hold=1),
            make(3, last_seen_at=D(-720), litigation_hold=True),
            make(4, closed_at=D(-40), closed_by="staff", litigation_hold=True),
        ]
        self.assertEqual(acts(cases), [])

    def test_hold_missing_key(self):
        acc = make(1, last_seen_at=D(-800))
        del acc["litigation_hold"]
        self.assertEqual(kinds([acc]), {1: "delete"})

    def test_hold_and_staff_with_junk_dates(self):
        accs = [make(1, last_seen_at="junk", litigation_hold=True),
                make(2, closed_at=dt.datetime(2020, 1, 1), email="a@tidewater-klatring.no")]
        self.assertEqual(acts(accs), [])

    def test_staff_excluded(self):
        for i, e in enumerate(("A@TIDEWATER-KLATRING.NO", " a@tidewater-klatring.no ", "a@Tidewater-Klatring.No")):
            self.assertEqual(acts([make(i, email=e, last_seen_at=D(-900))]), [])

    def test_lookalikes_not_staff(self):
        for i, e in enumerate(("x@tidewater-klatring.no.evil.com", "x@sub.tidewater-klatring.no",
                               "x@notidewater-klatring.no", None)):
            self.assertEqual(kinds([make(i, email=e, last_seen_at=D(-900))]), {i: "delete"})
        acc = make(9, last_seen_at=D(-900))
        del acc["email"]
        self.assertEqual(kinds([acc]), {9: "delete"})

    def test_status(self):
        for i, s in enumerate(("anonymised", "Anonymized", " DELETED ")):
            self.assertEqual(acts([make(i, status=s, last_seen_at=D(-900))]), [])
        self.assertEqual(kinds([make(1, status="active", last_seen_at=D(-900))]), {1: "delete"})
        acc = make(2, last_seen_at=D(-900))
        del acc["status"]
        self.assertEqual(kinds([acc]), {2: "delete"})


class TestOutput(unittest.TestCase):
    def _mixed(self):
        return [make(1, email="del@example.com", last_seen_at=D(-800)),
                make(2, email="anon@example.com", last_seen_at=D(-800), unpaid_invoices=1),
                make(3, email="warn@example.com", last_seen_at=D(-720))]

    def test_keys_and_no_email(self):
        r = acts(self._mixed())
        self.assertEqual(len(r), 3)
        for a in r:
            self.assertEqual(set(a), {"account_id", "action", "due", "approved_by"})
        text = json.dumps(r)
        for e in ("del@example.com", "anon@example.com", "warn@example.com", "@example.com"):
            self.assertNotIn(e, text)

    def test_dpo_and_warn_none(self):
        r = {a["account_id"]: a for a in acts(self._mixed())}
        self.assertEqual(r[1]["approved_by"], "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir")
        self.assertEqual(r[2]["approved_by"], g.DPO)
        self.assertIn("approved_by", r[3])
        self.assertIsNone(r[3]["approved_by"])

    def test_json_roundtrip(self):
        r = acts(self._mixed())
        self.assertEqual(json.loads(json.dumps(r, ensure_ascii=False)), r)
        self.assertEqual(json.loads(json.dumps(r)), r)

    def test_return_is_plain_list(self):
        self.assertIs(type(acts([])), list)

    def test_log_has_no_email(self):
        accs = [make(i, email=f"u{i}@example.com", last_seen_at=D(-800)) for i in range(201)]
        with self.assertLogs("gdpr_purge", "WARNING") as cm:
            acts(accs)
        out = "\n".join(cm.output)
        self.assertNotIn("@example.com", out)
        self.assertIn("200", out)

    def test_no_log_when_not_deferred(self):
        with self.assertNoLogs("gdpr_purge", "WARNING"):
            acts([make(1, last_seen_at=D(-800))])

    def test_error_messages_no_email(self):
        with self.assertRaises(TypeError) as cm:
            acts([make(1, email="secret@example.com", last_seen_at="2020-01-01")])
        self.assertNotIn("secret@example.com", str(cm.exception))
        self.assertNotIn("2020-01-01", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            acts([make(5, email="secret@example.com"), make(5, email="secret@example.com")])
        self.assertNotIn("secret", str(cm.exception))


class TestCap(unittest.TestCase):
    def deletable(self, n, start=1):
        return [make(i, last_seen_at=D(-800)) for i in range(start, start + n)]

    def test_exactly_200(self):
        rep = plan_purge_report(self.deletable(200), TODAY)
        self.assertEqual(len(rep.actions), 200)
        self.assertEqual(rep.deferred_count, 0)

    def test_201(self):
        rep = plan_purge_report(self.deletable(201), TODAY)
        self.assertEqual(len(rep.actions), 200)
        self.assertEqual(rep.deferred_count, 1)
        self.assertEqual(rep.deferred_ids, [201])

    def test_report_frozen(self):
        rep = plan_purge_report([], TODAY)
        with self.assertRaises(Exception):
            rep.actions = []

    def test_closed_priority(self):
        inactive = [make(i, last_seen_at=D(-(900 + i))) for i in range(1, 151)]
        closed = [make(i, closed_at=D(-31)) for i in range(151, 251)]
        rep = plan_purge_report(inactive + closed, TODAY)
        ids = {a["account_id"] for a in rep.actions}
        self.assertEqual(len(ids), 200)
        self.assertTrue(set(range(151, 251)) <= ids)
        self.assertEqual(ids & set(range(1, 151)), set(range(51, 151)))
        self.assertEqual(rep.deferred_ids, list(range(1, 51)))

    def test_tie_break_by_id(self):
        accs = self.deletable(250)
        random.Random(3).shuffle(accs)
        rep = plan_purge_report(accs, TODAY)
        self.assertEqual(rep.deferred_ids, list(range(201, 251)))

    def test_deferred_no_action(self):
        rep = plan_purge_report(self.deletable(205), TODAY)
        out_ids = {a["account_id"] for a in rep.actions}
        self.assertTrue(out_ids.isdisjoint(rep.deferred_ids))

    def test_anonymise_uncapped(self):
        accs = self.deletable(200) + [make(i, last_seen_at=D(-800), unpaid_invoices=1) for i in range(1000, 1050)]
        rep = plan_purge_report(accs, TODAY)
        k = [a["action"] for a in rep.actions]
        self.assertEqual((k.count("delete"), k.count("anonymise")), (200, 50))
        self.assertEqual(rep.deferred_count, 0)

    def test_warns_unaffected(self):
        accs = self.deletable(201) + [make(i, last_seen_at=D(-720)) for i in range(1000, 1003)]
        k = [a["action"] for a in acts(accs)]
        self.assertEqual((k.count("delete"), k.count("warn")), (200, 3))

    def test_held_do_not_consume_slots(self):
        held = [make(i, last_seen_at=D(-800), litigation_hold=True) for i in range(1000, 1005)]
        rep = plan_purge_report(self.deletable(200) + held, TODAY)
        self.assertEqual(len(rep.actions), 200)
        self.assertEqual(rep.deferred_count, 0)

    def test_deferred_ids_sorted_and_logged(self):
        accs = self.deletable(203)
        with self.assertLogs("gdpr_purge", "WARNING") as cm:
            plan_purge(accs, TODAY)
        self.assertIn("[201, 202, 203]", cm.output[0])


class TestSorting(unittest.TestCase):
    def test_sorted_with_high_id_closed(self):
        accs = [make(i, last_seen_at=D(-800)) for i in range(1, 201)]
        accs.append(make(999, closed_at=D(-31)))
        random.Random(5).shuffle(accs)
        rep = plan_purge_report(accs, TODAY)
        ids = [a["account_id"] for a in rep.actions]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(ids[-1], 999)
        self.assertEqual(rep.deferred_ids, [200])

    def test_interleaved(self):
        accs = [make(3, last_seen_at=D(-720)), make(1, last_seen_at=D(-800)),
                make(2, last_seen_at=D(-800), unpaid_invoices=1)]
        r = acts(accs)
        self.assertEqual([(a["account_id"], a["action"]) for a in r],
                         [(1, "delete"), (2, "anonymise"), (3, "warn")])

    def test_string_ids(self):
        r = acts([make("b", last_seen_at=D(-800)), make("a", last_seen_at=D(-800))])
        self.assertEqual([a["account_id"] for a in r], ["a", "b"])

    def test_determinism(self):
        accs = [make(i, last_seen_at=D(-(600 + i * 3)), closed_at=D(-i) if i % 5 == 0 else None,
                     unpaid_invoices=i % 7 == 0) for i in range(1, 120)]
        base = acts(accs)
        for seed in range(5):
            s = accs[:]
            random.Random(seed).shuffle(s)
            self.assertEqual(acts(s), base)


class TestInputHandling(unittest.TestCase):
    def test_no_mutation(self):
        accs = [make(i, last_seen_at=D(-800 + i)) for i in (5, 3, 9, 1)]
        before = copy.deepcopy(accs)
        acts(accs)
        self.assertEqual(accs, before)
        self.assertEqual([a["id"] for a in accs], [5, 3, 9, 1])

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            acts([make(1), make(1)])

    def test_missing_id(self):
        acc = make(1)
        del acc["id"]
        with self.assertRaises(ValueError):
            acts([acc])

    def test_bad_dates(self):
        now = dt.datetime(2026, 10, 13)
        with self.assertRaises(TypeError):
            acts([], now)
        with self.assertRaises(TypeError):
            acts([], None)
        with self.assertRaises(TypeError):
            acts([], "2026-10-13")
        for field in ("last_seen_at", "closed_at"):
            for bad in (dt.datetime(2020, 1, 1), "2020-01-01"):
                with self.assertRaises(TypeError, msg=(field, bad)):
                    acts([make(1, **{field: bad})])


class TestTenantAndLastLogin(unittest.TestCase):
    def _accounts(self):
        return [make(1, last_seen_at=D(-800)), make(2, last_seen_at=D(-720)),
                make(3, last_seen_at=D(-800), unpaid_invoices=1), make(4, closed_at=D(-29), closed_by="staff")]

    def test_tenant_irrelevant(self):
        plain = self._accounts()
        base = acts(plain)
        for t in (None, "x", 42, ""):
            with_t = [dict(a, tenant=t) for a in plain]
            self.assertEqual(acts(with_t), base)

    def test_tenant_and_last_login_never_read(self):
        spies = [Spy(a, tenant="x") for a in self._accounts()]
        spies.append(Spy(make(5, litigation_hold=True, tenant=None)))
        spies.append(Spy(make(6, email="s@tidewater-klatring.no", tenant=None)))
        self.assertEqual(acts(spies), acts(self._accounts()))
        for s in spies:
            self.assertNotIn("tenant", s.accessed)
            self.assertNotIn("last_login", s.accessed)


if __name__ == "__main__":
    unittest.main()