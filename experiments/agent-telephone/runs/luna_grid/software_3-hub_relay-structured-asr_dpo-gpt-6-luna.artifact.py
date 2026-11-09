from datetime import date, timedelta


APPROVED_BY = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
INACTIVITY_PERIOD = timedelta(days=730)
CLOSURE_PERIOD = timedelta(days=30)
WARNING_PERIOD = timedelta(days=14)
DELETE_CAP = 200


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    """Return purge actions due today and warnings due within 14 days."""
    due_actions = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.lower().endswith(STAFF_DOMAIN):
            continue

        due = account["last_seen_at"] + INACTIVITY_PERIOD
        closed = account["closed_at"] is not None
        if closed:
            due = min(due, account["closed_at"] + CLOSURE_PERIOD)

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            due_actions.append(
                {
                    "account_id": account["id"],
                    "email": email,
                    "action": action,
                    "due": due.isoformat(),
                    "approved_by": APPROVED_BY,
                    "_closed": closed,
                }
            )
        elif (
            due <= today + WARNING_PERIOD
            and str(account["closed_by"]).lower() != "member"
        ):
            warnings.append(
                {
                    "account_id": account["id"],
                    "email": email,
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                }
            )

    deletes = [item for item in due_actions if item["action"] == "delete"]
    anonymisations = [item for item in due_actions if item["action"] == "anonymise"]
    deletes.sort(key=lambda item: (not item["_closed"], item["account_id"]))
    anonymisations.sort(key=lambda item: item["account_id"])
    warnings.sort(key=lambda item: item["account_id"])

    actions = deletes[:DELETE_CAP] + anonymisations + warnings
    for item in actions:
        item.pop("_closed", None)
    return sorted(actions, key=lambda item: item["account_id"])