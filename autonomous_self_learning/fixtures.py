from __future__ import annotations
from decimal import Decimal

from .models import TradeOutcome


D = Decimal


TRADES = [
    TradeOutcome(
        "MOMENTUM", "NVDA", "BUY", D("0.028"), 55,
        "BULL_TREND", D("0.90"), "Trend continuation",
    ),
    TradeOutcome(
        "MOMENTUM", "MSFT", "BUY", D("0.018"), 80,
        "BULL_TREND", D("0.84"), "Trend continuation",
    ),
    TradeOutcome(
        "MOMENTUM", "AAPL", "BUY", D("-0.009"), 45,
        "BULL_TREND", D("0.77"), "False breakout",
    ),
    TradeOutcome(
        "MOMENTUM", "META", "BUY", D("0.021"), 70,
        "BULL_TREND", D("0.86"), "Volume confirmation",
    ),
    TradeOutcome(
        "MOMENTUM", "AMD", "BUY", D("0.013"), 60,
        "BULL_TREND", D("0.80"), "Momentum continuation",
    ),
    TradeOutcome(
        "MOMENTUM", "GOOGL", "BUY", D("-0.006"), 50,
        "SIDEWAYS", D("0.68"), "Regime mismatch",
    ),
    TradeOutcome(
        "BREAKOUT", "TSLA", "BUY", D("0.035"), 40,
        "BULL_TREND", D("0.89"), "Range breakout",
    ),
    TradeOutcome(
        "BREAKOUT", "AMZN", "BUY", D("0.024"), 65,
        "BULL_TREND", D("0.82"), "Breakout retest",
    ),
    TradeOutcome(
        "BREAKOUT", "NFLX", "BUY", D("0.019"), 55,
        "BULL_TREND", D("0.79"), "Resistance break",
    ),
    TradeOutcome(
        "BREAKOUT", "COIN", "BUY", D("-0.008"), 35,
        "VOLATILE", D("0.71"), "Failed breakout",
    ),
    TradeOutcome(
        "BREAKOUT", "PLTR", "BUY", D("0.027"), 50,
        "BULL_TREND", D("0.87"), "Strong continuation",
    ),
    TradeOutcome(
        "BREAKOUT", "AVGO", "BUY", D("0.016"), 75,
        "BULL_TREND", D("0.81"), "Breakout continuation",
    ),
    TradeOutcome(
        "MEAN_REVERSION", "XLE", "SELL", D("-0.034"), 90,
        "BULL_TREND", D("0.55"), "Regime mismatch",
    ),
    TradeOutcome(
        "MEAN_REVERSION", "IWM", "BUY", D("0.006"), 120,
        "SIDEWAYS", D("0.62"), "Mean reversion",
    ),
    TradeOutcome(
        "MEAN_REVERSION", "QQQ", "SELL", D("-0.027"), 110,
        "BULL_TREND", D("0.58"), "Trend persisted",
    ),
    TradeOutcome(
        "MEAN_REVERSION", "SPY", "SELL", D("-0.018"), 100,
        "BULL_TREND", D("0.52"), "Trend persisted",
    ),
]

# Add deterministic evidence so healthy strategies exceed the evidence threshold.
for i in range(20):
    TRADES.append(
        TradeOutcome(
            "MOMENTUM",
            f"MOM{i}",
            "BUY",
            D("0.010") if i % 4 else D("-0.004"),
            45 + i,
            "BULL_TREND",
            D("0.78"),
            "Historical momentum fixture",
        )
    )
    TRADES.append(
        TradeOutcome(
            "BREAKOUT",
            f"BRK{i}",
            "BUY",
            D("0.014") if i % 5 else D("-0.003"),
            35 + i,
            "BULL_TREND",
            D("0.81"),
            "Historical breakout fixture",
        )
    )
