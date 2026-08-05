from __future__ import annotations
from typing import Any

from .models import RuntimeConfiguration


def build_environment_preview(
    runtime: RuntimeConfiguration,
) -> dict[str, Any]:
    prefix = "PAPER" if runtime.broker_mode == "paper" else "LIVE"
    return {
        f"{prefix}_PROFILE_NAME": runtime.profile_name,
        f"{prefix}_TRADING_HORIZON": runtime.horizon,
        f"{prefix}_ALLOWED_SYMBOLS": ",".join(runtime.allowed_symbols),
        f"{prefix}_ALLOWED_ORDER_TYPES": ",".join(
            runtime.allowed_order_types
        ),
        f"{prefix}_TIME_IN_FORCE": runtime.time_in_force,
        f"{prefix}_MAX_ORDER_NOTIONAL": str(
            runtime.risk_limits.maximum_order_notional
        ),
        f"{prefix}_MAX_DAILY_ORDERS": str(
            runtime.risk_limits.maximum_daily_orders
        ),
        f"{prefix}_MAX_DAILY_LOSS": str(
            runtime.risk_limits.maximum_daily_loss
        ),
        f"{prefix}_MAX_GROSS_EXPOSURE": str(
            runtime.risk_limits.maximum_gross_exposure
        ),
        f"{prefix}_MAX_SYMBOL_EXPOSURE": str(
            runtime.risk_limits.maximum_symbol_exposure
        ),
        f"{prefix}_ALLOCATION_ENABLED": str(
            runtime.allocation_enabled
        ).lower(),
        f"{prefix}_MULTI_ACCOUNT_ENABLED": str(
            runtime.multi_account_enabled
        ).lower(),
        f"{prefix}_BROKER_NETWORK_ENABLED": "false",
        f"{prefix}_BROKER_WRITE_ENABLED": "false",
        f"{prefix}_AUTOMATIC_ORDER_SUBMISSION_ENABLED": "false",
    }
