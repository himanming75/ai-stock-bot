from __future__ import annotations

from dataclasses import dataclass

from runtime_engine import Event, EventBus

from .dedup import DuplicateSignalGuard
from .filters import ConfidenceFilter, CooldownFilter, RiskPreFilter
from .models import MarketSnapshot, StrategySignal
from .strategy import Strategy


@dataclass
class SignalEngineStats:
    evaluated: int = 0
    accepted: int = 0
    rejected_confidence: int = 0
    rejected_cooldown: int = 0
    rejected_duplicate: int = 0
    rejected_risk: int = 0


class SignalEngine:
    """Evaluate strategies and publish accepted signals to the runtime EventBus."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        strategies: list[Strategy],
        confidence_filter: ConfidenceFilter,
        cooldown_filter: CooldownFilter,
        duplicate_guard: DuplicateSignalGuard,
        risk_filter: RiskPreFilter,
    ) -> None:
        if not strategies:
            raise ValueError("at least one strategy is required")
        self.event_bus = event_bus
        self.strategies = list(strategies)
        self.confidence_filter = confidence_filter
        self.cooldown_filter = cooldown_filter
        self.duplicate_guard = duplicate_guard
        self.risk_filter = risk_filter
        self.stats = SignalEngineStats()

    def evaluate(self, snapshot: MarketSnapshot) -> list[StrategySignal]:
        snapshot.validate()
        accepted: list[StrategySignal] = []

        for strategy in self.strategies:
            self.stats.evaluated += 1
            signal = strategy.evaluate(snapshot)
            signal.validate()

            confidence = self.confidence_filter.check(signal)
            if not confidence.accepted:
                self.stats.rejected_confidence += 1
                continue

            if self.duplicate_guard.is_duplicate(signal):
                self.stats.rejected_duplicate += 1
                continue

            cooldown = self.cooldown_filter.check(signal)
            if not cooldown.accepted:
                self.stats.rejected_cooldown += 1
                continue

            risk = self.risk_filter.check(signal, snapshot)
            if not risk.accepted:
                self.stats.rejected_risk += 1
                continue

            self.event_bus.publish(Event(
                topic="strategy.signal",
                payload={"signal": signal},
                created_at=signal.generated_at,
            ))
            accepted.append(signal)
            self.stats.accepted += 1

        return accepted
