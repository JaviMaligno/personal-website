from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    approver = "Tordis Svenbjorn Dottir"
    pending_deletes = []
    actions = []

    for account in accounts:
        email = account["email"]
        if email.lower().endswith("@tidewater-klatring.no") or account["litigation_hold"]:
            continue

        due = account["last_seen_at"] + timedelta(days=730)
        if account["closed_at"] is not None:
            due = min(due, account["closed_at"] + timedelta(days=30))

        if due <= today:
            action = "anonymise" if account["unpaid_invoices"] else "delete"
            item = {
                "account_id": account["id"],
                "email": email,
                "action": action,
                "due": due.isoformat(),
                "approved_by": approver,
            }
            if action == "delete":
                pending_deletes.append((account["closed_at"] is None, item))
            else:
                actions.append(item)
        elif (
            due <= today + timedelta(days=14)
            and account["closed_by"] != "member"
        ):
            actions.append({
                "account_id": account["id"],
                "email": email,
                "action": "warn",
                "due": due.isoformat(),
                "approved_by": None,
            })

    pending_deletes.sort(key=lambda entry: entry[0])
    actions.extend(item for _, item in pending_deletes[:200])
    actions.sort(key=lambda item: item["account_id"])
    return actions