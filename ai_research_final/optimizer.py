from __future__ import annotations
from decimal import Decimal
import itertools
import random
from typing import Any, Callable


class ParameterOptimizer:
    def grid_search(
        self,
        *,
        grid: dict[str, list[Any]],
        objective: Callable[[dict[str, Any]], Decimal],
    ) -> dict[str, Any]:
        keys = sorted(grid)
        combinations = [
            dict(zip(keys, values))
            for values in itertools.product(*(grid[key] for key in keys))
        ]
        rows = []
        for params in combinations:
            score = objective(params)
            rows.append({
                "parameters": params,
                "score": str(score.quantize(Decimal("0.0001"))),
            })
        rows.sort(
            key=lambda row: Decimal(row["score"]),
            reverse=True,
        )
        return {
            "method": "GRID_SEARCH",
            "evaluation_count": len(rows),
            "best": rows[0],
            "results": rows,
            "actual_strategy_parameters_changed": False,
        }

    def random_search(
        self,
        *,
        space: dict[str, list[Any]],
        evaluations: int,
        objective: Callable[[dict[str, Any]], Decimal],
        seed: int = 11,
    ) -> dict[str, Any]:
        if evaluations <= 0:
            raise ValueError("EVALUATIONS_MUST_BE_POSITIVE")
        rng = random.Random(seed)
        rows = []
        for _ in range(evaluations):
            params = {
                key: rng.choice(values)
                for key, values in sorted(space.items())
            }
            score = objective(params)
            rows.append({
                "parameters": params,
                "score": str(score.quantize(Decimal("0.0001"))),
            })
        rows.sort(
            key=lambda row: Decimal(row["score"]),
            reverse=True,
        )
        return {
            "method": "RANDOM_SEARCH",
            "evaluation_count": len(rows),
            "best": rows[0],
            "results": rows,
            "actual_strategy_parameters_changed": False,
        }


class BayesianOptimizationInterface:
    def describe(self) -> dict[str, Any]:
        return {
            "interface_ready": True,
            "backend_connected": False,
            "supported_future_backends": [
                "OPTUNA",
                "SCIKIT_OPTIMIZE",
                "CUSTOM_GAUSSIAN_PROCESS",
            ],
            "actual_bayesian_optimization_performed": False,
        }
