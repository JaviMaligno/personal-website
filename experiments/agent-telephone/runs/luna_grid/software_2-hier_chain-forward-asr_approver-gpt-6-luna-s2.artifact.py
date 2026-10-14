from datetime import datetime
from typing import Any


def prorate_seats(
    subscription: dict[str, Any],
    new_plan: dict[str, Any],
    changed_at: datetime,
) -> list[dict[str, Any]]:
    """Prorate a plan change once the caller supplies how the new seat count is represented."""
    if subscription["status"] == "trialing":
        return []

    if new_plan["seat_price_cents"] < subscription["seat_price_cents"]:
        return []

    raise ValueError(
        "New seat count is unspecified; clarify how seat changes are represented."
    )