from __future__ import annotations
from decimal import Decimal
from typing import Any

from .models import DynamicRiskDecision


class DynamicRiskEngineV2:
    def evaluate(
        self,
        *,
        symbol: str,
        base_notional: Decimal,
        volatility: Decimal,
        portfolio_drawdown: Decimal,
        maximum_drawdown: Decimal,
        average_correlation: Decimal,
        daily_loss_limit_reached: bool,
    ) -> DynamicRiskDecision:
        blockers: list[str] = []
        if base_notional <= 0:
            blockers.append("BASE_NOTIONAL_NOT_POSITIVE")
        if daily_loss_limit_reached:
            blockers.append("DAILY_LOSS_LIMIT_REACHED")
        if maximum_drawdown <= 0:
            blockers.append("MAXIMUM_DRAWDOWN_NOT_POSITIVE")

        volatility_multiplier = max(
            Decimal("0.25"),
            min(Decimal("1"), Decimal("0.30") / max(
                volatility, Decimal("0.01")
            )),
        )
        drawdown_ratio = (
            portfolio_drawdown / maximum_drawdown
            if maximum_drawdown > 0
            else Decimal("1")
        )
        drawdown_multiplier = max(
            Decimal("0"),
            Decimal("1") - drawdown_ratio,
        )
        correlation_multiplier = max(
            Decimal("0.25"),
            Decimal("1") - max(Decimal("0"), average_correlation),
        )

        adjusted = (
            base_notional
            * volatility_multiplier
            * drawdown_multiplier
            * correlation_multiplier
        ).quantize(Decimal("0.01"))

        if adjusted <= 0:
            blockers.append("ADJUSTED_NOTIONAL_ZERO")
        blocked = bool(blockers)
        if blocked:
            adjusted = Decimal("0")

        return DynamicRiskDecision(
            symbol=symbol,
            base_notional=base_notional,
            adjusted_notional=adjusted,
            volatility_multiplier=volatility_multiplier.quantize(
                Decimal("0.0001")
            ),
            drawdown_multiplier=drawdown_multiplier.quantize(
                Decimal("0.0001")
            ),
            correlation_multiplier=correlation_multiplier.quantize(
                Decimal("0.0001")
            ),
            blocked=blocked,
            blockers=tuple(blockers),
        )
