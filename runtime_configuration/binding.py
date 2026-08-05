from __future__ import annotations
from decimal import Decimal
from typing import Any

from configuration_profiles.models import TradingProfile

from .models import RuntimeConfiguration, RuntimeRiskLimits


def bind_profile_to_runtime(
    profile: TradingProfile,
) -> RuntimeConfiguration:
    validation = profile.validate()
    if not validation["valid"]:
        raise ValueError(
            "INVALID_TRADING_PROFILE:" + ",".join(validation["failed"])
        )

    return RuntimeConfiguration(
        profile_name=profile.profile_name,
        broker_mode=profile.broker_mode,
        horizon=profile.horizon,
        allowed_symbols=profile.allowed_symbols,
        allowed_order_types=profile.allowed_order_types,
        time_in_force=profile.time_in_force,
        require_market_open=profile.require_market_open,
        allocation_enabled=profile.allocation_enabled,
        multi_account_enabled=profile.multi_account_enabled,
        profile_enabled=profile.enabled,
        risk_limits=RuntimeRiskLimits(
            maximum_order_notional=profile.maximum_order_notional,
            maximum_daily_orders=profile.maximum_daily_orders,
            maximum_daily_loss=profile.maximum_daily_loss,
            maximum_gross_exposure=profile.maximum_gross_exposure,
            maximum_symbol_exposure=profile.maximum_symbol_exposure,
        ),
        broker_network_enabled=False,
        broker_write_enabled=False,
        automatic_order_submission_enabled=False,
    )


def build_strategy_binding(
    runtime: RuntimeConfiguration,
) -> dict[str, Any]:
    return {
        "strategy_horizon": runtime.horizon,
        "allowed_symbols": list(runtime.allowed_symbols),
        "allocation_enabled": runtime.allocation_enabled,
        "multi_account_enabled": runtime.multi_account_enabled,
        "strategy_execution_enabled": False,
    }


def build_risk_binding(
    runtime: RuntimeConfiguration,
) -> dict[str, Any]:
    return {
        **runtime.risk_limits.as_json(),
        "risk_enforcement_enabled": True,
        "broker_submission_enabled": False,
    }


def build_order_router_binding(
    runtime: RuntimeConfiguration,
) -> dict[str, Any]:
    return {
        "broker_mode": runtime.broker_mode,
        "allowed_order_types": list(runtime.allowed_order_types),
        "time_in_force": runtime.time_in_force,
        "require_market_open": runtime.require_market_open,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
    }
