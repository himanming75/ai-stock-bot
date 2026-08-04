from __future__ import annotations
from typing import Any

def apply_fill(order: dict[str, Any], quantity: float, price: float) -> dict[str, Any]:
    ordered = float(order.get("quantity", 0) or 0)
    filled = float(order.get("filled_quantity", 0) or 0)
    average = float(order.get("average_fill_price", 0) or 0)
    fill_qty = max(0.0, float(quantity))
    if filled + fill_qty > ordered:
        raise ValueError("Fill quantity exceeds ordered quantity.")
    total_value = average * filled + float(price) * fill_qty
    new_filled = filled + fill_qty
    new_average = total_value / new_filled if new_filled else 0.0
    remaining = ordered - new_filled
    state = "FILLED" if remaining == 0 and ordered > 0 else "PARTIALLY_FILLED"
    return {
        **order,
        "filled_quantity": new_filled,
        "remaining_quantity": remaining,
        "average_fill_price": round(new_average, 6),
        "state": state,
    }
