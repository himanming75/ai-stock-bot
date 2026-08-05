from __future__ import annotations
from decimal import Decimal


def authorize_micro_order(
    *,
    estimated_notional: Decimal,
    maximum_order_notional: Decimal,
    daily_order_count: int,
    maximum_daily_orders: int,
    daily_realized_loss: Decimal,
    maximum_daily_loss: Decimal,
    symbol: str,
    allowed_symbols: tuple[str, ...],
) -> dict:
    checks = {
        "estimated_notional_positive": estimated_notional > 0,
        "order_notional_within_limit": (
            estimated_notional <= maximum_order_notional
        ),
        "daily_order_limit": daily_order_count < maximum_daily_orders,
        "daily_loss_limit": (
            abs(min(daily_realized_loss, Decimal("0")))
            < maximum_daily_loss
        ),
        "symbol_allowed": symbol.upper() in allowed_symbols,
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "approved": all(checks.values()),
    }
