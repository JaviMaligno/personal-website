"""Retention purge planner.

plan_purge(accounts, today) is a pure function: no clock, I/O, mutation or logging.

Assumptions (PM defaults, implemented as stated):
- `status` is ignored.
- Accounts headed for "anonymise" are also warned in the warn window.
- The 200 cap counts delete actions only; anonymise and warn are uncapped.
- Warn is suppressed whenever closed_by == "member".
- Malformed accounts (non-dict, missing id, non-date date fields, errors while
  evaluating) are skipped, so no destructive action is taken for them (R17).
- A datetime.datetime is treated as malformed; only datetime.date is accepted.
- Mixed, non-comparable id types fall back to ordering by (type name, str(id)).

Conflict flagged for the client: a house rule asks for the member's `email` on
every action dict, but R1 requires exactly four keys and R9 forbids the email
anywhere in the output. The spec is followed and no email is emitted; support
can look the member up by account_id. Please confirm which rule should win.
"""
import json
import random
from copy import deepcopy
from datetime import date, datetime, timedelta

DPO_NAME = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY = timedelta(days=730)
CLOSURE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)
DELETE_CAP = 200


def _d(v):
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    raise ValueError("bad date")


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_DOMAIN)


def _sorted(items, key):
    try:
        return sorted(items, key=key)
    except TypeError:
        return sorted(items, key=lambda x: (type(key(x)).__name__, str(key(x))))


def _evaluate(a, today):
    """Return (id, action, due, closed) or None."""
    if not isinstance(a, dict):
        return None
    if a.get("litigation_hold"):
        return None
    if _is_staff(a.get("email")):
        return None
    if "id" not in a or a["id"] is None:
        return None
    last_seen = _d(a.get("last_seen_at"))
    closed_at = _d(a.get("closed_at"))
    terms = []
    if last_seen is not None:
        terms.append(last_seen + INACTIVITY)
    if closed_at is not None:
        terms.append(closed_at + CLOSURE)
    if not terms:
        return None
    due = min(terms)
    if due <= today:
        action = "anonymise" if a.get("unpaid_invoices") else "delete"
    elif due <= today + WARN_WINDOW:
        if a.get("closed_by") == "member":
            return None
        action = "warn"
    else:
        return None
    return a["id"], action, due, closed_at is not None


def _out(id_, action, due):
    return {
        "account_id": id_,
        "action": action,
        "due": due.isoformat(),
        "approved_by": None if action == "warn" else DPO_NAME,
    }


def plan_purge(accounts, today):
    deletes, others = [], []
    for a in accounts or []:
        try:
            r = _evaluate(a, today)
        except Exception:
            continue
        if r is None:
            continue
        (deletes if r[1] == "delete" else others).append(r)

    closed = _sorted([r for r in deletes if r[3]], lambda r: (r[2], r[0]))
    inactive = _sorted([r for r in deletes if not r[3]], lambda r: (r[2], r[0]))
    selected = (closed + inactive)[:DELETE_CAP]

    result = [_out(i, act, due) for i, act, due, _ in selected + others]
    return _sorted(result, lambda x: x["account_id"])


# ---------------------------------------------------------------- tests
TODAY = date(2026, 10, 13)


def _acc(id_=1, **kw):
    base = {
        "id": id_, "email": "m%s@example.com" % id_, "status": "active",
        "last_seen_at": None, "last_login": None, "closed_at": None,
        "closed_by": None, "unpaid_invoices": 0, "litigation_hold": False,
    }
    base.update(kw)
    return base


def _one(**kw):
    r = plan_purge([_acc(**kw)], TODAY)
    return r[0] if r else None


def test_empty():
    assert plan_purge([], TODAY) == []


def test_inactivity_boundaries():
    r = _one(last_seen_at=date(2024, 10, 13))
    assert r == {"account_id": 1, "action": "delete", "due": "2026-10-13", "approved_by": DPO_NAME}
    assert _one(last_seen_at=date(2024, 10, 12))["due"] == "2026-10-12"


def test_closed_and_min():
    assert _one(closed_at=date(2026, 9, 13))["action"] == "delete"
    r = _one(last_seen_at=date(2024, 10, 1), closed_at=date(2026, 10, 10))
    assert r["due"] == "2026-10-01" and r["action"] == "delete"


def test_no_dates_no_action():
    assert _one() is None


def test_last_login_ignored():
    assert _one(last_login=date(2000, 1, 1)) is None
    assert _one(last_seen_at=date(2026, 1, 1), last_login=date(2000, 1, 1)) is None


def test_warn_window():
    assert _one(last_seen_at=date(2024, 10, 14))["action"] == "warn"
    r = _one(last_seen_at=date(2024, 10, 27))
    assert r["action"] == "warn" and r["approved_by"] is None and "approved_by" in r
    assert _one(last_seen_at=date(2024, 10, 28)) is None


def test_warn_closed_by():
    assert _one(closed_at=date(2026, 9, 20), closed_by="staff")["action"] == "warn"
    assert _one(closed_at=date(2026, 9, 20), closed_by="member") is None


def test_unpaid_anonymise():
    for u in (2, [{"n": 1}]):
        r = _one(last_seen_at=date(2024, 10, 1), unpaid_invoices=u)
        assert r["action"] == "anonymise" and r["approved_by"] == DPO_NAME
    assert _one(last_seen_at=date(2024, 10, 20), unpaid_invoices=1)["action"] == "warn"
    assert _one(last_seen_at=date(2024, 10, 1), unpaid_invoices=[])["action"] == "delete"


def test_hold_and_staff_email():
    old = date(2020, 1, 1)
    assert _one(last_seen_at=old, litigation_hold=True) is None
    assert _one(last_seen_at=old, email="  A@Tidewater-Klatring.NO ") is None
    assert _one(last_seen_at=old, email="a@x.tidewater-klatring.no") is not None
    assert _one(last_seen_at=old, email="a@tidewater-klatring.no.com") is not None
    assert _one(last_seen_at=old, email="a@tidewater-klatring.norway") is not None
    assert _one(last_seen_at=old, email=None) is not None
    a = _acc(last_seen_at=old)
    del a["email"]
    assert plan_purge([a], TODAY)


def test_email_not_in_output():
    accs = [_acc(i, email="secret%d@example.com" % i, last_seen_at=date(2020, 1, 1)) for i in range(5)]
    accs.append(_acc(9, email="secret9@example.com", last_seen_at=date(2024, 10, 20)))
    out = json.dumps(plan_purge(accs, TODAY), ensure_ascii=False)
    assert "secret" not in out and "@" not in out


def test_json_and_keys():
    r = plan_purge([_acc(last_seen_at=date(2020, 1, 1))], TODAY)
    assert isinstance(json.loads(json.dumps(r))[0]["due"], str)
    assert set(r[0]) == {"account_id", "action", "due", "approved_by"}


def test_no_mutation_extra_keys_tenant():
    accs = [_acc(1, last_seen_at=date(2020, 1, 1), tenant="a", weird=object.__name__)]
    snap = deepcopy(accs)
    r1 = plan_purge(accs, TODAY)
    assert accs == snap
    for a in accs:
        del a["tenant"]
    assert plan_purge(accs, TODAY) == r1


def _bulk(n_closed, n_inactive):
    accs = []
    for i in range(n_inactive):
        accs.append(_acc(1000 + i, last_seen_at=date(2020, 1, 1) + timedelta(days=i)))
    for i in range(n_closed):
        accs.append(_acc(i, closed_at=date(2026, 8, 1) + timedelta(days=i % 30), closed_by="staff"))
    return accs


def test_cap_closed_priority():
    r = plan_purge(_bulk(30, 220), TODAY)
    ids = {x["account_id"] for x in r}
    assert len(r) == 200 and set(range(30)) <= ids


def test_cap_mix():
    r = plan_purge(_bulk(150, 100), TODAY)
    ids = [x["account_id"] for x in r]
    assert len(r) == 200
    assert sum(i < 1000 for i in ids) == 150
    assert {i for i in ids if i >= 1000} == set(range(1000, 1050))


def test_cap_boundaries():
    assert len(plan_purge(_bulk(0, 200), TODAY)) == 200
    assert len(plan_purge(_bulk(0, 201), TODAY)) == 200
    assert len(plan_purge(_bulk(0, 199), TODAY)) == 199


def test_cap_only_deletes():
    accs = _bulk(0, 200)
    accs += [_acc(5000 + i, last_seen_at=date(2020, 1, 1), unpaid_invoices=1) for i in range(10)]
    accs += [_acc(6000 + i, last_seen_at=date(2024, 10, 20)) for i in range(10)]
    r = plan_purge(accs, TODAY)
    assert len(r) == 220


def test_sorted_and_shuffle_invariant():
    accs = _bulk(20, 250)
    base = plan_purge(accs, TODAY)
    ids = [x["account_id"] for x in base]
    assert ids == sorted(ids)
    random.Random(1).shuffle(accs)
    assert plan_purge(accs, TODAY) == base


def test_malformed_skipped():
    good = _acc(1, last_seen_at=date(2020, 1, 1))
    bad = [
        None, "x", {}, _acc(None, last_seen_at=date(2020, 1, 1)),
        _acc(2, last_seen_at="2020-01-01"),
        _acc(3, last_seen_at=datetime(2020, 1, 1)),
        _acc(4, closed_at="bad"),
        _acc(5, last_seen_at=date.min),
    ]
    r = plan_purge(bad + [good], TODAY)
    assert [x["account_id"] for x in r] == [1]