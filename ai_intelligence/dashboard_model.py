from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


class DashboardV2ModelBuilder:
    def build(
        self,
        *,
        regime: dict[str, Any],
        scanner_ranking: list[dict[str, Any]],
        sector_ranking: list[dict[str, Any]],
        explanations: list[dict[str, Any]],
        ai_v2_bundle_1: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "stage": "AI_V2_DASHBOARD_2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_regime": regime,
            "top_symbols": scanner_ranking[:10],
            "top_sectors": sector_ranking[:10],
            "strategy_explanations": explanations[:10],
            "strategy_ranking": ai_v2_bundle_1.get("strategy_ranking", []),
            "learning_summary": ai_v2_bundle_1.get("learning_summary", {}),
            "portfolio_optimization": ai_v2_bundle_1.get(
                "portfolio_optimization", {}
            ),
            "dynamic_risk_decisions": ai_v2_bundle_1.get(
                "dynamic_risk_decisions", []
            ),
            "read_only": True,
            "broker_actions_available": False,
            "automatic_order_submission_enabled": False,
        }
