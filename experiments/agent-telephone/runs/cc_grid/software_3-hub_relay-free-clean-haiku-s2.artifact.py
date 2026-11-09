"""Tidewater Climbing GDPR clean-up planner.

plan_purge(accounts, today) returns the actions for one run. It is pure: it does not read the clock, touch the network or disk, or emit member email addresses. review_flags(accounts, today) returns the records withheld for human review, with account ids and reason strings only.

RULES
  Inactivity candidate: last_seen_at + 730 days. last_login is never read.
  Closed candidate:     closed_at + 30 days.
  Due date:             the earlier of the candidates that exist.
  litigation_hold True: no action, not counted anywhere.
  Staff email (suffix @tidewater-klatring.no, case-insensitive): no action.
  due <= today:         delete, or anonymise if unpaid_invoices > 0.
  today < due <= today + 14: warn, unless closed_by == "member".
  Otherwise:            no action.
  Warn actions have approved_by None. Delete and anonymise actions have APPROVER.

CAP
  At most DELETE_CAP (200) delete actions per run. Closed accounts (closed_at set) are selected before inactive ones. Within each group, selection is by due ascending, then by account id. Accounts over the cap are not returned and remain due for a later run. Warn actions are never counted.
  Anonymise actions are NOT counted by default. Set ANONYMISE_COUNTS_TOWARD_CAP to True to include them in the cap pool.

ID ORDERING
  Ids may be int or str. Ints sort numerically and before strings. Strings sort by (length, text), so "9" comes before "10". Output is sorted by this key. Mixed id types are accepted but are not expected.

MALFORMED INPUT
  Raise (the whole run aborts and nothing is returned):
    accounts is not an iterable of dicts; a record is missing a required key; a date field is not a datetime.date (datetime is rejected); today is not a datetime.date; email is neither str nor None; litigation_hold is not a bool; unpaid_invoices is neither int nor None, or is negative; id is neither int nor str.
    Rationale: these indicate a broken export. Guessing at them could delete the wrong data, so the run stops.
  Flag and withhold (the run continues and that account produces no action):
    unpaid_invoices is None.
    last_seen_at is None on an account that is not closed.
    closed_at is later than today.
    closed_by is not "member" or "staff". Under the literal rule, this also applies to active accounts whose closed_by is None. Confirm this before go-live, because it would flag every active account if the export leaves closed_by empty.
    closed_by is "member" and closed_at is None.
    The id is duplicated. Every record with that id is withheld, including records that are on hold.
  Rationale: a single bad record should not block the batch, and withholding it blocks the destructive path.

OPEN QUESTIONS AND BLOCKERS
  RETENTION BLOCKER, NOT SOLVED IN CODE: Skatteetaten requires invoices to be kept for five years. This rule protects only accounts that currently have unpaid invoices. A paid account reaching its due date will be deleted along with its invoices. The data has no invoice date. A DPO or legal decision is required before go-live.
  Anonymised accounts remain due on later runs because the function is stateless. If an anonymised account's invoices are later paid, the next run deletes it.
  Warn notices for accounts with unpaid invoices will be sent as specified. The downstream notice text must not say "deleted" for accounts that will be anonymised.
  The meaning of status is undefined, so it is not used. last_login is not used.

STATUS
  This module has not been executed. The test suite is still to be written and run with python3 -I.
"""

from collections import Counter
from datetime import date, datetime, timedelta

APPROVER = "Þórdís Sveinbjörnsdóttir"
INACTIVITY_DAYS = 730
CLOSED_GRACE_DAYS = 30
WARN_WINDOW_DAYS = 14
DELETE_CAP = 200
ANONYMISE_COUNTS_TOWARD_CAP = False
STAFF_EMAIL_SUFFIX = "@tidewater-klatring.no"

_REQUIRED_KEYS = (
    "id",
    "email",
    "last_seen_at",
    "closed_at",
    "closed_by",
    "unpaid_invoices",
    "litigation_hold",
)

FLAG_DUPLICATE_ID = "duplicate account id"
FLAG_UNPAID_MISSING = "unpaid_invoices is None"
FLAG_LAST_SEEN_MISSING = "last_seen_at is None on an account that is not closed"
FLAG_CLOSED_AT_FUTURE = "closed_at is later than today"
FLAG_CLOSED_BY_INVALID = "closed_by is not 'member' or 'staff'"
FLAG_MEMBER_NO_CLOSED_AT = "closed_by is 'member' but closed_at is None"


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _id_key(account_id):
    if isinstance(account_id, int):
        return (0, account_id, "")
    return (1, len(account_id), account_id)


def _validate(accounts, today):
    if not _is_date(today):
        raise TypeError("today must be a datetime.date")
    try:
        records = list(accounts)
    except TypeError:
        raise TypeError("accounts must be an iterable of dicts") from None
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise TypeError(f"record {i} is not a dict")
        missing = [k for k in _REQUIRED_KEYS if k not in rec]
        if missing:
            raise ValueError(f"record {i} is missing keys: {', '.join(missing)}")
        aid = rec["id"]
        if isinstance(aid, bool) or not isinstance(aid, (int, str)):
            raise TypeError(f"record {i} has an id that is neither int nor str")
        if rec["email"] is not None and not isinstance(rec["email"], str):
            raise TypeError(f"record {i} has a non-str email")
        for key in ("last_seen_at", "closed_at"):
            if rec[key] is not None and not _is_date(rec[key]):
                raise TypeError(f"record {i} has a non-date {key}")
        if not isinstance(rec["litigation_hold"], bool):
            raise TypeError(f"record {i} has a non-bool litigation_hold")
        unpaid = rec["unpaid_invoices"]
        if unpaid is not None:
            if isinstance(unpaid, bool) or not isinstance(unpaid, int):
                raise TypeError(f"record {i} has a non-int unpaid_invoices")
            if unpaid < 0:
                raise ValueError(f"record {i} has a negative unpaid_invoices")
    return records


def _evaluate(records, today):
    """Return (candidates, flags). Candidates are internal dicts, not yet capped."""
    dup_ids = {k for k, n in Counter(r["id"] for r in records).items() if n > 1}
    horizon = today + timedelta(days=WARN_WINDOW_DAYS)
    candidates = []
    flags = []
    for r in records:
        aid = r["id"]
        if aid in dup_ids:
            flags.append((aid, FLAG_DUPLICATE_ID))
            continue
        if r["litigation_hold"]:
            continue
        email = r["email"]
        if email is not None and email.lower().endswith(STAFF_EMAIL_SUFFIX):
            continue

        last_seen = r["last_seen_at"]
        closed_at = r["closed_at"]
        closed_by = r["closed_by"]
        unpaid = r["unpaid_invoices"]

        if unpaid is None:
            flags.append((aid, FLAG_UNPAID_MISSING))
            continue
        if closed_by not in ("member", "staff"):
            flags.append((aid, FLAG_CLOSED_BY_INVALID))
            continue
        if closed_by == "member" and closed_at is None:
            flags.append((aid, FLAG_MEMBER_NO_CLOSED_AT))
            continue
        if closed_at is None and last_seen is None:
            flags.append((aid, FLAG_LAST_SEEN_MISSING))
            continue
        if closed_at is not None and closed_at > today:
            flags.append((aid, FLAG_CLOSED_AT_FUTURE))
            continue

        due_options = []
        if last_seen is not None:
            due_options.append(last_seen + timedelta(days=INACTIVITY_DAYS))
        if closed_at is not None:
            due_options.append(closed_at + timedelta(days=CLOSED_GRACE_DAYS))
        due = min(due_options)

        if due <= today:
            action = "anonymise" if unpaid > 0 else "delete"
        elif due <= horizon:
            if closed_by == "member":
                continue
            action = "warn"
        else:
            continue

        candidates.append({
            "account_id": aid,
            "action": action,
            "due": due,
            "closed": closed_at is not None,
        })
    return candidates, flags


def _apply_cap(candidates):
    candidates.sort(key=lambda c: (
        0 if c["closed"] else 1,
        c["due"],
        _id_key(c["account_id"]),
    ))
    kept = []
    used = 0
    for c in candidates:
        counted = c["action"] == "delete" or (
            c["action"] == "anonymise" and ANONYMISE_COUNTS_TOWARD_CAP
        )
        if counted:
            if used >= DELETE_CAP:
                continue
            used += 1
        kept.append(c)
    return kept


def plan_purge(accounts, today):
    """Return the list of actions for this run, sorted by account id.

    Each action has exactly the keys account_id, action, due (YYYY-MM-DD),
    and approved_by. No email addresses appear in the output.
    """
    records = _validate(accounts, today)
    candidates, _ = _evaluate(records, today)
    kept = _apply_cap(candidates)
    kept.sort(key=lambda c: _id_key(c["account_id"]))
    return [
        {
            "account_id": c["account_id"],
            "action": c["action"],
            "due": c["due"].isoformat(),
            "approved_by": None if c["action"] == "warn" else APPROVER,
        }
        for c in kept
    ]


def review_flags(accounts, today):
    """Return records withheld for review as dicts with account_id and reason.

    Sorted by account id. Contains no email addresses.
    """
    records = _validate(accounts, today)
    _, flags = _evaluate(records, today)
    flags.sort(key=lambda f: (_id_key(f[0]), f[1]))
    return [{"account_id": aid, "reason": reason} for aid, reason in flags]