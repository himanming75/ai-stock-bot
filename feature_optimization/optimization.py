from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import itertools
import json
import random
from pathlib import Path
from typing import Any, Callable


class AutoOptimizer:
    def grid_search(
        self,
        *,
        grid: dict[str, list[Any]],
        objective: Callable[[dict[str, Any]], Decimal],
    ) -> dict[str, Any]:
        keys = sorted(grid)
        rows = []
        for values in itertools.product(*(grid[key] for key in keys)):
            params = dict(zip(keys, values))
            rows.append({
                "parameters": params,
                "score": str(
                    objective(params).quantize(Decimal("0.0001"))
                ),
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
        seed: int = 21,
    ) -> dict[str, Any]:
        rng = random.Random(seed)
        rows = []
        for _ in range(evaluations):
            params = {
                key: rng.choice(values)
                for key, values in sorted(space.items())
            }
            rows.append({
                "parameters": params,
                "score": str(
                    objective(params).quantize(Decimal("0.0001"))
                ),
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


class OptimizationHistory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(
        self,
        *,
        strategy_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "strategy_id": strategy_id,
            "method": result["method"],
            "evaluation_count": result["evaluation_count"],
            "best": result["best"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "actual_promotion_performed": False,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record


class ChampionCandidatePreview:
    def evaluate(
        self,
        *,
        current_score: Decimal,
        candidate_score: Decimal,
        minimum_margin: Decimal,
    ) -> dict[str, Any]:
        margin = candidate_score - current_score
        eligible = margin >= minimum_margin
        return {
            "current_score": str(current_score),
            "candidate_score": str(candidate_score),
            "margin": str(margin.quantize(Decimal("0.0001"))),
            "promotion_eligible": eligible,
            "actual_promotion_performed": False,
            "operator_approval_required": True,
        }


class RollbackPreview:
    def build(
        self,
        *,
        current_version: str,
        target_version: str,
    ) -> dict[str, Any]:
        return {
            "current_version": current_version,
            "target_version": target_version,
            "rollback_preview_allowed": bool(target_version),
            "actual_rollback_performed": False,
            "operator_approval_required": True,
        }
