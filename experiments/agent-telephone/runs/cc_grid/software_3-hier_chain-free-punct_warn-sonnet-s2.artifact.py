"""GDPR purge planner for Tidewater Climbing.

plan_purge(accounts, today) -> list of action dicts.

Assumptions and decisions:
- House rule deviation: the house rule says every action dict carries the account's
  `email`, so actions have keys account_id, action, due, approved_by AND email.
  This conflicts with the task text ("exactly four keys, never include the email");
  the house rule was followed here and should be confirmed with the requester.
- `status`, `tenant` and `last_login` are ignored entirely.
- Inactivity due = last_seen_at + 730 days; closed due = closed_at + 30 days
  (only when closed_at is not None). Due is the earlier of the two.
- last_seen_at None: use closed due if closed, else skip the account.
- Unusable (non-date) dates: the account is skipped. Datetimes are converted via .date().
- Missing `id` raises ValueError; non-date `today` raises ValueError.
- Cap: at most 200 "delete" actions; anonymise is not counted or deferred.
  Order: closed (closed_at not None) first, then by due ascending, then id.
  Deferred accounts get no action (no warn).
- Sorting: by id; numbers first (numeric order), then others by str(id).
  Sort is stable, so duplicate ids are handled independently.
- Unpaid invoices: numbers > 0, non-empty containers, other truthy values.
"""
import datetime as _dt

APPROVER = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 14
MAX_DELETES = 200


def _to_date(v):
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    return None


def _unpaid(v):
    if v is None or isinstance(v, bool):
        return bool(v)
    if isinstance(v, (int, float)):
        return v > 0
    try:
        return bool(v)
    except Exception:
        return False


def _id_key(i):
    if isinstance(i, (int, float)) and not isinstance(i, bool):
        return (0, i, "")
    return (1, 0, str(i))


def plan_purge(accounts, today):
    if not isinstance(today, _dt.date):
        raise ValueError("today must be a datetime.date")
    today = _to_date(today)
    horizon = today + _dt.timedelta(days=WARN_DAYS)

    deletes, others = [], []
    for acc in accounts:
        if "id" not in acc or acc["id"] is None:
            raise ValueError("account is missing required key 'id'")
        aid = acc["id"]

        if acc.get("litigation_hold"):
            continue
        email = acc.get("email")
        if isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX):
            continue

        raw_closed = acc.get("closed_at")
        closed_at = _to_date(raw_closed)
        if raw_closed is not None and closed_at is None:
            continue
        raw_seen = acc.get("last_seen_at")
        seen = _to_date(raw_seen)
        if raw_seen is not None and seen is None:
            continue

        candidates = []
        if seen is not None:
            candidates.append(seen + _dt.timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            candidates.append(closed_at + _dt.timedelta(days=CLOSED_DAYS))
        if not candidates:
            continue
        due = min(candidates)

        def make(action, approver):
            return {
                "account_id": aid,
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver,
                "email": email,
            }

        if due <= today:
            if _unpaid(acc.get("unpaid_invoices")):
                others.append(make("anonymise", APPROVER))
            else:
                deletes.append((
                    0 if closed_at is not None else 1,
                    due,
                    _id_key(aid),
                    make("delete", APPROVER),
                ))
        elif due <= horizon:
            if closed_at is not None and acc.get("closed_by") == "member":
                continue
            others.append(make("warn", None))

    deletes.sort(key=lambda t: t[:3])
    result = others + [t[3] for t in deletes[:MAX_DELETES]]
    result.sort(key=lambda a: _id_key(a["account_id"]))
    return result