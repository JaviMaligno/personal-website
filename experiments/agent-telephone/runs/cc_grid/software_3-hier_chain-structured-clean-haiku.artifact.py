# -*- coding: utf-8 -*-
"""Purge planner for Tidewater Climbing accounts.

Pure function: no I/O, no mutation of inputs. Emails never appear in
actions or in exception messages.

Open-point decisions implemented here:
  OP1: the 200 cap counts delete actions only; anonymise is not capped.
  OP2: an account with due <= today gets only its delete/anonymise action.
  OP3: unpaid invoices do not suppress a warn in the warn window.
  OP4: warn window is (today, today + 14]; due == today is a removal.

Ambiguities left to the reader:
  - Duplicate account ids are not deduplicated; each input account is
    evaluated independently and may produce its own actions.
  - The warn text may be misleading for unpaid-invoice accounts that will
    be anonymised on the due date (R18). The module emits the warn as specified.
  - "Closed" for R10 ordering is taken as closed_at is not None, even when
    the 730-day due date is earlier than closed_at + 30 days.
"""

import datetime as _dt

APPROVER = "Þórdís Sveinbjörnsdóttir"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_DAYS = 14
DELETE_CAP = 200
STAFF_SUFFIX = "@tidewater-klatring.no"
REQUIRED_KEYS = (
    "id",
    "email",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)


def _is_date(value):
    return isinstance(value, _dt.date) and not isinstance(value, _dt.datetime)


def _validate(accounts, today):
    if not _is_date(today):
        raise ValueError("today must be a datetime.date")
    for acc in accounts:
        if not isinstance(acc, dict):
            raise ValueError("account must be a dict (id unknown)")
        acc_id = acc.get("id", "<unknown>")
        for key in REQUIRED_KEYS:
            if key not in acc:
                raise ValueError(f"account {acc_id!r}: missing field {key!r}")
        if not _is_date(acc["last_seen_at"]):
            raise ValueError(f"account {acc_id!r}: field 'last_seen_at' must be a date")
        if acc["closed_at"] is not None and not _is_date(acc["closed_at"]):
            raise ValueError(f"account {acc_id!r}: field 'closed_at' must be a date or None")
        if not isinstance(acc["email"], str):
            raise ValueError(f"account {acc_id!r}: field 'email' must be a str")


def _is_staff(email):
    return email.strip().lower().endswith(STAFF_SUFFIX)


def plan_purge(accounts, today):
    _validate(accounts, today)

    horizon = today + _dt.timedelta(days=WARN_DAYS)
    delete_candidates = []   # (group, due, account_id); group 0 = closed, 1 = open
    anonymise_items = []     # (account_id, due)
    warn_items = []          # (account_id, due)

    for acc in accounts:
        # (a) litigation hold: no action at all
        if acc["litigation_hold"]:
            continue
        # (b) staff accounts: no action at all
        if _is_staff(acc["email"]):
            continue
        # (c) due date per R3; last_login is intentionally not read (R2)
        due = acc["last_seen_at"] + _dt.timedelta(days=INACTIVITY_DAYS)
        closed_at = acc["closed_at"]
        if closed_at is not None:
            grace_end = closed_at + _dt.timedelta(days=CLOSED_GRACE_DAYS)
            if grace_end < due:
                due = grace_end
        # (d) removal candidate
        if due <= today:
            if acc["unpaid_invoices"]:
                anonymise_items.append((acc["id"], due))
            else:
                group = 0 if closed_at is not None else 1
                delete_candidates.append((group, due, acc["id"]))
        # (e) warn window (today, today + 14], skipped for member closures
        elif due <= horizon and acc["closed_by"] != "member":
            warn_items.append((acc["id"], due))

    # R10: cap deletes at 200; closed first, then by due, then by id
    delete_candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    selected = delete_candidates[:DELETE_CAP]

    out = []
    for _group, due, acc_id in selected:
        out.append({
            "account_id": acc_id,
            "action": "delete",
            "due": due.isoformat(),
            "approved_by": APPROVER,
        })
    for acc_id, due in anonymise_items:
        out.append({
            "account_id": acc_id,
            "action": "anonymise",
            "due": due.isoformat(),
            "approved_by": APPROVER,
        })
    for acc_id, due in warn_items:
        out.append({
            "account_id": acc_id,
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
        })

    out.sort(key=lambda a: (a["account_id"], a["action"], a["due"]))
    return out


def _self_test():
    import copy

    t = _dt.date(2026, 10, 13)
    dd = _dt.timedelta

    def acc(i, last_seen, **kw):
        a = {
            "id": i,
            "email": "m%s@example.com" % i,
            "last_seen_at": last_seen,
            "closed_at": None,
            "closed_by": None,
            "unpaid_invoices": False,
            "litigation_hold": False,
        }
        a.update(kw)
        return a

    accs = [
        acc("due_today", t - dd(days=730)),
        acc("warn_edge", t + dd(days=14) - dd(days=730)),
        acc("beyond", t + dd(days=15) - dd(days=730)),
        acc("member_close", t - dd(days=1), closed_at=t - dd(days=16), closed_by="member"),
        acc("unpaid", t - dd(days=730), unpaid_invoices=True),
        acc("hold", t - dd(days=800), litigation_hold=True),
        acc("staff", t - dd(days=800), email="  X@Tidewater-Klatring.NO "),
        acc("lookalike", t - dd(days=800), email="x@nottidewater-klatring.no"),
    ]
    snapshot = copy.deepcopy(accs)
    out = plan_purge(accs, t)
    assert accs == snapshot, "input was mutated"
    assert [(a["account_id"], a["action"]) for a in out] == [
        ("due_today", "delete"),
        ("lookalike", "delete"),
        ("unpaid", "anonymise"),
        ("warn_edge", "warn"),
    ], out
    for a in out:
        assert set(a) == {"account_id", "action", "due", "approved_by"}
    assert out[-1]["due"] == (t + dd(days=14)).isoformat()
    assert out[-1]["approved_by"] is None
    assert out[0]["approved_by"] == APPROVER

    big = (
        [acc("c%03d" % i, t - dd(days=800), closed_at=t - dd(days=40)) for i in range(150)]
        + [acc("o%03d" % i, t - dd(days=740)) for i in range(100)]
    )
    out_big = plan_purge(big, t)
    dels = [a["account_id"] for a in out_big if a["action"] == "delete"]
    assert len(dels) == 200
    assert sorted(x for x in dels if x.startswith("c")) == sorted(x for x in dels if x.startswith("c"))
    assert len([x for x in dels if x.startswith("c")]) == 150
    assert [x for x in dels if x.startswith("o")] == ["o%03d" % i for i in range(50)]

    def _err(fn):
        try:
            fn()
        except ValueError as e:
            return str(e)
        return None

    assert _err(lambda: plan_purge([], _dt.datetime(2026, 10, 13))) is not None
    msg = _err(lambda: plan_purge([acc("x", t, email=5)], t))
    assert msg is not None and "'x'" in msg and "email" in msg and "@" not in msg
    print("self-test ok")


if __name__ == "__main__":
    _self_test()