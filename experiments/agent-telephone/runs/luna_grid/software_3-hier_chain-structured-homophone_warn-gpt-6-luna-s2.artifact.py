from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    actions = []
    deletions = []

    for account in accounts:
        email = account["email"]
        if account["litigation_hold"] or email.casefold().endswith(
            "@tidewater-klatring.no"
        ):
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            item = {
                "account_id": account["id"],
                "action": action,
                "due": due.isoformat(),
                "approved_by": "Þórdís Sveinbjörnsdóttir",
                "email": email,
            }
            if action == "delete":
                deletions.append((account, item))
            else:
                actions.append(item)
        elif (
            due <= today + timedelta(days=40)
            and account["closed_by"] != "member"
        ):
            actions.append(
                {
                    "account_id": account["id"],
                    "action": "warn",
                    "due": due.isoformat(),
                    "approved_by": None,
                    "email": email,
                }
            )

    deletions.sort(
        key=lambda pair: (
            pair[0]["closed_at"] is None,
            str(pair[0]["id"]),
        )
    )
    actions.extend(item for _, item in deletions[:200])
    actions.sort(key=lambda item: str(item["account_id"]))
    return actions