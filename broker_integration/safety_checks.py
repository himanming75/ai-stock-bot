from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .execution_config import ExecutionConfig
from .execution_models import CanonicalOrderRequest
from .idempotency import count_for_date


MARKET_PRICE_SAFETY_BUFFER = Decimal("1.03")


def find_position_quantity(
    positions: list[dict[str, Any]],
    symbol: str,
) -> Decimal:
    normalized = symbol.strip().upper()
    total = Decimal("0")
    for item in positions:
        if str(item.get("symbol", "")).strip().upper() == normalized:
            total += Decimal(str(item.get("qty", "0")))
    return total


def estimated_notional(
    order: CanonicalOrderRequest,
    latest_trade_price: Decimal | None,
) -> tuple[Decimal, str]:
    if order.notional is not None:
        return order.notional, "ORDER_NOTIONAL"

    if order.qty is None:
        raise ValueError("ORDER_SIZE_MISSING")

    if order.order_type == "limit":
        if order.limit_price is None:
            raise ValueError("LIMIT_PRICE_REQUIRED")
        return order.qty * order.limit_price, "QTY_X_LIMIT_PRICE"

    if latest_trade_price is None or latest_trade_price <= 0:
        raise ValueError("LATEST_TRADE_PRICE_REQUIRED_FOR_MARKET_QTY")

    return (
        order.qty * latest_trade_price * MARKET_PRICE_SAFETY_BUFFER,
        "QTY_X_LATEST_TRADE_X_1.03",
    )


def evaluate_pre_submit(
    config: ExecutionConfig,
    order: CanonicalOrderRequest,
    account: dict[str, Any],
    asset: dict[str, Any],
    clock: dict[str, Any],
    kill_switch: dict[str, Any],
    risk_permission: bool,
    latest_trade_price: Decimal | None,
    positions: list[dict[str, Any]],
    registry_path: Path,
) -> dict[str, Any]:
    order.validate()
    notional, source = estimated_notional(order, latest_trade_price)
    buying_power = Decimal(str(account.get("buying_power", "0")))
    held_qty = find_position_quantity(positions, order.symbol)
    today = datetime.now(timezone.utc).date().isoformat()
    daily_count = count_for_date(registry_path, today)

    checks = {
        "paper_endpoint_enforced": config.paper_endpoint_enforced,
        "credentials_present": config.credentials_present,
        "network_enabled": config.network_enabled,
        "write_enabled": config.write_enabled,
        "confirmation_valid": config.explicit_confirmation_valid,
        "kill_switch_inactive": (
            kill_switch.get("kill_switch_active") is False
        ),
        "risk_permission": risk_permission is True,
        "account_active": account.get("status") == "ACTIVE",
        "account_not_blocked": (
            account.get("account_blocked") is False
            and account.get("trading_blocked") is False
        ),
        "market_open": clock.get("is_open") is True,
        "asset_active": asset.get("status") == "active",
        "asset_tradable": asset.get("tradable") is True,
        "symbol_allowed": (
            order.symbol.strip().upper() in config.allowed_symbols
        ),
        "notional_within_limit": (
            notional <= config.maximum_order_notional
        ),
        "buying_power_sufficient": (
            order.side == "sell" or buying_power >= notional
        ),
        "sell_quantity_available": (
            order.side != "sell"
            or (
                order.qty is not None
                and held_qty >= order.qty
            )
        ),
        "daily_order_limit": daily_count < config.maximum_daily_orders,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "approved": not failed,
        "checks": checks,
        "failed": failed,
        "estimated_notional": str(notional),
        "estimated_notional_source": source,
        "latest_trade_price": (
            str(latest_trade_price)
            if latest_trade_price is not None
            else None
        ),
        "market_price_safety_buffer": str(MARKET_PRICE_SAFETY_BUFFER),
        "held_quantity": str(held_qty),
        "daily_order_count_before": daily_count,
        "maximum_daily_orders": config.maximum_daily_orders,
        "maximum_order_notional": str(config.maximum_order_notional),
        "user_reference_price_used": False,
    }
