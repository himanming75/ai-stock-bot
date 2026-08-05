from __future__ import annotations

from decimal import Decimal

from .models import D, HUNDRED, ZERO, ratio, text


def bounded(value: Decimal, low=ZERO, high=HUNDRED) -> Decimal:
    return min(high, max(low, value))


def severity(score: Decimal, warning: Decimal, critical: Decimal) -> str:
    if score >= critical:
        return "CRITICAL"
    if score >= warning:
        return "WARNING"
    return "NORMAL"


def position_risk_scores(
    positions: list[dict],
    max_single_position_percent: Decimal,
) -> list[dict]:
    records = []
    for position in positions:
        weight = abs(D(position.get("portfolio_weight_percent")))
        unrealized_loss_percent = max(
            ZERO,
            -D(position.get("unrealized_pl_percent")),
        )
        concentration_component = bounded(
            ratio(weight, max_single_position_percent) * Decimal("60")
        )
        loss_component = bounded(
            ratio(unrealized_loss_percent, Decimal("10")) * Decimal("40")
        )
        score = bounded(concentration_component + loss_component)
        records.append(
            {
                "symbol": position.get("symbol"),
                "portfolio_weight_percent": text(weight),
                "unrealized_pl_percent": position.get(
                    "unrealized_pl_percent", "0"
                ),
                "concentration_component": text(concentration_component),
                "loss_component": text(loss_component),
                "risk_score": text(score),
            }
        )
    return sorted(
        records,
        key=lambda item: D(item["risk_score"]),
        reverse=True,
    )
