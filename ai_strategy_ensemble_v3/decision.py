from __future__ import annotations
from collections import defaultdict
from typing import Any

def combine(allocations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for row in allocations:
        grouped[str(row.get("symbol", "UNKNOWN"))].append(row)
    results = []
    for symbol, rows in sorted(grouped.items()):
        signed = 0.0
        support = []
        for row in rows:
            direction = 1 if row["action"] == "BUY" else (-1 if row["action"] == "SELL" else 0)
            contribution = direction * row["weight_pct"] * row["signal_confidence"] / 100
            signed += contribution
            support.append({
                "strategy_id": row["strategy_id"],
                "action": row["action"],
                "weight_pct": row["weight_pct"],
                "contribution": round(contribution, 4),
            })
        action = "BUY" if signed > 10 else ("SELL" if signed < -10 else "HOLD")
        results.append({
            "symbol": symbol,
            "action": action,
            "confidence": round(min(100.0, abs(signed)), 4),
            "support": support,
        })
    return results
