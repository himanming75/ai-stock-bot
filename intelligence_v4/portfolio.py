from __future__ import annotations
from decimal import Decimal
from .models import PortfolioAllocation

class PortfolioIntelligenceV2:
    def allocate(
        self,
        *,
        symbol: str,
        portfolio_value: Decimal,
        current_weight: Decimal,
        desired_weight: Decimal,
        sector_weight_after: Decimal,
        correlated_exposure_after: Decimal,
        cash_reserve_minimum: Decimal = Decimal("0.10"),
        minimum_rebalance_delta: Decimal = Decimal("0.02"),
    ) -> PortfolioAllocation:
        blockers = []
        capped = min(desired_weight, Decimal("0.20"))
        if sector_weight_after > Decimal("0.35"):
            blockers.append("SECTOR_CONCENTRATION_LIMIT")
        if correlated_exposure_after > Decimal("0.45"):
            blockers.append("CORRELATED_EXPOSURE_LIMIT")
        if capped > Decimal("1") - cash_reserve_minimum:
            blockers.append("CASH_RESERVE_VIOLATION")
        delta = abs(capped - current_weight)
        rebalance = delta >= minimum_rebalance_delta and not blockers
        notional = (portfolio_value * capped).quantize(Decimal("0.01")) if not blockers else Decimal("0")
        return PortfolioAllocation(
            symbol=symbol,
            target_weight=capped.quantize(Decimal("0.0001")),
            target_notional=notional,
            rebalance_required=rebalance,
            blockers=tuple(blockers),
        )
