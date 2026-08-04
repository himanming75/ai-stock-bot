from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("DAILY_LOSS_INPUT_INVALID")


def evaluate_daily_loss(
    equity: Any,
    last_equity: Any,
    daily_loss_limit_pct: Any,
) -> dict:
    current = _d(equity)
    previous = _d(last_equity)
    limit = _d(daily_loss_limit_pct)

    if current < 0:
        raise ValueError("EQUITY_NEGATIVE")
    if previous <= 0:
        raise ValueError("LAST_EQUITY_MUST_BE_POSITIVE")
    if not Decimal("0") < limit <= Decimal("0.05"):
        raise ValueError("DAILY_LOSS_LIMIT_OUT_OF_RANGE")

    daily_pnl = current - previous
    daily_return_pct = daily_pnl / previous
    daily_loss_pct = max(Decimal("0"), -daily_return_pct)
    limit_amount = previous * limit
    remaining_loss_buffer = max(Decimal("0"), limit_amount + daily_pnl)

    breached = daily_loss_pct >= limit
    warning_threshold = limit * Decimal("0.75")
    warning = not breached and daily_loss_pct >= warning_threshold

    if breached:
        state = "DAILY_LOSS_LIMIT_BREACHED"
        action = "PAUSE_REQUIRED"
    elif warning:
        state = "DAILY_LOSS_WARNING"
        action = "REDUCE_NEW_RISK"
    else:
        state = "DAILY_LOSS_WITHIN_LIMIT"
        action = "CONTINUE_MONITORING"

    return {
        "equity": float(current),
        "last_equity": float(previous),
        "daily_pnl": float(daily_pnl),
        "daily_return_pct": float(daily_return_pct),
        "daily_loss_pct": float(daily_loss_pct),
        "daily_loss_limit_pct": float(limit),
        "daily_loss_limit_amount": float(limit_amount),
        "remaining_loss_buffer": float(remaining_loss_buffer),
        "warning_threshold_pct": float(warning_threshold),
        "warning": warning,
        "breached": breached,
        "state": state,
        "required_action": action,
        "new_risk_allowed": not breached,
        "automatic_resume_allowed": False,
        "manual_resume_required": breached,
    }
