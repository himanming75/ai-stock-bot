from __future__ import annotations
import random
import statistics
from typing import Any

def simulate(
    returns: list[float],
    initial_value: float,
    iterations: int = 1000,
    horizon_days: int = 20,
    seed: int = 92064,
) -> dict[str, Any]:
    if not returns:
        return {
            "iterations": 0,
            "horizon_days": horizon_days,
            "loss_probability_pct": 0.0,
            "median_ending_value": initial_value,
            "worst_5pct_ending_value": initial_value,
            "best_95pct_ending_value": initial_value,
        }

    rng = random.Random(seed)
    endings = []
    for _ in range(iterations):
        value = initial_value
        for _ in range(horizon_days):
            value *= 1.0 + rng.choice(returns)
        endings.append(value)

    endings.sort()
    losses = [value for value in endings if value < initial_value]
    index_5 = max(0, int(iterations * 0.05) - 1)
    index_95 = min(iterations - 1, int(iterations * 0.95))
    return {
        "iterations": iterations,
        "horizon_days": horizon_days,
        "loss_probability_pct": round(
            len(losses) / iterations * 100.0, 4
        ),
        "median_ending_value": round(statistics.median(endings), 4),
        "worst_5pct_ending_value": round(endings[index_5], 4),
        "best_95pct_ending_value": round(endings[index_95], 4),
    }
