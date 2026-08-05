from __future__ import annotations
from decimal import Decimal
import random
from typing import Any


class MonteCarloSimulator:
    def simulate(
        self,
        *,
        returns: list[Decimal],
        simulations: int,
        horizon: int,
        seed: int = 7,
    ) -> dict[str, Any]:
        if not returns:
            raise ValueError("RETURNS_REQUIRED")
        if simulations <= 0 or horizon <= 0:
            raise ValueError("SIMULATION_COUNTS_MUST_BE_POSITIVE")

        rng = random.Random(seed)
        ending_equities = []
        maximum_drawdowns = []
        ruin_count = 0

        for _ in range(simulations):
            equity = Decimal("1")
            peak = Decimal("1")
            max_drawdown = Decimal("0")
            for _step in range(horizon):
                result = returns[rng.randrange(len(returns))]
                equity *= Decimal("1") + result
                peak = max(peak, equity)
                if peak > 0:
                    drawdown = (peak - equity) / peak
                    max_drawdown = max(max_drawdown, drawdown)
                if equity <= Decimal("0.5"):
                    ruin_count += 1
                    break
            ending_equities.append(equity)
            maximum_drawdowns.append(max_drawdown)

        ending_sorted = sorted(ending_equities)
        drawdown_sorted = sorted(maximum_drawdowns)
        def percentile(values, fraction):
            index = min(len(values) - 1, max(0, int((len(values)-1) * fraction)))
            return values[index]

        return {
            "simulation_count": simulations,
            "horizon": horizon,
            "median_ending_equity": str(
                percentile(ending_sorted, 0.50).quantize(Decimal("0.0001"))
            ),
            "p05_ending_equity": str(
                percentile(ending_sorted, 0.05).quantize(Decimal("0.0001"))
            ),
            "p95_ending_equity": str(
                percentile(ending_sorted, 0.95).quantize(Decimal("0.0001"))
            ),
            "median_maximum_drawdown": str(
                percentile(drawdown_sorted, 0.50).quantize(Decimal("0.0001"))
            ),
            "p95_maximum_drawdown": str(
                percentile(drawdown_sorted, 0.95).quantize(Decimal("0.0001"))
            ),
            "risk_of_ruin": str(
                (Decimal(ruin_count) / Decimal(simulations)).quantize(
                    Decimal("0.0001")
                )
            ),
            "actual_capital_used": False,
        }
