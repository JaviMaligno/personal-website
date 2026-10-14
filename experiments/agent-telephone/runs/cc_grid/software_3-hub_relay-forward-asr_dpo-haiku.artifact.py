from datetime import date, timedelta

APPROVER = "Tordis Svenbjorn Dottir"
STAFF_DOMAIN = "@tidewater-klatring.no"
DELETE_CAP = 200
INACTIVITY = timedelta(days=730)
CLOSED_GRACE = timedelta(days=30)
WARN_WINDOW = timedelta(days=14)

# Open items (no rule in spec, no special case implemented):
# - Already-anonymised accounts are not special-cased; they are planned like any other account.
# - Deletions dropped by the cap are not carried over; they are re-evaluated on the next run.
# - `due` is not clamped to `today`, so overdue accounts report a past date.


def _is_staff(email):
    return (email or "").lower().endswith(STAFF_DOMAIN)


def plan_purge(accounts, today):
    seen_ids = set()
    for acc in accounts:
        if acc["id"] in seen_ids:
            raise ValueError(f"duplicate account id: {acc['id']!r}")
        seen_ids.add(acc["id"])
        if acc["last_seen_at"] is None:
            raise ValueError(f"last_seen_at is None for account {acc['id']!r}")

    purge = []  # (account, action, due) for accounts with due <= today
    warns = []  # (account, due) for accounts with today < due <= today + 14 days

    for acc in accounts:
        if acc["litigation_hold"] or _is_staff(acc["email"]):
            continue

        due = acc["last_seen_at"] + INACTIVITY
        if acc["closed_at"] is not None:
            due = min(due, acc["closed_at"] + CLOSED_GRACE)

        if due <= today:
            action = "anonymise" if acc["unpaid_invoices"] else "delete"
            purge.append((acc, action, due))
        elif due <= today + WARN_WINDOW and acc["closed_by"] != "member":
            warns.append((acc, due))

    # Cap applies to delete actions only: closed accounts first, then earliest due, then id.
    deletes = [p for p in purge if p[1] == "delete"]
    deletes.sort(key=lambda p: (p[0]["closed_at"] is None, p[2], p[0]["id"]))
    allowed_deletes = {p[0]["id"] for p in deletes[:DELETE_CAP]}

    actions = []
    for acc, action, due in purge:
        if action == "delete" and acc["id"] not in allowed_deletes:
            continue
        actions.append({
            "account_id": acc["id"],
            "action": action,
            "due": due.isoformat(),
            "approved_by": APPROVER,
        })

    for acc, due in warns:
        actions.append({
            "account_id": acc["id"],
            "action": "warn",
            "due": due.isoformat(),
            "approved_by": None,
        })

    actions.sort(key=lambda a: a["account_id"])
    return actions


if __name__ == "__main__":
    today = date(2026, 10, 13)
    base = dict(email="m@example.com", status="active", last_login=None,
                closed_by="staff", unpaid_invoices=False, litigation_hold=False)
    accounts = [
        dict(base, id=1, last_seen_at=today - timedelta(days=731), closed_at=None),
        dict(base, id=2, last_seen_at=today, closed_at=today - timedelta(days=30), closed_by="member"),
        dict(base, id=3, last_seen_at=today - timedelta(days=729), closed_at=None,
             unpaid_invoices=True),
        dict(base, id=4, last_seen_at=today - timedelta(days=716), closed_at=None),
        dict(base, id=5, last_seen_at=today, closed_at=None, litigation_hold=True),
        dict(base, id=6, last_seen_at=today - timedelta(days=731), closed_at=None,
             email="x@tidewater-klatring.no"),
    ]
    out = plan_purge(accounts, today)
    assert [a["account_id"] for a in out] == [1, 2, 3, 4], out
    assert out[0]["action"] == "delete" and out[0]["approved_by"] == APPROVER
    assert out[1]["action"] == "delete" and out[1]["due"] == "2026-09-13"
    assert out[2]["action"] == "anonymise"
    assert out[3]["action"] == "warn" and out[3]["approved_by"] is None
    assert all(set(a) == {"account_id", "action", "due", "approved_by"} for a in out)