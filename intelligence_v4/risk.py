from __future__ import annotations
from decimal import Decimal
from .models import RiskBudgetDecision

class AdaptiveRiskEngineV3:
    def evaluate(
        self,
        *,
        symbol: str,
        base_notional: Decimal,
        volatility: Decimal,
        sector_exposure: Decimal,
        portfolio_exposure: Decimal,
        drawdown_ratio: Decimal,
        consecutive_losses: int,
        daily_loss_limit_reached: bool,
        strategy_risk_budget: Decimal,
    ) -> RiskBudgetDecision:
        blockers = []
        if base_notional <= 0:
            blockers.append("BASE_NOTIONAL_NOT_POSITIVE")
        if daily_loss_limit_reached:
            blockers.append("DAILY_LOSS_LIMIT_REACHED")
        if sector_exposure >= Decimal("0.35"):
            blockers.append("SECTOR_EXPOSURE_LIMIT")
        if portfolio_exposure >= Decimal("0.80"):
            blockers.append("PORTFOLIO_EXPOSURE_LIMIT")
        if strategy_risk_budget <= 0:
            blockers.append("STRATEGY_RISK_BUDGET_EMPTY")

        vol = max(Decimal("0.20"), min(Decimal("1"), Decimal("0.25") / max(volatility, Decimal("0.01"))))
        dd = max(Decimal("0"), Decimal("1") - min(Decimal("1"), drawdown_ratio))
        streak = max(Decimal("0.25"), Decimal("1") - Decimal(str(max(0, consecutive_losses))) * Decimal("0.15"))
        budget = min(Decimal("1"), strategy_risk_budget)
        multiplier = (vol * dd * streak * budget).quantize(Decimal("0.0001"))
        approved = (base_notional * multiplier).quantize(Decimal("0.01"))
        if approved <= 0:
            blockers.append("APPROVED_NOTIONAL_ZERO")
        if blockers:
            approved = Decimal("0")
        return RiskBudgetDecision(
            symbol=symbol,
            approved_notional=approved,
            risk_multiplier=multiplier,
            blocked=bool(blockers),
            blockers=tuple(blockers),
        )
