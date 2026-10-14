"""Seat proration invoice lines.

Day-count convention: use calendar dates and count [changed_at.date(),
period_end.date()), so the change date is excluded and period end is excluded.
Clamp the resulting day count to 0–30.
"""

from datetime import datetime
import unittest


def _description(plan_name: str, kind: str, period_end: datetime) -> str:
    date = period_end.date().isoformat()
    prefix = f"{plan_name} {kind} through "
    return prefix[: max(0, 80 - len(date))] + date


def _vat(amount_cents: int) -> int:
    """Round 21% VAT half-up to an integer cent."""
    return (amount_cents * 21 + 50) // 100


def prorate_seats(subscription, new_plan, changed_at):
    """Return credit and charge lines for a seat-plan change."""
    if subscription["status"] == "trialing":
        return []

    old_price = subscription["seat_price_cents"]
    new_price = new_plan["seat_price_cents"]
    if new_price < old_price:
        return []

    period_end = subscription["period_end"]
    days = max(0, min(30, (period_end.date() - changed_at.date()).days))
    seats = subscription["billable_seats"]
    vat_id = subscription["vat_id"]
    lines = []

    if old_price > 0 and seats > 0 and days > 0:
        numerator = old_price * seats * days
        amount = (numerator + 29) // 30
        if amount >= 50:
            lines.append({
                "subscription_id": subscription["id"],
                "kind": "credit",
                "amount_cents": amount,
                "vat_cents": 0 if vat_id else _vat(amount),
                "description": _description(
                    subscription["plan_name"], "credit", period_end
                ),
                "approved_by": (
                    "Ramón Etxeberria-Goñi"
                    if amount > 50_000
                    else "Nguyễn Thị Phương Thảo"
                ),
            })

    if new_price > 0 and seats > 0 and days > 0:
        amount = new_price * seats * days // 30
        if amount >= 50:
            lines.append({
                "subscription_id": subscription["id"],
                "kind": "charge",
                "amount_cents": amount,
                "vat_cents": 0 if vat_id else _vat(amount),
                "description": _description(new_plan["name"], "charge", period_end),
                "approved_by": None,
            })

    return lines


class ProrateSeatsTests(unittest.TestCase):
    def setUp(self):
        self.subscription = {
            "id": "sub-1",
            "status": "active",
            "plan_name": "Old plan",
            "seat_price_cents": 101,
            "seats": 99,
            "billable_seats": 1,
            "vat_id": None,
            "period_end": datetime.fromisoformat("2025-02-01T00:00:00+00:00"),
        }
        self.new_plan = {"name": "New plan", "seat_price_cents": 200}

    def test_rounding_boundaries_and_credit_first(self):
        lines = prorate_seats(
            self.subscription, self.new_plan,
            datetime.fromisoformat("2025-01-30T00:00:00+00:00"),
        )
        self.assertEqual([line["kind"] for line in lines], ["credit", "charge"])
        self.assertEqual([line["amount_cents"] for line in lines], [7, 6])
        self.assertEqual(prorate_seats(
            {**self.subscription, "seat_price_cents": 1500},
            {"name": "New", "seat_price_cents": 1800},
            datetime.fromisoformat("2025-01-30T00:00:00+00:00"),
        )[0]["amount_cents"], 100)

    def test_change_date_cutoff_and_out_of_period_clamping(self):
        for changed_at in (
            datetime.fromisoformat("2025-02-01T00:00:00+00:00"),
            datetime.fromisoformat("2025-02-02T00:00:00+00:00"),
        ):
            self.assertEqual(prorate_seats(self.subscription, self.new_plan, changed_at), [])
        lines = prorate_seats(
            self.subscription, self.new_plan,
            datetime.fromisoformat("2024-12-01T00:00:00+00:00"),
        )
        self.assertEqual([line["amount_cents"] for line in lines], [101, 200])

    def test_downgrade_and_trialing(self):
        changed_at = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
        self.assertEqual(
            prorate_seats(self.subscription, {"name": "Cheaper", "seat_price_cents": 50}, changed_at),
            [],
        )
        self.assertEqual(
            prorate_seats(
                {**self.subscription, "status": "trialing"}, self.new_plan, changed_at
            ),
            [],
        )

    def test_vat_and_reverse_charge(self):
        changed_at = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
        lines = prorate_seats(self.subscription, self.new_plan, changed_at)
        self.assertEqual([line["vat_cents"] for line in lines], [22, 42])
        reversed_lines = prorate_seats(
            {**self.subscription, "vat_id": "VAT-1"}, self.new_plan, changed_at
        )
        self.assertEqual([line["vat_cents"] for line in reversed_lines], [0, 0])

    def test_credit_approval_threshold(self):
        changed_at = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
        line = prorate_seats(
            {**self.subscription, "seat_price_cents": 50_000},
            {"name": "New", "seat_price_cents": 50_001},
            changed_at,
        )[0]
        self.assertEqual(line["approved_by"], "Ramón Etxeberria-Goñi")

    def test_description_is_at_most_80_characters_and_keeps_date(self):
        changed_at = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
        lines = prorate_seats(
            {**self.subscription, "plan_name": "A" * 200},
            {"name": "B" * 200, "seat_price_cents": 200},
            changed_at,
        )
        for line in lines:
            self.assertLessEqual(len(line["description"]), 80)
            self.assertTrue(line["description"].endswith("2025-02-01"))


if __name__ == "__main__":
    unittest.main()
```