from datetime import date, timedelta


APPROVER = "Þórdís Sveinbjörnsdóttir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_LIMIT = 200


def plan_purge(accounts, today):
    """Return purge actions for eligible accounts."""
    actions = []
    deletions = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith(STAFF_DOMAIN):
            continue

        inactivity_due = account["last_seen_at"] + timedelta(days=730)
        due = inactivity_due
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))

        base = {
            "account_id": account["id"],
            "email": email,
            "due": due.isoformat(),
        }

        if due <= today:
            if account["unpaid_invoices"]:
                actions.append({**base, "action": "anonymise", "approved_by": APPROVER})
            else:
                deletions.append((account, base))
        elif (
            today < due <= today + timedelta(days=14)
            and not (
                account["closed_at"] is not None
                and account["closed_by"] == "member"
            )
        ):
            actions.append({**base, "action": "warn"})

    deletions.sort(
        key=lambda item: (
            item[0]["closed_at"] is None,
            str(item[0]["id"]).casefold(),
            type(item[0]["id"]).__name__,
            repr(item[0]["id"]),
        )
    )
    actions.extend(
        {**base, "action": "delete", "approved_by": APPROVER}
        for _, base in deletions[:DELETE_LIMIT]
    )

    actions.sort(
        key=lambda action: (
            str(action["account_id"]).casefold(),
            type(action["account_id"]).__name__,
            repr(action["account_id"]),
        )
    )
    return actions