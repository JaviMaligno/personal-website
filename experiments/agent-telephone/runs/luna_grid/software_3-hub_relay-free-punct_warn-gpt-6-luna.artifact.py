from datetime import date, timedelta


_APPROVER = "Þórdís Sveinbjörnsdóttir"
_STAFF_DOMAIN = "@tidewater-klatring.no"
_DELETE_LIMIT = 200
_WARNING_WINDOW = 14


def _has_unpaid_invoices(account):
    return bool(account.get("unpaid_invoices", account.get("has_unpaid_invoices", False)))


def plan_purge(accounts, today):
    candidates = []
    warnings = []

    for account in accounts:
        email = account.get("email", "")
        if email.endswith(_STAFF_DOMAIN) or account.get("litigation_hold"):
            continue

        deadline = account["last_seen_at"] + timedelta(days=730)
        closed_at = account.get("closed_at")
        is_closed = closed_at is not None

        if is_closed:
            deadline = min(deadline, closed_at + timedelta(days=30))

        if deadline <= today:
            action = "anonymise" if _has_unpaid_invoices(account) else "delete"
            candidates.append(
                {
                    "account_id": account["account_id"],
                    "action": action,
                    "due": deadline.isoformat(),
                    "approved_by": _APPROVER,
                    "email": email,
                    "_closed": is_closed,
                }
            )
        elif (
            deadline <= today + timedelta(days=_WARNING_WINDOW)
            and account.get("closed_by") != "member"
        ):
            warnings.append(
                {
                    "account_id": account["account_id"],
                    "action": "warn",
                    "due": deadline.isoformat(),
                    "approved_by": None,
                    "email": email,
                }
            )

    deletions = [item for item in candidates if item["action"] == "delete"]
    other_actions = [item for item in candidates if item["action"] != "delete"]
    deletions.sort(key=lambda item: (not item["_closed"], item["due"], item["account_id"]))
    selected = deletions[:_DELETE_LIMIT] + other_actions

    actions = selected + warnings
    actions.sort(key=lambda item: item["account_id"])
    for item in actions:
        item.pop("_closed", None)
    return actions