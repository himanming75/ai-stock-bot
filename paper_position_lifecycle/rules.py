from __future__ import annotations
from typing import Any

def evaluate_exit(
    position: dict[str, Any],
    mark_price: float,
    holding_days: int,
    high_water_mark: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    average_cost = float(position.get("average_cost", 0.0))
    quantity = float(position.get("quantity", 0.0))
    if average_cost <= 0 or quantity <= 0 or mark_price <= 0:
        return {
            "action": "HOLD",
            "reason": "INVALID_POSITION_OR_MARK",
            "return_pct": 0.0,
            "trailing_drawdown_pct": 0.0,
        }

    return_pct = (mark_price / average_cost - 1.0) * 100.0
    stop_loss_pct = float(policy.get("stop_loss_pct", 5.0))
    take_profit_pct = float(policy.get("take_profit_pct", 10.0))
    trailing_stop_pct = float(policy.get("trailing_stop_pct", 4.0))
    maximum_holding_days = int(policy.get("maximum_holding_days", 20))

    effective_high = max(high_water_mark, mark_price)
    trailing_drawdown_pct = (
        (effective_high - mark_price) / effective_high * 100.0
        if effective_high > 0 else 0.0
    )

    if return_pct <= -stop_loss_pct:
        action, reason = "EXIT", "STOP_LOSS"
    elif return_pct >= take_profit_pct:
        action, reason = "EXIT", "TAKE_PROFIT"
    elif trailing_drawdown_pct >= trailing_stop_pct and return_pct > 0:
        action, reason = "EXIT", "TRAILING_STOP"
    elif holding_days >= maximum_holding_days:
        action, reason = "EXIT", "MAX_HOLDING_PERIOD"
    else:
        action, reason = "HOLD", "NO_EXIT_TRIGGER"

    return {
        "action": action,
        "reason": reason,
        "return_pct": round(return_pct, 4),
        "trailing_drawdown_pct": round(trailing_drawdown_pct, 4),
        "effective_high_water_mark": round(effective_high, 4),
    }
