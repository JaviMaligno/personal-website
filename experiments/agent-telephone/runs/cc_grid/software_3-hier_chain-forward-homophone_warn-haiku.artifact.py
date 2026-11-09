"""GDPR purge planner for Tidewater Climbing.

plan_purge(accounts, today) -> list[dict]

Output action keys, in order: account_id, action, due, approved_by.
due is an ISO string (YYYY-MM-DD). approved_by is the DPO name for
delete and anonymise, and None (present, null) for warn.
No email or other personal field appears in any action. Logging uses ids only.

Due date:
  open account:   last_seen_at + 730 days
  closed account: min(last_seen_at + 730 days, closed_at + 30 days)

Rules, first match wins per account:
  1. litigation_hold truthy: nothing.
  2. Staff (email, stripped and lowercased, ends with the staff domain): nothing.
  3. due <= today: anonymise if unpaid invoices, else delete.
  4. today < due <= today + 40 days (inclusive): warn, unless closed_by == "member".
  5. Otherwise nothing.

Cap: at most 200 delete actions per run. Anonymise is never capped.
Deletes are ordered closed-first, then due ascending, then id key.
Overflow deletes are not emitted. Their ids are logged as a warning and
they are picked up by the next run because the planner is stateless.

Validation (ValueError, raised before any output; messages name the id, never the email):
  last_seen_at missing, None, or not a date (datetime rejected).
  closed_at not None and not a date (datetime rejected).
  Duplicate ids.

Output order: sorted by account_id. Key is (0, value, "") for int ids and
(1, 0, value) for str ids, so mixed id types never compare directly.

Resolved conflicts and ambiguities (for PM review):
  - Warn boundary is inclusive at day 40, as specified.
  - Accounts with unpaid invoices still get a warn. The brief does not exclude them.
  - Anonymise is not counted toward the 200 cap. The brief caps deletions only.
  - Overflow deletes are absent from this run's output and survive only in the
    log. The brief is silent on overflow. PM should confirm this is acceptable.
  - Timeliness risk: overflow deletes stay past due until a later run. PM should
    accept this or escalate to the DPO.
  - closed_by == "member" with closed_at None: due is computed as open, and no
    warn is sent (conservative).
  - Staff match is case-insensitive and whitespace-tolerant.
  - status and last_login are ignored. There is no fallback to last_login.
  - tenant is ignored.
  - approved_by is the NFC form of the DPO name.

Test cases (names and expectations):
  test_due_today_is_delete_not_warn: due == today gives delete.
  test_due_today_plus_40_warns: due == today + 40 gives warn.
  test_due_today_plus_41_nothing: due == today + 41 gives no action.
  test_closed_grace_earlier_than_inactivity: closed-based due is used.
  test_inactivity_earlier_than_closed_grace: inactivity-based due is used.
  test_leap_day_last_seen: 2024-02-29 arithmetic is correct.
  test_member_closed_warn_window_no_warn: no warn.
  test_staff_closed_warn_window_warns: warn is emitted.
  test_member_closed_at_none_no_warn: open due, no warn.
  test_unpaid_due_is_anonymise_uncapped: anonymise, not counted toward cap.
  test_litigation_hold_past_due_nothing: no action.
  test_staff_email_variants_nothing: upper, mixed case, and padded emails yield nothing.
  test_email_none_is_not_staff: normal rules apply.
  test_201_deletables_caps_at_200: exactly 200 deletes; closed preferred; no error.
  test_anonymise_emitted_at_cap: anonymise still emitted when 200 deletes exist.
  test_mixed_int_and_str_ids_sort: sorts without raising.
  test_approved_by_exact_dpo_string: delete and anonymise carry the NFC name.
  test_warn_approved_by_null_key_present: warn has approved_by None.
  test_json_round_trip_utf8_and_iso_dates: ensure_ascii=False keeps the name.
  test_last_seen_none_raises_with_id: ValueError names the id.
  test_datetime_rejected: datetime for last_seen_at or closed_at raises.
  test_duplicate_ids_raise: ValueError on duplicate id.
  test_empty_input_returns_empty_list: [] returns [].
  test_no_email_in_any_action: no personal field appears in output.
"""

import logging
import unicodedata
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)

DPO_APPROVER = unicodedata.normalize("NFC", "Þórdís Sveinbjörnsdóttir")
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=40)


def _id_key(account_id):
    if isinstance(account_id, int):
        return (0, account_id, "")
    return (1, 0, str(account_id))


def _is_date(value):
    return isinstance(value, date) and not isinstance(value, datetime)


def _validate(accounts):
    seen = set()
    for acc in accounts:
        aid = acc["id"]
        if aid in seen:
            raise ValueError(f"duplicate account id: {aid!r}")
        seen.add(aid)
        if not _is_date(acc.get("last_seen_at")):
            raise ValueError(f"account {aid!r}: last_seen_at must be a date")
        closed_at = acc.get("closed_at")
        if closed_at is not None and not _is_date(closed_at):
            raise ValueError(f"account {aid!r}: closed_at must be a date or None")


def _action(aid, action, due, approver):
    return {
        "account_id": aid,
        "action": action,
        "due": due.isoformat(),
        "approved_by": approver,
    }


def plan_purge(accounts, today):
    accounts = list(accounts)
    _validate(accounts)
    if not _is_date(today):
        raise ValueError("today must be a date")

    warn_until = today + WARN_WINDOW
    out = []
    deletes = []

    for acc in accounts:
        if acc.get("litigation_hold"):
            continue
        email = acc.get("email")
        if email is not None and email.strip().lower().endswith(STAFF_DOMAIN):
            continue

        aid = acc["id"]
        closed_at = acc.get("closed_at")
        due = acc["last_seen_at"] + INACTIVITY
        if closed_at is not None:
            due = min(due, closed_at + CLOSED_GRACE)

        unpaid = bool(acc.get("unpaid_invoices"))
        if due <= today:
            if unpaid:
                out.append(_action(aid, "anonymise", due, DPO_APPROVER))
            else:
                group = 0 if closed_at is not None else 1
                deletes.append((group, due, _id_key(aid), aid))
        elif due <= warn_until:
            if acc.get("closed_by") != "member":
                out.append(_action(aid, "warn", due, None))

    deletes.sort(key=lambda t: (t[0], t[1], t[2]))
    kept = deletes[:DELETE_CAP]
    deferred = deletes[DELETE_CAP:]

    for _, due, _, aid in kept:
        out.append(_action(aid, "delete", due, DPO_APPROVER))

    if deferred:
        log.warning(
            "deferred %d delete(s) to next run; ids=%s",
            len(deferred),
            [str(t[3]) for t in deferred],
        )

    out.sort(key=lambda a: _id_key(a["account_id"]))
    return out