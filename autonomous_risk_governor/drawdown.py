from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("DRAWDOWN_INPUT_INVALID")


def evaluate_drawdown(
    equity: Any,
    peak_equity: Any,
    maximum_drawdown_pct: Any,
) -> dict:
    current = _d(equity)
    peak = _d(peak_equity)
    limit = _d(maximum_drawdown_pct)

    if current < 0:
        raise ValueError("EQUITY_NEGATIVE")
    if peak <= 0:
        raise ValueError("PEAK_EQUITY_MUST_BE_POSITIVE")
    if not Decimal("0") < limit <= Decimal("0.20"):
        raise ValueError("MAXIMUM_DRAWDOWN_OUT_OF_RANGE")

    updated_peak = max(peak, current)
    drawdown_amount = updated_peak - current
    drawdown_pct = drawdown_amount / updated_peak
    remaining_buffer = max(Decimal("0"), (updated_peak * limit) - drawdown_amount)

    breached = drawdown_pct >= limit
    warning_threshold = limit * Decimal("0.75")
    warning = not breached and drawdown_pct >= warning_threshold

    if breached:
        state = "MAX_DRAWDOWN_BREACHED"
        action = "PAUSE_REQUIRED"
    elif warning:
        state = "MAX_DRAWDOWN_WARNING"
        action = "REDUCE_NEW_RISK"
    else:
        state = "MAX_DRAWDOWN_WITHIN_LIMIT"
        action = "CONTINUE_MONITORING"

    return {
        "equity": float(current),
        "previous_peak_equity": float(peak),
        "updated_peak_equity": float(updated_peak),
        "new_peak_recorded": updated_peak > peak,
        "drawdown_amount": float(drawdown_amount),
        "drawdown_pct": float(drawdown_pct),
        "maximum_drawdown_pct": float(limit),
        "maximum_drawdown_amount": float(updated_peak * limit),
        "remaining_drawdown_buffer": float(remaining_buffer),
        "warning_threshold_pct": float(warning_threshold),
        "warning": warning,
        "breached": breached,
        "state": state,
        "required_action": action,
        "new_risk_allowed": not breached,
        "automatic_resume_allowed": False,
        "manual_resume_required": breached,
    }
