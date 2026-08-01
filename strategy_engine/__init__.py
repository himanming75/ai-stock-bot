"""Strategy signal engine foundation for AI Stock Bot."""

from .models import (
    MarketSnapshot,
    SignalAction,
    StrategySignal,
)
from .strategy import Strategy
from .sample_strategy import MovingAverageCrossStrategy
from .filters import ConfidenceFilter, CooldownFilter, RiskPreFilter
from .dedup import DuplicateSignalGuard
from .engine import SignalEngine, SignalEngineStats

__all__ = [
    "MarketSnapshot",
    "SignalAction",
    "StrategySignal",
    "Strategy",
    "MovingAverageCrossStrategy",
    "ConfidenceFilter",
    "CooldownFilter",
    "RiskPreFilter",
    "DuplicateSignalGuard",
    "SignalEngine",
    "SignalEngineStats",
]
