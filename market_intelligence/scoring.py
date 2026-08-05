from __future__ import annotations

from decimal import Decimal

from .models import FusionInput


ZERO = Decimal("0")
ONE = Decimal("1")


def clamp(value: Decimal, low: Decimal = ZERO, high: Decimal = ONE) -> Decimal:
    return max(low, min(high, value))


def signed_to_unit(value: Decimal, scale: Decimal = ONE) -> Decimal:
    if scale <= 0:
        return Decimal("0.5")
    return clamp(Decimal("0.5") + value / (Decimal("2") * scale))


def score_momentum(item: FusionInput) -> Decimal:
    one_day = signed_to_unit(item.price_return_1d, Decimal("0.08"))
    five_day = signed_to_unit(item.price_return_5d, Decimal("0.20"))
    volume = clamp(item.volume_ratio / Decimal("3"))
    relative = signed_to_unit(item.relative_strength, Decimal("1"))
    return clamp(
        one_day * Decimal("0.20")
        + five_day * Decimal("0.35")
        + volume * Decimal("0.15")
        + relative * Decimal("0.30")
    )


def score_technical(item: FusionInput) -> Decimal:
    breadth = signed_to_unit(item.breadth_score, Decimal("1"))
    volatility_quality = ONE - clamp(item.realized_volatility / Decimal("0.80"))
    return clamp(
        breadth * Decimal("0.45")
        + volatility_quality * Decimal("0.25")
        + score_momentum(item) * Decimal("0.30")
    )


def score_news(item: FusionInput) -> Decimal:
    sentiment = signed_to_unit(item.news_sentiment, Decimal("1"))
    importance = clamp(item.news_importance)
    return clamp(Decimal("0.5") + (sentiment - Decimal("0.5")) * importance * Decimal("1.6"))


def score_earnings(item: FusionInput) -> Decimal:
    surprise = signed_to_unit(item.earnings_surprise, Decimal("0.50"))
    revision = signed_to_unit(item.earnings_revision, Decimal("0.50"))
    return clamp(surprise * Decimal("0.60") + revision * Decimal("0.40"))


def score_macro(item: FusionInput) -> Decimal:
    risk = ONE - clamp(item.macro_risk)
    rates = ONE - clamp(item.rates_pressure)
    return clamp(risk * Decimal("0.65") + rates * Decimal("0.35"))


def score_options(item: FusionInput) -> Decimal:
    put_call_quality = ONE - clamp(abs(item.options_put_call - ONE) / Decimal("2"))
    iv_quality = ONE - clamp(item.options_iv_rank)
    flow = signed_to_unit(item.options_flow, Decimal("1"))
    return clamp(
        put_call_quality * Decimal("0.25")
        + iv_quality * Decimal("0.25")
        + flow * Decimal("0.50")
    )


def risk_penalty(item: FusionInput) -> Decimal:
    volatility = clamp(item.realized_volatility / Decimal("1.0"))
    spread = clamp(item.spread_bps / Decimal("100"))
    event = clamp(item.event_risk)
    illiquidity = ONE - clamp(item.liquidity_score)
    return clamp(
        volatility * Decimal("0.30")
        + spread * Decimal("0.20")
        + event * Decimal("0.30")
        + illiquidity * Decimal("0.20")
    )
