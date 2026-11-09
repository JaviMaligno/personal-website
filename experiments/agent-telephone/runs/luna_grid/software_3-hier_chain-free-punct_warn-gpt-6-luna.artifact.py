from datetime import date, timedelta
from typing import Any


APPROVER = "Þórdís Sveinbjörnsdóttir"
DELETION_CAP = 200
STAFF_DOMAIN = "@tidewater-klatring.no"


def plan_purge(accounts: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """Plan account actions.

    Assumptions: account_id is present; last_seen_at and closed_at are
    datetime.date values (or None for closed_at); litigation_hold and
    unpaid_invoices are truthy when applicable; closed_by_member identifies
    member-initiated closure. Accounts with a missing or invalid required
    last_seen_at are skipped. Invalid optional closed_at values are ignored.
    """
    candidates: list[tuple[bool, str, dict[str, Any]]] = []
    actions: list[dict[str, Any]] = []

    for account in accounts:
        email = account.get("email")
        if account.get("litigation_hold") or (
            isinstance(email, str) and email.lower().endswith(STAFF_DOMAIN)
        ):
            continue

        last_seen = account.get("last_seen_at")
        if not isinstance(last_seen, date) or isinstance(last_seen, type):
            continue

        closed_at = account.get("closed_at")
        if not isinstance(closed_at, date) or isinstance(closed_at, type):
            closed_at = None

        due = min(
            last_seen + timedelta(days=730),
            *([closed_at + timedelta(days=30)] if closed_at else []),
        )
        account_id = account["account_id"]

        if due <= today:
            if account.get("unpaid_invoices"):
                actions.append(
                    {
                        "account_id": account_id,
                        "action": "anonymisation",
                        "due": due.isoformat(),
                        "approved_by": APPROVER,
                    }
                )
            else:
                candidates.append(
                    (closed_at is not None, str(account_id), {
                        "account_id": account_id,
                        "action": "deletion",
                        "due": due.isoformat(),
                        "approved_by": APPROVER,
                    })
                )
        elif (
            due <= today + timedelta(days=14)
            and due > today
            and not account.get("closed_by_member")
        ):
            actions.append(
                {
                    "account_id": account_id,
                    "action": "warning",
                    "due": due.isoformat(),
                    "approved_by": None,
                }
            )

    candidates.sort(key=lambda item: (not item[0], item[1]))
    actions.extend(item[2] for item in candidates[:DELETION_CAP])
    actions.sort(key=lambda action: str(action["account_id"]))
    return actions


if __name__ == "__main__":
    import unittest

    class PlanPurgeTests(unittest.TestCase):
        today = date(2025, 1, 1)

        def account(self, account_id: int = 1, **changes: Any) -> dict[str, Any]:
            account = {
                "account_id": account_id,
                "email": f"user{account_id}@example.com",
                "last_seen_at": date(2023, 1, 1),
                "closed_at": None,
                "litigation_hold": False,
                "unpaid_invoices": False,
                "closed_by_member": False,
            }
            account.update(changes)
            return account

        def test_due_basis_and_precedence(self) -> None:
            result = plan_purge(
                [
                    self.account(1, last_seen_at=date(2022, 1, 1)),
                    self.account(
                        2,
                        last_seen_at=date(2025, 1, 1),
                        closed_at=date(2024, 1, 1),
                    ),
                    self.account(
                        3,
                        last_seen_at=date(2022, 1, 1),
                        last_login=date(2030, 1, 1),
                    ),
                ],
                self.today,
            )
            self.assertEqual([a["account_id"] for a in result], [1, 2, 3])
            self.assertEqual(result[1]["due"], "2024-01-31")
            self.assertEqual(result[2]["due"], "2023-12-31")

        def test_due_today_and_warning_boundaries(self) -> None:
            result = plan_purge(
                [
                    self.account(1, last_seen_at=date(2023, 1, 1)),
                    self.account(2, last_seen_at=date(2023, 1, 2)),
                    self.account(3, last_seen_at=date(2023, 1, 15)),
                    self.account(4, last_seen_at=date(2023, 1, 16)),
                ],
                self.today,
            )
            self.assertEqual(
                [(a["account_id"], a["action"]) for a in result],
                [(1, "deletion"), (2, "warning"), (3, "warning")],
            )

        def test_unpaid_and_exclusions(self) -> None:
            result = plan_purge(
                [
                    self.account(1, unpaid_invoices=True),
                    self.account(2, litigation_hold=True),
                    self.account(3, email="staff@tidewater-klatring.no"),
                    self.account(4, last_seen_at=None),
                ],
                self.today,
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["action"], "anonymisation")
            self.assertEqual(result[0]["approved_by"], APPROVER)

        def test_member_closed_suppresses_warning(self) -> None:
            result = plan_purge(
                [
                    self.account(
                        1,
                        last_seen_at=date(2024, 1, 2),
                        closed_at=date(2025, 1, 1),
                        closed_by_member=True,
                    )
                ],
                self.today,
            )
            self.assertEqual(result, [])

        def test_cap_priority_tie_break_and_anonymisation(self) -> None:
            accounts = [
                self.account(i, last_seen_at=date(2020, 1, 1))
                for i in range(1, 204)
            ]
            accounts.extend(
                [
                    self.account(
                        300,
                        last_seen_at=date(2025, 1, 1),
                        closed_at=date(2020, 1, 1),
                    ),
                    self.account(301, unpaid_invoices=True),
                ]
            )
            result = plan_purge(accounts, self.today)
            deletions = [a for a in result if a["action"] == "deletion"]
            self.assertEqual(len(deletions), DELETION_CAP)
            self.assertEqual(deletions[0]["account_id"], 1)
            self.assertEqual(deletions[-1]["account_id"], 300)
            self.assertIn(
                {"account_id": 301, "action": "anonymisation",
                 "due": "2023-12-31", "approved_by": APPROVER},
                result,
            )

        def test_exact_fields_and_order(self) -> None:
            result = plan_purge(
                [self.account(2), self.account(1, unpaid_invoices=True)],
                self.today,
            )
            self.assertEqual([a["account_id"] for a in result], [1, 2])
            self.assertTrue(
                all(
                    set(a) == {"account_id", "action", "due", "approved_by"}
                    for a in result
                )
            )
            self.assertEqual(result[0]["action"], "anonymisation")

    unittest.main()