from __future__ import annotations
from typing import Any

def daily_loss_guard(
    current_daily_loss_pct: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    warning = float(policy.get("daily_loss_warning_pct", 2.0))
    stop = float(policy.get("daily_loss_stop_pct", 5.0))
    absolute_loss = abs(min(0.0, current_daily_loss_pct))
    if absolute_loss >= stop:
        state = "STOP_REQUIRED"
    elif absolute_loss >= warning:
        state = "WARNING"
    else:
        state = "NORMAL"
    return {
        "state": state,
        "current_daily_loss_pct": round(current_daily_loss_pct, 4),
        "warning_threshold_pct": warning,
        "stop_threshold_pct": stop,
        "order_submission_enabled": False,
        "automatic_stop_execution_enabled": False,
    }

def concentration_guard(
    allocations: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    limit = float(policy.get("maximum_single_allocation_pct", 40.0))
    largest = max(
        (float(item.get("weight_pct", 0.0)) for item in allocations),
        default=0.0,
    )
    return {
        "passed": largest <= limit,
        "largest_allocation_pct": round(largest, 4),
        "maximum_single_allocation_pct": limit,
    }

def volatility_guard(
    annualized_volatility_pct: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    limit = float(policy.get("maximum_annualized_volatility_pct", 60.0))
    return {
        "passed": annualized_volatility_pct <= limit,
        "annualized_volatility_pct": round(
            annualized_volatility_pct, 4
        ),
        "maximum_annualized_volatility_pct": limit,
    }
