from __future__ import annotations
from decimal import Decimal

from .models import AIVote, StrategyPerformance


D = Decimal


VOTES = [
    AIVote(
        voter_id="TREND_AI",
        action="BUY",
        confidence=D("0.92"),
        weight=D("0.25"),
        reason="Trend slope and moving averages aligned",
    ),
    AIVote(
        voter_id="VOLUME_AI",
        action="BUY",
        confidence=D("0.84"),
        weight=D("0.15"),
        reason="Relative volume expansion confirmed",
    ),
    AIVote(
        voter_id="RISK_AI",
        action="WAIT",
        confidence=D("0.76"),
        weight=D("0.25"),
        reason="Risk acceptable but not ideal",
    ),
    AIVote(
        voter_id="REGIME_AI",
        action="BUY",
        confidence=D("0.88"),
        weight=D("0.15"),
        reason="Bull trend regime detected",
    ),
    AIVote(
        voter_id="PORTFOLIO_AI",
        action="BUY",
        confidence=D("0.80"),
        weight=D("0.10"),
        reason="Portfolio concentration remains acceptable",
    ),
    AIVote(
        voter_id="EXECUTION_AI",
        action="WAIT",
        confidence=D("0.65"),
        weight=D("0.10"),
        reason="Spread is acceptable but timing can improve",
    ),
]

VETO_VOTES = [
    *VOTES,
    AIVote(
        voter_id="SAFETY_AI",
        action="WAIT",
        confidence=D("1.00"),
        weight=D("0.00"),
        reason="Critical safety condition",
        veto=True,
    ),
]

CHAMPION = StrategyPerformance(
    strategy_id="MOMENTUM",
    trade_count=300,
    win_rate=D("0.61"),
    expected_return=D("0.58"),
    sharpe_ratio=D("0.62"),
    max_drawdown=D("0.24"),
    stability=D("0.72"),
)

CHALLENGER = StrategyPerformance(
    strategy_id="BREAKOUT",
    trade_count=320,
    win_rate=D("0.68"),
    expected_return=D("0.70"),
    sharpe_ratio=D("0.76"),
    max_drawdown=D("0.22"),
    stability=D("0.79"),
)

WEAK_CHALLENGER = StrategyPerformance(
    strategy_id="SCALPING",
    trade_count=30,
    win_rate=D("0.71"),
    expected_return=D("0.69"),
    sharpe_ratio=D("0.74"),
    max_drawdown=D("0.42"),
    stability=D("0.40"),
)
