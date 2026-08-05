from __future__ import annotations

from decimal import Decimal

from .models import FusionInput, SymbolIntelligence
from .quality import DataQualityGate
from .scoring import (
    clamp,
    risk_penalty,
    score_earnings,
    score_macro,
    score_momentum,
    score_news,
    score_options,
    score_technical,
)


class SymbolRanker:
    def __init__(self, quality_gate: DataQualityGate | None = None) -> None:
        self.quality_gate = quality_gate or DataQualityGate()

    def rank(self, item: FusionInput, regime: str) -> SymbolIntelligence:
        quality = self.quality_gate.evaluate(item)
        momentum = score_momentum(item)
        technical = score_technical(item)
        news = score_news(item)
        earnings = score_earnings(item)
        macro = score_macro(item)
        options = score_options(item)
        sector = clamp(Decimal("0.5") + item.sector_strength / Decimal("2"))
        liquidity = clamp(item.liquidity_score)
        penalty = risk_penalty(item)

        weights = {
            "momentum": Decimal("0.22"),
            "technical": Decimal("0.16"),
            "news": Decimal("0.12"),
            "earnings": Decimal("0.13"),
            "macro": Decimal("0.10"),
            "options": Decimal("0.11"),
            "sector": Decimal("0.09"),
            "liquidity": Decimal("0.07"),
        }
        if regime == "TRENDING_UP":
            weights["momentum"] += Decimal("0.08")
            weights["technical"] += Decimal("0.02")
            weights["macro"] -= Decimal("0.05")
            weights["earnings"] -= Decimal("0.05")
        elif regime == "HIGH_VOLATILITY":
            weights["liquidity"] += Decimal("0.08")
            weights["macro"] += Decimal("0.07")
            weights["momentum"] -= Decimal("0.08")
            weights["options"] -= Decimal("0.07")

        raw = (
            momentum * weights["momentum"]
            + technical * weights["technical"]
            + news * weights["news"]
            + earnings * weights["earnings"]
            + macro * weights["macro"]
            + options * weights["options"]
            + sector * weights["sector"]
            + liquidity * weights["liquidity"]
        )
        composite = clamp((raw - penalty * Decimal("0.35")) * quality.confidence)

        blockers = list(quality.blockers)
        if item.liquidity_score < Decimal("0.20"):
            blockers.append("LIQUIDITY_HARD_BLOCK")
        if item.event_risk >= Decimal("0.98"):
            blockers.append("EVENT_RISK_HARD_BLOCK")

        if blockers:
            bias = "BLOCKED"
        elif composite >= Decimal("0.68"):
            bias = "LONG"
        elif composite <= Decimal("0.32"):
            bias = "AVOID"
        else:
            bias = "NEUTRAL"

        return SymbolIntelligence(
            symbol=item.symbol,
            regime=regime,
            composite_score=composite.quantize(Decimal("0.0001")),
            momentum_score=momentum.quantize(Decimal("0.0001")),
            technical_score=technical.quantize(Decimal("0.0001")),
            news_score=news.quantize(Decimal("0.0001")),
            earnings_score=earnings.quantize(Decimal("0.0001")),
            macro_score=macro.quantize(Decimal("0.0001")),
            options_score=options.quantize(Decimal("0.0001")),
            sector_score=sector.quantize(Decimal("0.0001")),
            liquidity_score=liquidity.quantize(Decimal("0.0001")),
            risk_penalty=penalty.quantize(Decimal("0.0001")),
            confidence=quality.confidence.quantize(Decimal("0.0001")),
            trade_bias=bias,
            blockers=tuple(sorted(set(blockers))),
        )
