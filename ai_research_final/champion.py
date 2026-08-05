from __future__ import annotations
from decimal import Decimal
from typing import Any


class ChampionChallengerManager:
    def evaluate(
        self,
        *,
        candidates: list[dict[str, Any]],
        minimum_score: Decimal,
        minimum_margin: Decimal,
    ) -> dict[str, Any]:
        if not candidates:
            raise ValueError("CANDIDATES_REQUIRED")
        ranked = sorted(
            candidates,
            key=lambda row: Decimal(str(row["score"])),
            reverse=True,
        )
        champion = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        margin = (
            Decimal(str(champion["score"]))
            - Decimal(str(runner_up["score"]))
            if runner_up else Decimal("999")
        )
        eligible = (
            Decimal(str(champion["score"])) >= minimum_score
            and margin >= minimum_margin
        )
        return {
            "champion_candidate": champion,
            "challengers": ranked[1:],
            "promotion_eligible": eligible,
            "promotion_margin": str(margin.quantize(Decimal("0.0001"))),
            "actual_promotion_performed": False,
            "operator_approval_required": True,
        }
