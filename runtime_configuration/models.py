from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RuntimeRiskLimits:
    maximum_order_notional: Decimal
    maximum_daily_orders: int
    maximum_daily_loss: Decimal
    maximum_gross_exposure: Decimal
    maximum_symbol_exposure: Decimal

    def as_json(self) -> dict[str, Any]:
        return {
            "maximum_order_notional": str(self.maximum_order_notional),
            "maximum_daily_orders": self.maximum_daily_orders,
            "maximum_daily_loss": str(self.maximum_daily_loss),
            "maximum_gross_exposure": str(self.maximum_gross_exposure),
            "maximum_symbol_exposure": str(self.maximum_symbol_exposure),
        }


@dataclass(frozen=True)
class RuntimeConfiguration:
    profile_name: str
    broker_mode: str
    horizon: str
    allowed_symbols: tuple[str, ...]
    allowed_order_types: tuple[str, ...]
    time_in_force: str
    require_market_open: bool
    allocation_enabled: bool
    multi_account_enabled: bool
    profile_enabled: bool
    risk_limits: RuntimeRiskLimits
    broker_network_enabled: bool
    broker_write_enabled: bool
    automatic_order_submission_enabled: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "broker_mode": self.broker_mode,
            "horizon": self.horizon,
            "allowed_symbols": list(self.allowed_symbols),
            "allowed_order_types": list(self.allowed_order_types),
            "time_in_force": self.time_in_force,
            "require_market_open": self.require_market_open,
            "allocation_enabled": self.allocation_enabled,
            "multi_account_enabled": self.multi_account_enabled,
            "profile_enabled": self.profile_enabled,
            "risk_limits": self.risk_limits.as_json(),
            "broker_network_enabled": self.broker_network_enabled,
            "broker_write_enabled": self.broker_write_enabled,
            "automatic_order_submission_enabled": (
                self.automatic_order_submission_enabled
            ),
        }
