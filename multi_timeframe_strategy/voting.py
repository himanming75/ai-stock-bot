from __future__ import annotations
from collections import defaultdict
from typing import Any

def vote(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        if row.get("eligible"):
            grouped[str(row.get("symbol"))].append(row)
    candidates = []
    for symbol, items in grouped.items():
        signed = 0.0
        support = []
        for item in items:
            direction = 1 if str(item.get("action")).upper() == "BUY" else -1
            weighted = direction * float(item.get("strategy_score", 0)) * float(item.get("capital_weight_pct", 0)) / 100
            signed += weighted
            support.append({
                "strategy_id": item.get("strategy_id"),
                "profile": item.get("profile"),
                "timeframe": item.get("timeframe"),
                "action": item.get("action"),
                "weighted_vote": round(weighted, 4),
            })
        action = "BUY" if signed > 0 else "SELL"
        candidates.append({
            "symbol": symbol,
            "action": action,
            "ensemble_score": round(abs(signed), 4),
            "support": support,
        })
    candidates.sort(key=lambda row: row["ensemble_score"], reverse=True)
    return candidates
