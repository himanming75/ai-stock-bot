from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


class MetricsCollector:
    def collect(
        self,
        *,
        shadow_result: dict[str, Any],
        feature_result: dict[str, Any],
        validation_result: dict[str, Any],
    ) -> dict[str, Any]:
        portfolio = shadow_result.get("shadow_portfolio_snapshot", {})
        risk = shadow_result.get("shadow_risk", {})
        ensemble = feature_result.get("ensemble_result", {})

        checks = {
            "shadow_status_pass": shadow_result.get("status") == "PASS",
            "feature_status_pass": feature_result.get("status") == "PASS",
            "validation_status_pass": validation_result.get("status") == "PASS",
            "release_locked": shadow_result.get("release_gate") == "LOCKED",
            "orders_zero": (
                shadow_result.get("actual_paper_orders_submitted") == 0
                and shadow_result.get("actual_live_orders_submitted") == 0
            ),
        }
        return {
            "stage": "AI_MONITORING_METRICS",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "failed": [key for key, value in checks.items() if not value],
            "health_status": "PASS" if all(checks.values()) else "FAIL",
            "shadow_equity": portfolio.get("equity", "0"),
            "shadow_cash": portfolio.get("cash", "0"),
            "shadow_realized_pnl": portfolio.get("realized_pnl", "0"),
            "shadow_unrealized_pnl": portfolio.get("unrealized_pnl", "0"),
            "shadow_risk_state": risk.get("risk_state", "UNKNOWN"),
            "maximum_drawdown": risk.get("maximum_drawdown", "0"),
            "ensemble_score": ensemble.get("ensemble_score", "0"),
            "ensemble_signal": ensemble.get("signal", "HOLD"),
            "release_gate": shadow_result.get("release_gate", "UNKNOWN"),
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_order_submission_performed": False,
        }
