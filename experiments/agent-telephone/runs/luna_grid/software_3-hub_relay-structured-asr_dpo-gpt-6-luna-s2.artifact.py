from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    actions = []
    deletion_candidates = []

    for account in accounts:
        email = account.get("email", "")
        if account.get("litigation_hold") or email.endswith("@tidewater-klatring.no"):
            continue

        due_date = account["last_seen_at"] + timedelta(days=730)
        if account.get("closed_at") is not None:
            closure_due = account["closed_at"] + timedelta(days=30)
            if closure_due < due_date:
                due_date = closure_due

        if due_date <= today:
            if account.get("unpaid_invoices"):
                actions.append({
                    "account_id": account["account_id"],
                    "email": email,
                    "action": "anonymise",
                    "due": due_date.isoformat(),
                    "approved_by": "Tordis Svenbjorn Dottir",
                })
            else:
                deletion_candidates.append((account, due_date))
        elif (
            due_date <= today + timedelta(days=14)
            and account.get("closed_by") != "member"
        ):
            actions.append({
                "account_id": account["account_id"],
                "email": email,
                "action": "warn",
                "due": due_date.isoformat(),
                "approved_by": None,
            })

    deletion_candidates.sort(
        key=lambda item: (
            item[0].get("closed_at") is None,
            item[0]["account_id"],
        )
    )
    for account, due_date in deletion_candidates[:200]:
        actions.append({
            "account_id": account["account_id"],
            "email": account.get("email", ""),
            "action": "delete",
            "due": due_date.isoformat(),
            "approved_by": "Tordis Svenbjorn Dottir",
        })

    actions.sort(key=lambda action: action["account_id"])
    return actions