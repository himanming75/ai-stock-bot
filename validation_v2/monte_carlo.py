from __future__ import annotations

import random
from typing import Any


def run_monte_carlo(
    trades: list[dict[str, Any]],
    *,
    iterations: int = 500,
    seed: int = 8709,
    initial_equity: float = 100000.0,
) -> dict[str, Any]:
    pnls = [float(trade.get("net_pnl", 0.0)) for trade in trades]
    if not pnls:
        return {
            "iterations": iterations,
            "p05_ending_equity": initial_equity,
            "median_ending_equity": initial_equity,
            "p95_ending_equity": initial_equity,
            "probability_of_loss_pct": 0.0,
        }

    rng = random.Random(seed)
    endings = []
    for _ in range(iterations):
        shuffled = list(pnls)
        rng.shuffle(shuffled)
        endings.append(initial_equity + sum(shuffled))

    endings.sort()
    p05 = endings[max(0, int(iterations * 0.05) - 1)]
    median = endings[int(iterations * 0.50)]
    p95 = endings[min(iterations - 1, int(iterations * 0.95))]
    losses = sum(1 for value in endings if value < initial_equity)

    return {
        "iterations": iterations,
        "p05_ending_equity": round(p05, 4),
        "median_ending_equity": round(median, 4),
        "p95_ending_equity": round(p95, 4),
        "probability_of_loss_pct": round(losses / iterations * 100.0, 2),
    }
