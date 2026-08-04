from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("POSITION_LIMIT_INPUT_INVALID")


def evaluate_position_limit(
    equity: Any,
    current_position_value: Any,
    proposed_order_notional: Any,
    maximum_position_pct: Any,
) -> dict:
    account_equity = _d(equity)
    current_value = _d(current_position_value)
    proposed_value = _d(proposed_order_notional)
    limit_pct = _d(maximum_position_pct)

    if account_equity <= 0:
        raise ValueError("EQUITY_MUST_BE_POSITIVE")
    if current_value < 0:
        raise ValueError("CURRENT_POSITION_VALUE_NEGATIVE")
    if proposed_value < 0:
        raise ValueError("PROPOSED_ORDER_NOTIONAL_NEGATIVE")
    if not Decimal("0") < limit_pct <= Decimal("0.25"):
        raise ValueError("MAXIMUM_POSITION_PCT_OUT_OF_RANGE")

    maximum_position_value = account_equity * limit_pct
    projected_position_value = current_value + proposed_value
    current_position_pct = current_value / account_equity
    projected_position_pct = projected_position_value / account_equity
    remaining_capacity = max(Decimal("0"), maximum_position_value - current_value)
    excess_amount = max(Decimal("0"), projected_position_value - maximum_position_value)

    breached = projected_position_value > maximum_position_value
    warning_threshold_pct = limit_pct * Decimal("0.80")
    warning = (
        not breached
        and projected_position_pct >= warning_threshold_pct
    )

    if breached:
        state = "POSITION_LIMIT_BREACHED"
        action = "BLOCK_NEW_POSITION_RISK"
    elif warning:
        state = "POSITION_LIMIT_WARNING"
        action = "REDUCE_PROPOSED_POSITION"
    else:
        state = "POSITION_LIMIT_WITHIN_LIMIT"
        action = "CONTINUE_MONITORING"

    allowed_order_notional = min(proposed_value, remaining_capacity)

    return {
        "equity": float(account_equity),
        "current_position_value": float(current_value),
        "proposed_order_notional": float(proposed_value),
        "projected_position_value": float(projected_position_value),
        "current_position_pct": float(current_position_pct),
        "projected_position_pct": float(projected_position_pct),
        "maximum_position_pct": float(limit_pct),
        "maximum_position_value": float(maximum_position_value),
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
