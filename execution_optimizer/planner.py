from __future__ import annotations
from typing import Any

def build(candidate: dict[str, Any], quote: dict[str, Any], fill: dict[str, Any], slippage: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    action = str(candidate.get("action", "HOLD")).upper()
    quantity = int(candidate.get("quantity", 1) or 1)
    confidence = float(candidate.get("confidence", 0) or 0)
    quote_passed = quote.get("passed") is True
    fill_ok = float(fill["fill_probability_pct"]) >= float(policy["minimum_fill_probability_pct"])
    slip_ok = abs(float(slippage["expected_slippage_pct"])) <= float(policy["maximum_expected_slippage_pct"])
    if quote_passed and fill_ok and slip_ok:
        order_type = "LIMIT"
        tif = "DAY"
        offset = float(policy["limit_offset_bps"]) / 10000
        mid = float(quote["mid"])
        limit_price = mid * (1 + offset if action == "BUY" else 1 - offset)
    else:
        order_type = "BLOCKED"
        tif = "NONE"
        limit_price = 0.0
    return {
        "symbol": candidate.get("symbol"),
        "action": action,
        "quantity": quantity,
        "confidence": confidence,
        "order_type": order_type,
        "time_in_force": tif,
        "limit_price": round(limit_price, 4),
        "plan_allowed": order_type != "BLOCKED",
    }
