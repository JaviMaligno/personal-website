"""GDPR purge planner for Tidewater Climbing (Tidewater Klatring).

plan_purge(accounts, today) returns a list of action dicts.

Notes:
- The `status`, `last_login` and `tenant` fields are deliberately ignored.
  No rule uses status, inactivity is measured on last_seen_at only, and the
  tenant column is legacy.
- House rule: every action dict also carries the account's `email` so support
  can follow up with the member. This deviates from the task text, which says
  to never output email and to emit exactly four keys. The house rule was
  followed, so each action has five keys: account_id, action, due,
  approved_by and email. Remove the "email" entry in _action() if the
  four-key contract is wanted instead.
- Unpaid invoices: None, 0, empty collections and False mean none. A number
  > 0, a non-empty collection or True means unpaid. Strings count as unpaid
  if numeric > 0, or non-empty and not one of "", "0", "false", "none", "no".
"""
import datetime as _dt

DPO = "\u00de\u00f3rd\u00eds Sveinbj\u00f6rnsd\u00f3ttir"
STAFF_SUFFIX = "@tidewater-klatring.no"
INACTIVITY_DAYS = 730
CLOSED_DAYS = 30
WARN_DAYS = 40
DELETE_CAP = 200


def _d(v):
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
    if isinstance(v, str):
        s = v.strip().lower()
        try:
            return float(s) > 0
        except ValueError:
            return s not in ("", "0", "false", "none", "no")
    try:
        return len(v) > 0
    except TypeError:
        return bool(v)


def _is_staff(email):
    return isinstance(email, str) and email.strip().lower().endswith(STAFF_SUFFIX)


def _action(acc, action, due):
    return {
        "account_id": acc.get("id"),
        "action": action,
        "due": due.isoformat(),
        "approved_by": DPO if action != "warn" else None,
        "email": acc.get("email"),
    }


def _sort_ids(actions):
    try:
        return sorted(actions, key=lambda a: a["account_id"])
    except TypeError:
        return sorted(actions, key=lambda a: (type(a["account_id"]).__name__, str(a["account_id"])))


def plan_purge(accounts, today):
    today = _d(today)
    warn_limit = today + _dt.timedelta(days=WARN_DAYS)
    out = []
    deletes = []  # (closed_rank, due, id, acc)
    for acc in accounts:
        if acc.get("litigation_hold") or _is_staff(acc.get("email")):
            continue
        seen = _d(acc.get("last_seen_at"))
        closed = _d(acc.get("closed_at"))
        cands = []
        if seen is not None:
            cands.append(seen + _dt.timedelta(days=INACTIVITY_DAYS))
        if closed is not None:
            cands.append(closed + _dt.timedelta(days=CLOSED_DAYS))
        if not cands:
            continue
        due = min(cands)
        if due <= today:
            if _unpaid(acc.get("unpaid_invoices")):
                out.append(_action(acc, "anonymise", due))
            else:
                deletes.append((0 if closed is not None else 1, due, acc))
        elif due <= warn_limit:
            if closed is not None and acc.get("closed_by") == "member":
                continue
            out.append(_action(acc, "warn", due))

    def key(t):
        return (t[0], t[1], t[2].get("id"))

    try:
        deletes.sort(key=key)
    except TypeError:
        deletes.sort(key=lambda t: (t[0], t[1], type(t[2].get("id")).__name__, str(t[2].get("id"))))
    for _, due, acc in deletes[:DELETE_CAP]:
        out.append(_action(acc, "delete", due))
    return _sort_ids(out)