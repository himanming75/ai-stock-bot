from __future__ import annotations
from decimal import Decimal

def build_candidates(route: str, score: Decimal, confidence: Decimal):
    from intelligence_v4.models import StrategyCandidate
    profiles = {
        "MOMENTUM_BREAKOUT_ENSEMBLE": ("momentum_v4", "breakout_v4", "trend_follow_v4"),
        "MEAN_REVERSION_ENSEMBLE": ("mean_reversion_v4", "range_v4", "reversal_v4"),
        "EVENT_CATALYST_ENSEMBLE": ("event_catalyst_v4", "momentum_v4", "breakout_v4"),
        "OPTIONS_CONFIRMATION_ENSEMBLE": ("options_flow_v4", "momentum_v4", "swing_v4"),
        "BALANCED_MULTI_FACTOR_ENSEMBLE": ("momentum_v4", "mean_reversion_v4", "swing_v4"),
    }
    ids = profiles.get(route, profiles["BALANCED_MULTI_FACTOR_ENSEMBLE"])
    values = []
    for idx, strategy_id in enumerate(ids):
        decay = Decimal(str(idx)) * Decimal("0.05")
        values.append(StrategyCandidate(
            strategy_id,
            max(Decimal("0.20"), score - decay),
            max(Decimal("0.30"), confidence - decay),
            max(Decimal("0.25"), score - decay / 2),
            max(Decimal("0.25"), confidence - decay / 2),
            Decimal("0.10") + decay / 2,
            Decimal("0.08") + decay / 2,
        ))
    return values

def normalize_regime(regime: str) -> str:
    return {
        "TRENDING_UP": "TRENDING",
        "TRENDING_DOWN": "TRENDING",
        "LOW_VOLATILITY_RANGE": "RANGING",
        "MIXED": "RANGING",
        "HIGH_VOLATILITY": "HIGH_VOLATILITY",
    }.get(regime, "RANGING")
