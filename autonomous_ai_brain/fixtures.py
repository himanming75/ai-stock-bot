from __future__ import annotations
from decimal import Decimal
from .models import StrategyCandidate


D = Decimal


CANDIDATES = [
    StrategyCandidate(
        strategy_id="MOMENTUM",
        signal="BUY",
        confidence=D("0.86"),
        expected_return=D("0.72"),
        drawdown_risk=D("0.28"),
        regime_fit=D("0.91"),
        stability=D("0.82"),
        evidence_count=80,
        explanation="Strong trend and volume continuation",
    ),
    StrategyCandidate(
        strategy_id="BREAKOUT",
        signal="BUY",
        confidence=D("0.73"),
        expected_return=D("0.66"),
        drawdown_risk=D("0.42"),
        regime_fit=D("0.76"),
        stability=D("0.69"),
        evidence_count=65,
        explanation="Price near validated breakout level",
    ),
    StrategyCandidate(
        strategy_id="MEAN_REVERSION",
        signal="SELL",
        confidence=D("0.61"),
        expected_return=D("0.48"),
        drawdown_risk=D("0.62"),
        regime_fit=D("0.30"),
        stability=D("0.40"),
        evidence_count=55,
        explanation="Overextension detected but regime mismatch",
    ),
    StrategyCandidate(
        strategy_id="SCALPING",
        signal="BUY",
        confidence=D("0.70"),
        expected_return=D("0.58"),
        drawdown_risk=D("0.50"),
        regime_fit=D("0.63"),
        stability=D("0.60"),
        evidence_count=8,
        explanation="Insufficient evidence sample",
    ),
]
