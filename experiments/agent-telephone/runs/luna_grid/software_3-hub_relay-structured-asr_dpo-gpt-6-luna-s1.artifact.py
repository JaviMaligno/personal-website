from datetime import date, datetime, timedelta


def plan_purge(accounts, today):
    """Return due purge actions and upcoming warnings."""
    eligible = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        last_seen = account["last_seen_at"]
        if isinstance(last_seen, datetime):
            last_seen = last_seen.date()
        due = last_seen + timedelta(days=730)

        closed_at = account.get("closed_at")
        if closed_at is not None:
            closed_due = closed_at + timedelta(days=30)
            if closed_due < due:
                due = closed_due

        if due <= today:
            action = "anonymise" if account.get("unpaid_invoices") else "delete"
            eligible.append(
                {
                    "account_id": account["id"],
                    "email": email,
                    "action": action,
                    "due": due.isoformat(),
                    "approved_by": "Tordis Svenbjorn Dottir",
                }
            )
        elif (
            due <= today + timedelta(days=14)
            and account.get("closed_by") != "member"
        ):
            warnings.append(
                {
                    "account_id": account["id"],
                    "email": email,
                    "action": "warn",
                    "due": due.isoformat(),
                }
            )

    deletions = [a for a in eligible if a["action"] == "delete"]
    other_actions = [a for a in eligible if a["action"] != "delete"]

    deletions.sort(
        key=lambda a: (
            0 if next(
                account.get("closed_at") is not None
                for account in accounts
                if account["id"] == a["account_id"]
            ) else 1,
            a["due"],
            str(a["account_id"]),
        )
    )

    actions = other_actions + deletions[:200] + warnings
    actions.sort(key=lambda a: str(a["account_id"]))
    return actions