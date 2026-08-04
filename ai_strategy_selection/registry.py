from __future__ import annotations


STRATEGIES = {
    "TREND_FOLLOWING": {
        "preferred_regimes": {"BULL_TREND", "BEAR_TREND"},
        "minimum_liquidity": 40.0,
        "maximum_volatility": 85.0,
    },
    "MOMENTUM": {
        "preferred_regimes": {"BULL_TREND", "BEAR_TREND"},
        "minimum_liquidity": 55.0,
        "maximum_volatility": 75.0,
    },
    "BREAKOUT": {
        "preferred_regimes": {"BULL_TREND", "RANGE"},
        "minimum_liquidity": 60.0,
        "maximum_volatility": 80.0,
    },
    "MEAN_REVERSION": {
        "preferred_regimes": {"RANGE"},
        "minimum_liquidity": 45.0,
        "maximum_volatility": 65.0,
    },
    "CASH_DEFENSIVE": {
        "preferred_regimes": {"HIGH_VOLATILITY"},
        "minimum_liquidity": 0.0,
        "maximum_volatility": 100.0,
    },
}
