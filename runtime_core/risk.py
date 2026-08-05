from __future__ import annotations
from decimal import Decimal
from typing import Any

from .models import Signal


class RuntimeRiskEvaluator:
    def evaluate(
        self,
        *,
        signal: Signal,
        runtime_snapshot: dict[str, Any],
        daily_state: dict[str, Any],
    ) -> dict[str, Any]:
        risk = runtime_snapshot["risk_limits"]
        max_daily_orders = int(risk["maximum_daily_orders"])
        max_daily_loss = Decimal(str(risk["maximum_daily_loss"]))
        daily_orders = int(daily_state.get("order_count", 0))
        realized_loss = Decimal(str(daily_state.get("realized_loss", "0")))

        signal_validation = signal.validate()
        checks = {
            "signal_valid": signal_validation["valid"],
            "symbol_allowed": signal.symbol in runtime_snapshot.get(
                "allowed_symbols", []
            ),
            "daily_order_count_available": daily_orders < max_daily_orders,
            "daily_loss_within_limit": realized_loss < max_daily_loss,
            "market_gate_preserved": (
                runtime_snapshot.get("require_market_open") is True
            ),
            "broker_network_off": (
                runtime_snapshot.get("broker_network_enabled") is False
            ),
            "broker_write_off": (
                runtime_snapshot.get("broker_write_enabled") is False
            ),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "approved": all(checks.values()) and signal.side != "hold",
            "signal_validation": signal_validation,
            "broker_submission_allowed": False,
        }
