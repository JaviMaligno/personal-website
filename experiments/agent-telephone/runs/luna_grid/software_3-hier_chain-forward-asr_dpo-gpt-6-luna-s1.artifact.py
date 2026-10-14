from datetime import date as _date, timedelta as _timedelta

__all__ = ["plan_purge"]


def plan_purge(accounts: list[dict], today: _date) -> list[dict]:
    approver = "Tordis Svenbjorn Dottir"
    due_actions = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith("@tidewater-klatring.no"):
            continue

        due = account["last_seen_at"] + _timedelta(days=730)
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + _timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            due_actions.append((account, due, action))
        elif due <= today + _timedelta(days=14) and account["closed_by"] != "member":
            warnings.append((account, due, "warn"))

    deletes = [item for item in due_actions if item[2] == "delete"]
    deletes.sort(key=lambda item: (item[0]["closed_at"] is None, item[0]["id"]))
    kept_deletes = {id(item[0]) for item in deletes[:200]}

    actions = []
    for account, due, action in due_actions:
        if action == "delete" and id(account) not in kept_deletes:
            continue
        actions.append({
            "account_id": account["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": approver,
            "email": account["email"],
        })

    for account, due, _ in warnings:
        actions.append({
            "account_id": account["id"],
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
            "email": account["email"],
        })

    actions.sort(key=lambda action: action["account_id"])
    return actions