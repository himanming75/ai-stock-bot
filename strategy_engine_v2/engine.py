from __future__ import annotations

from strategy_engine_v2.decision import classify_decision
from strategy_engine_v2.explain import build_reasons
from strategy_engine_v2.models import SignalInput, StrategyDecision
from strategy_engine_v2.scoring import aggregate_signals


def evaluate_strategy(
    symbol: str,
    signals: list[SignalInput],
    *,
    buy_threshold: float = 35.0,
    sell_threshold: float = -35.0,
    watch_confidence: float = 45.0,
) -> StrategyDecision:
    metrics = aggregate_signals(signals)
    decision = classify_decision(
        metrics["composite_score"],
        metrics["confidence"],
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        watch_confidence=watch_confidence,
    )
    return StrategyDecision(
        symbol=symbol.upper().strip() or "UNKNOWN",
        decision=decision,
        confidence=metrics["confidence"],
        composite_score=metrics["composite_score"],
        bullish_count=metrics["bullish_count"],
        bearish_count=metrics["bearish_count"],
        neutral_count=metrics["neutral_count"],
        reasons=build_reasons(signals, decision),
    )
