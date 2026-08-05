from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("CONCENTRATION_INPUT_INVALID")


def symbol_market_value(
    positions: list[dict[str, Any]],
    symbol: str,
) -> Decimal:
    target = symbol.upper()
    total = Decimal("0")
    for position in positions:
        if str(position.get("symbol", "")).upper() != target:
            continue
        total += abs(_d(position.get("market_value", 0)))
    return total


def evaluate_symbol_concentration(
    equity: Any,
    positions: list[dict[str, Any]],
    symbol: str,
    proposed_order_notional: Any,
    maximum_symbol_exposure_pct: Any,
) -> dict:
    account_equity = _d(equity)
    proposed_notional = _d(proposed_order_notional)
    limit_pct = _d(maximum_symbol_exposure_pct)
    normalized_symbol = str(symbol).strip().upper()

    if account_equity <= 0:
        raise ValueError("EQUITY_MUST_BE_POSITIVE")
    if not normalized_symbol:
        raise ValueError("SYMBOL_REQUIRED")
    if proposed_notional < 0:
        raise ValueError("PROPOSED_ORDER_NOTIONAL_NEGATIVE")
    if not Decimal("0") < limit_pct <= Decimal("0.25"):
        raise ValueError("MAXIMUM_SYMBOL_EXPOSURE_PCT_OUT_OF_RANGE")

    current_value = symbol_market_value(positions, normalized_symbol)
    projected_value = current_value + proposed_notional

    current_pct = current_value / account_equity
    projected_pct = projected_value / account_equity
    maximum_value = account_equity * limit_pct
    remaining_capacity = max(Decimal("0"), maximum_value - current_value)
    excess_amount = max(Decimal("0"), projected_value - maximum_value)
    allowed_order_notional = min(proposed_notional, remaining_capacity)

    breached = projected_value > maximum_value
    warning_threshold_pct = limit_pct * Decimal("0.80")
    warning = not breached and projected_pct >= warning_threshold_pct

    if breached:
        state = "SYMBOL_CONCENTRATION_LIMIT_BREACHED"
        action = "BLOCK_NEW_SYMBOL_RISK"
    elif warning:
        state = "SYMBOL_CONCENTRATION_LIMIT_WARNING"
        action = "REDUCE_SYMBOL_RISK"
    else:
        state = "SYMBOL_CONCENTRATION_WITHIN_LIMIT"
        action = "CONTINUE_MONITORING"

    return {
        "symbol": normalized_symbol,
        "equity": float(account_equity),
        "current_symbol_value": float(current_value),
        "proposed_order_notional": float(proposed_notional),
        "projected_symbol_value": float(projected_value),
        "current_symbol_exposure_pct": float(current_pct),
        "projected_symbol_exposure_pct": float(projected_pct),
        "maximum_symbol_exposure_pct": float(limit_pct),
        "maximum_symbol_value": float(maximum_value),
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
