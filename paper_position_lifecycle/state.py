from __future__ import annotations
from typing import Any

def build_position_state(
    source_positions: dict[str, Any],
    prior_state: dict[str, Any],
    lifecycle_date: str,
) -> dict[str, Any]:
    output = {}
    prior_positions = prior_state.get("positions", {})
    for symbol, position in source_positions.items():
        prior = prior_positions.get(symbol, {})
        output[symbol] = {
            "quantity": float(position.get("quantity", 0.0)),
            "average_cost": float(position.get("average_cost", 0.0)),
            "opened_date": prior.get("opened_date", lifecycle_date),
            "holding_days": int(prior.get("holding_days", 0)) + 1,
            "high_water_mark": max(
                float(prior.get("high_water_mark", 0.0)),
                float(position.get("mark_price", position.get("average_cost", 0.0))),
            ),
            "status": "OPEN",
        }
    return {"positions": output}
