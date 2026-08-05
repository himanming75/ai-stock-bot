from __future__ import annotations

from decimal import Decimal


def choose_strategy_route(item: dict, regime: str) -> str:
    momentum = Decimal(str(item.get("momentum_score", "0")))
    technical = Decimal(str(item.get("technical_score", "0")))
    news = Decimal(str(item.get("news_score", "0")))
    earnings = Decimal(str(item.get("earnings_score", "0")))
    options = Decimal(str(item.get("options_score", "0")))

    if regime == "TRENDING_UP" and momentum >= Decimal("0.65"):
        return "MOMENTUM_BREAKOUT_ENSEMBLE"
    if regime == "LOW_VOLATILITY_RANGE" and technical >= Decimal("0.58"):
        return "MEAN_REVERSION_ENSEMBLE"
    if news >= Decimal("0.68") or earnings >= Decimal("0.68"):
        return "EVENT_CATALYST_ENSEMBLE"
    if options >= Decimal("0.70"):
        return "OPTIONS_CONFIRMATION_ENSEMBLE"
    return "BALANCED_MULTI_FACTOR_ENSEMBLE"
