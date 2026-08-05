from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LiveRiskPolicy:
    maximum_order_notional: float
    maximum_daily_orders: int
    maximum_daily_loss: float
    maximum_total_exposure: float
    maximum_position_count: int
    allowed_symbols: tuple[str, ...]
    allowed_account_ids: tuple[str, ...]

    def evaluate(self) -> dict[str, Any]:
        checks = {
            "maximum_order_notional_safe": (
                0 < self.maximum_order_notional <= 100
            ),
            "maximum_daily_orders_safe": (
                1 <= self.maximum_daily_orders <= 10
            ),
            "maximum_daily_loss_safe": (
                0 < self.maximum_daily_loss <= 100
            ),
            "maximum_total_exposure_safe": (
                0 < self.maximum_total_exposure <= 500
            ),
            "maximum_position_count_safe": (
                1 <= self.maximum_position_count <= 5
            ),
            "allowed_symbols_restricted": (
                1 <= len(self.allowed_symbols) <= 3
            ),
            "allowed_account_ids_restricted": (
                len(self.allowed_account_ids) <= 1
            ),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }
