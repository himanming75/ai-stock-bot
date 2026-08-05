from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


VALID_HORIZONS = {"ultra_short", "day", "swing", "position"}
VALID_MODES = {"paper", "live"}
VALID_ORDER_TYPES = {"market", "limit"}
VALID_TIF = {"day"}


@dataclass(frozen=True)
class TradingProfile:
    profile_name: str
    broker_mode: str
    horizon: str
    allowed_symbols: tuple[str, ...]
    allowed_order_types: tuple[str, ...]
    time_in_force: str
    maximum_order_notional: Decimal
    maximum_daily_orders: int
    maximum_daily_loss: Decimal
    maximum_gross_exposure: Decimal
    maximum_symbol_exposure: Decimal
    require_market_open: bool
    allocation_enabled: bool
    multi_account_enabled: bool
    enabled: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TradingProfile":
        return cls(
            profile_name=str(value.get("profile_name", "")).strip(),
            broker_mode=str(value.get("broker_mode", "")).lower(),
            horizon=str(value.get("horizon", "")).lower(),
            allowed_symbols=tuple(
                str(item).strip().upper()
                for item in value.get("allowed_symbols", [])
                if str(item).strip()
            ),
            allowed_order_types=tuple(
                str(item).strip().lower()
                for item in value.get("allowed_order_types", [])
            ),
            time_in_force=str(value.get("time_in_force", "")).lower(),
            maximum_order_notional=Decimal(
                str(value.get("maximum_order_notional", "0"))
            ),
            maximum_daily_orders=int(
                value.get("maximum_daily_orders", 0)
            ),
            maximum_daily_loss=Decimal(
                str(value.get("maximum_daily_loss", "0"))
            ),
            maximum_gross_exposure=Decimal(
                str(value.get("maximum_gross_exposure", "0"))
            ),
            maximum_symbol_exposure=Decimal(
                str(value.get("maximum_symbol_exposure", "0"))
            ),
            require_market_open=(
                value.get("require_market_open") is True
            ),
            allocation_enabled=(
                value.get("allocation_enabled") is True
            ),
            multi_account_enabled=(
                value.get("multi_account_enabled") is True
            ),
            enabled=value.get("enabled") is True,
        )

    def validate(self) -> dict[str, Any]:
        checks = {
            "profile_name_present": bool(self.profile_name),
            "broker_mode_valid": self.broker_mode in VALID_MODES,
            "horizon_valid": self.horizon in VALID_HORIZONS,
            "allowed_symbols_present": bool(self.allowed_symbols),
            "symbols_unique": (
                len(self.allowed_symbols) == len(set(self.allowed_symbols))
            ),
            "order_types_valid": (
                bool(self.allowed_order_types)
                and set(self.allowed_order_types) <= VALID_ORDER_TYPES
            ),
            "time_in_force_valid": self.time_in_force in VALID_TIF,
            "maximum_order_notional_positive": (
                self.maximum_order_notional > 0
            ),
            "maximum_daily_orders_positive": (
                self.maximum_daily_orders > 0
            ),
            "maximum_daily_loss_positive": (
                self.maximum_daily_loss > 0
            ),
            "maximum_gross_exposure_positive": (
                self.maximum_gross_exposure > 0
            ),
            "maximum_symbol_exposure_positive": (
                self.maximum_symbol_exposure > 0
            ),
            "symbol_exposure_within_gross": (
                self.maximum_symbol_exposure
                <= self.maximum_gross_exposure
            ),
            "market_open_required": self.require_market_open is True,
            "allocation_feature_preserved": isinstance(
                self.allocation_enabled, bool
            ),
            "multi_account_feature_preserved": isinstance(
                self.multi_account_enabled, bool
            ),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }
