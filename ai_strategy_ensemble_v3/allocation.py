from __future__ import annotations
from typing import Any

def allocate(rows: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    active = [row for row in rows if row["eligible"]]
    active.sort(key=lambda row: row["score"], reverse=True)
    active = active[: int(policy["maximum_active_strategies"])]
    if not active:
        return []
    total = sum(row["score"] for row in active) or 1.0
    maximum = float(policy["maximum_single_strategy_weight_pct"])
    allocations = []
    for row in active:
        weight = min(maximum, row["score"] / total * 100)
        allocations.append({**row, "weight_pct": weight})
    weight_total = sum(row["weight_pct"] for row in allocations) or 1.0
    for row in allocations:
        row["weight_pct"] = round(row["weight_pct"] / weight_total * 100, 4)
    return allocations
