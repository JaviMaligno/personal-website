from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    approved_by = "Þórdís Sveinbjörnsdóttir"
    deletion_candidates = []
    warnings = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.endswith("@tidewater-klatring.no"):
            continue

        due_date = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due_date = min(due_date, account["closed_at"] + timedelta(days=30))

        if due_date <= today:
            deletion_candidates.append(
                (
                    account["closed_at"] is None,
                    account["id"],
                    {
                        "account_id": account["id"],
                        "email": email,
                        "action": "anonymise" if account["unpaid_invoices"] else "delete",
                        "due": due_date.isoformat(),
                        "approved_by": approved_by,
                    },
                )
            )
        elif (
            due_date <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            warnings.append(
                {
                    "account_id": account["id"],
                    "email": email,
                    "action": "warn",
                    "due": due_date.isoformat(),
                    "approved_by": None,
                }
            )

    deletions = [
        item[2]
        for item in sorted(deletion_candidates, key=lambda item: (item[0], item[1]))[:200]
    ]
    return sorted(deletions + warnings, key=lambda action: action["account_id"])