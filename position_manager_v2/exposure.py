from __future__ import annotations
from collections import defaultdict
from typing import Any

def calculate(positions: list[dict[str, Any]], cash: float) -> dict[str, Any]:
    total_market = sum(float(p.get("market_value", 0) or 0) for p in positions)
    equity = total_market + float(cash)
    sectors = defaultdict(float)
    rows = []
    for p in positions:
        value = float(p.get("market_value", 0) or 0)
        weight = value / equity * 100 if equity else 0
        sectors[str(p.get("sector", "UNKNOWN"))] += value
        rows.append({"symbol": p.get("symbol"), "market_value": value, "weight_pct": round(weight, 4)})
    sector_rows = [
        {"sector": sector, "market_value": value, "weight_pct": round(value / equity * 100, 4) if equity else 0}
        for sector, value in sorted(sectors.items())
    ]
    return {
        "equity": round(equity, 2),
        "cash": round(float(cash), 2),
        "cash_weight_pct": round(float(cash) / equity * 100, 4) if equity else 0,
        "invested_value": round(total_market, 2),
        "symbol_exposure": rows,
        "sector_exposure": sector_rows,
    }
