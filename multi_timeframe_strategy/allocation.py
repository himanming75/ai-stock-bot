from __future__ import annotations
from typing import Any

def build(rows: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    allocations = []
    total_risk = 0.0
    for row in rows:
        if not row.get("eligible"):
            continue
        risk = float(row.get("risk_per_trade_pct", 0) or 0)
        total_risk += risk
        allocations.append({
            "strategy_id": row.get("strategy_id"),
            "symbol": row.get("symbol"),
            "profile": row.get("profile"),
            "capital_weight_pct": row.get("capital_weight_pct"),
            "risk_per_trade_pct": risk,
            "maximum_holding_minutes": row.get("maximum_holding_minutes"),
        })
    return {
        "rows": allocations,
        "total_projected_risk_pct": round(total_risk, 4),
        "within_total_risk_limit": total_risk <= float(policy["maximum_total_risk_pct"]),
    }
