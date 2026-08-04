from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("EXPOSURE_INPUT_INVALID")


def calculate_current_exposure(positions: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for position in positions:
        market_value = _d(position.get("market_value", 0))
        total += abs(market_value)
    return total


def evaluate_total_exposure(
    equity: Any,
    positions: list[dict[str, Any]],
    proposed_order_notional: Any,
    maximum_total_exposure_pct: Any,
) -> dict:
    account_equity = _d(equity)
    proposed_notional = _d(proposed_order_notional)
    limit_pct = _d(maximum_total_exposure_pct)

    if account_equity <= 0:
        raise ValueError("EQUITY_MUST_BE_POSITIVE")
    if proposed_notional < 0:
        raise ValueError("PROPOSED_ORDER_NOTIONAL_NEGATIVE")
    if not Decimal("0") < limit_pct <= Decimal("1.00"):
        raise ValueError("MAXIMUM_TOTAL_EXPOSURE_PCT_OUT_OF_RANGE")

    current_exposure = calculate_current_exposure(positions)
    projected_exposure = current_exposure + proposed_notional

    current_exposure_pct = current_exposure / account_equity
    projected_exposure_pct = projected_exposure / account_equity
    maximum_exposure_value = account_equity * limit_pct
    remaining_capacity = max(Decimal("0"), maximum_exposure_value - current_exposure)
    excess_amount = max(Decimal("0"), projected_exposure - maximum_exposure_value)
    allowed_order_notional = min(proposed_notional, remaining_capacity)

    breached = projected_exposure > maximum_exposure_value
    warning_threshold_pct = limit_pct * Decimal("0.80")
    warning = (
        not breached
        and projected_exposure_pct >= warning_threshold_pct
    )

    if breached:
        state = "TOTAL_EXPOSURE_LIMIT_BREACHED"
        action = "BLOCK_NEW_PORTFOLIO_RISK"
    elif warning:
        state = "TOTAL_EXPOSURE_LIMIT_WARNING"
        action = "REDUCE_NEW_PORTFOLIO_RISK"
    else:
        state = "TOTAL_EXPOSURE_WITHIN_LIMIT"
        action = "CONTINUE_MONITORING"

    return {
        "equity": float(account_equity),
        "position_count": len(positions),
        "current_exposure": float(current_exposure),
        "proposed_order_notional": float(proposed_notional),
        "projected_exposure": float(projected_exposure),
        "current_exposure_pct": float(current_exposure_pct),
        "projected_exposure_pct": float(projected_exposure_pct),
        "maximum_total_exposure_pct": float(limit_pct),
        "maximum_exposure_value": float(maximum_exposure_value),
        "remaining_capacity": float(remaining_capacity),
        "allowed_order_notional": float(allowed_order_notional),
        "excess_amount": float(excess_amount),
        "warning_threshold_pct": float(warning_threshold_pct),
        "warning": warning,
        "breached": breached,
        "state": state,
        "required_action": action,
        "new_risk_allowed": not breached,
    }
