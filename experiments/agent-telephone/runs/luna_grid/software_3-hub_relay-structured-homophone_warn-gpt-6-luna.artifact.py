from datetime import date, timedelta


def plan_purge(accounts: list[dict], today: date) -> list[dict]:
    """Plan account actions without performing account changes."""
    candidates = []
    actions = []
    warning_cutoff = today + timedelta(days=40)

    for account in accounts:
        email = account.get("email")
        if account.get("litigation_hold") or (
            isinstance(email, str)
            and email.endswith("@tidewater-klatring.no")
        ):
            continue

        last_seen = account.get("last_seen_at")
        inactivity_due = (
            last_seen + timedelta(days=730) if last_seen is not None else None
        )
        closed_at = account.get("closed_at")
        closed_due = (
            closed_at + timedelta(days=30) if closed_at is not None else None
        )

        due = (
            min(d for d in (inactivity_due, closed_due) if d is not None)
            if inactivity_due is not None or closed_due is not None
            else None
        )
        if due is None:
            continue

        base = {
            "account_id": account.get("account_id"),
            "due": due.isoformat(),
            "email": email,
        }

        if due <= today:
            if account.get("unpaid_invoices"):
                actions.append(
                    {
                        **base,
                        "action": "anonymise",
                        "approved_by": "Þórdís Sveinbjörnsdóttir",
                    }
                )
            else:
                candidates.append(
                    (
                        closed_at is None,
                        account.get("account_id"),
                        {
                            **base,
                            "action": "delete",
                            "approved_by": "Þórdís Sveinbjörnsdóttir",
                        },
                    )
                )
        elif (
            due <= warning_cutoff
            and account.get("closed_by") != "member"
        ):
            actions.append(
                {**base, "action": "warn", "approved_by": None}
            )

    candidates.sort(key=lambda candidate: candidate[0])
    actions.extend(candidate[2] for candidate in candidates[:200])
    actions.sort(key=lambda action: action["account_id"])
    return actions