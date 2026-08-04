from __future__ import annotations
from .registry import STRATEGIES


def _regime_bonus(strategy: str, regime: str) -> float:
    return 18.0 if regime in STRATEGIES[strategy]["preferred_regimes"] else -10.0


def score_all(payload: dict) -> dict[str, dict]:
    regime = str(payload["market_regime"]).upper()
    trend = float(payload["trend_strength"])
    momentum = float(payload["momentum_strength"])
    breakout = float(payload["breakout_strength"])
    mean_reversion = float(payload["mean_reversion_strength"])
    volatility = float(payload["volatility_score"])
    liquidity = float(payload["liquidity_score"])
    breadth = float(payload["breadth_score"])
    portfolio = float(payload.get("portfolio_score", 0.0))

    raw = {
        "TREND_FOLLOWING": (
            trend * 0.42 + breadth * 0.18 + liquidity * 0.10
            + portfolio * 0.10 + (100 - volatility) * 0.08
            + _regime_bonus("TREND_FOLLOWING", regime)
        ),
        "MOMENTUM": (
            momentum * 0.40 + trend * 0.18 + liquidity * 0.12
            + breadth * 0.12 + portfolio * 0.08
            + _regime_bonus("MOMENTUM", regime)
        ),
        "BREAKOUT": (
            breakout * 0.42 + liquidity * 0.16 + volatility * 0.08
            + breadth * 0.10 + portfolio * 0.08
            + _regime_bonus("BREAKOUT", regime)
        ),
        "MEAN_REVERSION": (
            mean_reversion * 0.46 + (100 - trend) * 0.12
            + (100 - volatility) * 0.12 + liquidity * 0.10
            + _regime_bonus("MEAN_REVERSION", regime)
        ),
        "CASH_DEFENSIVE": (
            volatility * 0.42 + (100 - breadth) * 0.18
            + (100 - liquidity) * 0.08 + (100 - portfolio) * 0.10
            + _regime_bonus("CASH_DEFENSIVE", regime)
        ),
    }

    output: dict[str, dict] = {}
    for strategy, value in raw.items():
        meta = STRATEGIES[strategy]
        eligible = (
            liquidity >= meta["minimum_liquidity"]
            and volatility <= meta["maximum_volatility"]
        )
        if strategy == "CASH_DEFENSIVE":
            eligible = True
        score = round(max(0.0, min(100.0, value)), 4)
        confidence = round(max(0.0, min(99.0, score * 0.92 + 5.0)), 2)
        output[strategy] = {
            "score": score,
            "confidence": confidence,
            "eligible": eligible,
        }
    return output
