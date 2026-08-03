from __future__ import annotations

DEFAULT_WEIGHTS = {
    "return": 1.0,
    "sharpe": 5.0,
    "drawdown": -0.8,
    "profit_factor": 2.0,
    "win_rate": 0.08,
    "excess_return": 1.2,
    "gate_bonus": 25.0,
}

def champion_score(row: dict, weights: dict | None = None) -> float:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    gate = row.get("gate", {})
    pf = min(float(row.get("profit_factor", 0.0)), 10.0)
    value = (
        w["return"] * float(row.get("total_return_pct", 0.0))
        + w["sharpe"] * float(row.get("sharpe_ratio", 0.0))
        + w["drawdown"] * float(row.get("maximum_drawdown_pct", 0.0))
        + w["profit_factor"] * pf
        + w["win_rate"] * float(row.get("win_rate_pct", 0.0))
        + w["excess_return"] * float(gate.get("excess_return_pct", 0.0))
        + (w["gate_bonus"] if gate.get("approved") else 0.0)
    )
    return round(value, 4)
