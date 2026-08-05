from __future__ import annotations
import random
from statistics import mean


def simulate(
    returns: list[float],
    *,
    simulations: int = 500,
    seed: int = 42,
) -> dict:
    if not returns:
        return {
            "simulation_count": 0,
            "median_cumulative_return": 0.0,
            "p05_cumulative_return": 0.0,
            "p95_cumulative_return": 0.0,
            "loss_probability": 0.0,
        }

    rng = random.Random(seed)
    outcomes = []

    for _ in range(simulations):
        equity = 1.0
        for _ in range(len(returns)):
            equity *= 1.0 + rng.choice(returns)
        outcomes.append(equity - 1.0)

    outcomes.sort()

    def percentile(p):
        index = int((len(outcomes) - 1) * p)
        return outcomes[index]

    return {
        "simulation_count": simulations,
        "median_cumulative_return": round(percentile(0.50), 8),
        "p05_cumulative_return": round(percentile(0.05), 8),
        "p95_cumulative_return": round(percentile(0.95), 8),
        "mean_cumulative_return": round(mean(outcomes), 8),
        "loss_probability": round(
            sum(1 for value in outcomes if value < 0) / len(outcomes),
            8,
        ),
        "seed": seed,
    }
