from __future__ import annotations
from decimal import Decimal
from typing import Any


DEFAULT_STRATEGIES = [
    {
        "strategy_id": "momentum_v2",
        "display_name": "Momentum V2",
        "category": "TREND",
        "horizons": ["ultra_short", "day", "swing"],
        "enabled": True,
        "priority": 1,
        "risk_tier": "MEDIUM",
    },
    {
        "strategy_id": "mean_reversion_v2",
        "display_name": "Mean Reversion V2",
        "category": "MEAN_REVERSION",
        "horizons": ["day", "swing"],
        "enabled": True,
        "priority": 2,
        "risk_tier": "MEDIUM",
    },
    {
        "strategy_id": "breakout_v2",
        "display_name": "Breakout V2",
        "category": "BREAKOUT",
        "horizons": ["ultra_short", "day"],
        "enabled": False,
        "priority": 3,
        "risk_tier": "HIGH",
    },
    {
        "strategy_id": "opening_range_v1",
        "display_name": "Opening Range",
        "category": "INTRADAY",
        "horizons": ["ultra_short", "day"],
        "enabled": False,
        "priority": 4,
        "risk_tier": "HIGH",
    },
    {
        "strategy_id": "gap_v1",
        "display_name": "Gap Strategy",
        "category": "EVENT",
        "horizons": ["ultra_short", "day"],
        "enabled": False,
        "priority": 5,
        "risk_tier": "HIGH",
    },
    {
        "strategy_id": "trend_following_v1",
        "display_name": "Trend Following",
        "category": "TREND",
        "horizons": ["swing", "position"],
        "enabled": False,
        "priority": 6,
        "risk_tier": "LOW",
    },
    {
        "strategy_id": "scalping_v1",
        "display_name": "Scalping",
        "category": "INTRADAY",
        "horizons": ["ultra_short"],
        "enabled": False,
        "priority": 7,
        "risk_tier": "VERY_HIGH",
    },
    {
        "strategy_id": "swing_v1",
        "display_name": "Swing Strategy",
        "category": "SWING",
        "horizons": ["swing"],
        "enabled": False,
        "priority": 8,
        "risk_tier": "MEDIUM",
    },
]


class StrategyMarketplace:
    def build(
        self,
        *,
        strategy_ranking: list[dict[str, Any]],
    ) -> dict[str, Any]:
        score_map = {
            row.get("strategy_id"): Decimal(
                str(row.get("total_score", row.get("score", "0")))
            )
            for row in strategy_ranking
        }
        rows = []
        for strategy in DEFAULT_STRATEGIES:
            score = score_map.get(
                strategy["strategy_id"], Decimal("0")
            )
            rows.append({
                **strategy,
                "research_score": str(
                    score.quantize(Decimal("0.0001"))
                ),
                "recommended": (
                    strategy["enabled"] and score >= Decimal("0.60")
                ),
                "actual_activation_performed": False,
            })
        rows.sort(
            key=lambda row: (
                row["enabled"],
                Decimal(row["research_score"]),
                -row["priority"],
            ),
            reverse=True,
        )
        return {
            "strategy_count": len(rows),
            "enabled_count": sum(1 for row in rows if row["enabled"]),
            "strategies": rows,
            "configuration_preview_only": True,
            "actual_strategy_activation_performed": False,
        }
