from __future__ import annotations
from typing import Any

def allocate(
    ranked: list[dict[str, Any]],
    top_n: int,
    max_weight_pct: float,
) -> list[dict[str, Any]]:
    selected = ranked[:max(1, top_n)]
    positives = [max(0.0, float(row.get("meta_score", 0.0))) for row in selected]
    total = sum(positives)
    if total <= 0:
        raw = [1.0 / len(selected)] * len(selected) if selected else []
    else:
        raw = [value / total for value in positives]

    cap = max_weight_pct / 100.0
    weights = raw[:]
    for _ in range(30):
        excess = 0.0
        free = []
        for index, value in enumerate(weights):
            if value > cap:
                excess += value - cap
                weights[index] = cap
            else:
                free.append(index)
        if excess <= 1e-12 or not free:
            break
        add = excess / len(free)
        for index in free:
            weights[index] += add

    total_after = sum(weights)
    if total_after > 0:
        weights = [value / total_after for value in weights]

    output = []
    for row, weight in zip(selected, weights):
        output.append({
            "strategy_id": row.get("strategy_id"),
            "base_strategy": row.get("base_strategy"),
            "meta_rank": row.get("meta_rank"),
            "meta_score": row.get("meta_score"),
            "weight_pct": round(weight * 100.0, 4),
        })
    return output
