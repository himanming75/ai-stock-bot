from __future__ import annotations
from decimal import Decimal


D = Decimal


def risk_multiplier(
    *,
    confidence: Decimal,
    volatility: Decimal,
    drawdown_ratio: Decimal,
) -> Decimal:
    confidence_factor = max(D("0"), min(D("1"), confidence))
    volatility_factor = max(
        D("0.20"),
        D("1") - volatility,
    )
    drawdown_factor = max(
        D("0.10"),
        D("1") - drawdown_ratio,
    )
    return confidence_factor * volatility_factor * drawdown_factor


def dynamic_cash_floor(
    *,
    regime: str,
    portfolio_volatility: Decimal,
    drawdown_ratio: Decimal,
) -> Decimal:
    base = D("0.20")
    value = str(regime or "UNKNOWN").upper()

    if value in {"BEAR", "CRITICAL", "HIGH_VOLATILITY"}:
        base += D("0.30")
    elif value in {"SIDEWAYS", "VOLATILE"}:
        base += D("0.15")
    elif value in {"BULL", "BULL_TREND"}:
        base += D("0.00")
    else:
        base += D("0.20")

    base += min(portfolio_volatility, D("0.25"))
    base += min(drawdown_ratio, D("0.20"))

    return min(D("0.80"), base)


def loss_budget_state(
    *,
    daily_loss_ratio: Decimal,
    weekly_loss_ratio: Decimal,
    daily_limit: Decimal,
    weekly_limit: Decimal,
) -> dict:
    daily_breached = daily_loss_ratio >= daily_limit
    weekly_breached = weekly_loss_ratio >= weekly_limit

    if daily_breached or weekly_breached:
        return {
            "state": "RISK_HOLD",
            "new_entries_allowed": False,
            "daily_breached": daily_breached,
            "weekly_breached": weekly_breached,
        }

    return {
        "state": "NORMAL",
        "new_entries_allowed": True,
        "daily_breached": False,
        "weekly_breached": False,
    }
