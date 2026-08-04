from __future__ import annotations
from typing import Any
from offline_ai_decision_engine.confidence import calculate as base_confidence
from offline_ai_decision_engine.regime import classify
from offline_ai_decision_engine.models import MarketInput

from .components import calculate as calculate_components
from .explainability import explain
from .models import Bar, SignalResult
from .patterns import detect
from .ranker import rank, score
from .risk import calculate as calculate_risk


PATTERN_BIAS = {
    "BULLISH_ENGULFING": 1.0,
    "HAMMER": 0.6,
    "BEARISH_ENGULFING": -1.0,
    "SHOOTING_STAR": -0.6,
    "DOJI": 0.0,
}


def _holding_days(signal_rank: str, risk_level: str) -> str:
    if signal_rank == "A" and risk_level == "LOW":
        return "3-7"
    if signal_rank in {"A", "B"}:
        return "2-5"
    if signal_rank == "C":
        return "1-3"
    return "0"


def analyze(payload: dict[str, Any]) -> SignalResult:
    symbol = str(payload["symbol"]).strip().upper()
    bars = [Bar.from_dict(item) for item in payload["bars"]]
    if len(bars) < 2:
        raise ValueError("AT_LEAST_TWO_BARS_REQUIRED")
    if any(bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close) for bar in bars):
        raise ValueError("INVALID_OHLC")

    market_trend = float(payload.get("market_trend", 0.0))
    news_score = float(payload.get("news_score", 0.0))
    components = calculate_components(bars, market_trend, news_score)
    patterns = detect(bars)
    pattern_bias = sum(PATTERN_BIAS.get(item, 0.0) for item in patterns)
    signal_score = score(components, pattern_bias)

    latest = bars[-1]
    base_input = MarketInput(
        symbol=symbol,
        close=latest.close,
        sma_fast=latest.close * (1.0 + components["trend"] / 30.0),
        sma_slow=latest.close,
        rsi=components["rsi"],
        atr_pct=components["atr_pct"],
        volume_ratio=components["volume_ratio"],
        market_trend=market_trend,
        news_score=news_score,
    )
    regime = classify(base_input)
    confidence_features = {
        "trend": components["trend"],
        "rsi_centered": components["momentum"],
        "market_trend": components["market_trend"],
        "news_score": components["news"],
    }
    confidence = base_confidence(signal_score, regime, confidence_features)

    action = (
        "BUY" if signal_score >= 0.20 and confidence >= 55
        else "SELL" if signal_score <= -0.20 and confidence >= 55
        else "HOLD"
    )
    signal_rank = rank(confidence, abs(signal_score))
    risk_score, risk_level = calculate_risk(components, action)

    review: list[str] = []
    if signal_rank == "D":
        review.append("Signal quality is too low for a future execution layer.")
    if action == "BUY" and components["rsi"] >= 70:
        review.append("BUY conflicts with overbought RSI.")
    if action == "SELL" and components["rsi"] <= 30:
        review.append("SELL conflicts with oversold RSI.")
    if risk_level == "HIGH":
        review.append("Risk score is high.")
    if not review:
        review.append("No major signal conflict detected.")
    review.append("This offline signal cannot submit an order.")

    return SignalResult(
        symbol=symbol,
        action=action,
        confidence=confidence,
        signal_rank=signal_rank,
        signal_score=signal_score,
        risk_score=risk_score,
        risk_level=risk_level,
        regime=regime,
        patterns=tuple(patterns),
        components=components,
        reasons=tuple(explain(action, components, patterns, regime)),
        self_review=tuple(review),
        expected_holding_days=_holding_days(signal_rank, risk_level),
    )
