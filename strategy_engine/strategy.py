from __future__ import annotations

from typing import Protocol

from .models import MarketSnapshot, StrategySignal


class Strategy(Protocol):
    name: str

    def evaluate(self, snapshot: MarketSnapshot) -> StrategySignal:
        """Evaluate one immutable market snapshot and return a signal."""
