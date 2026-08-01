from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from runtime_engine import Event, EventBus
from strategy_engine import MarketSnapshot, StrategySignal

from .dedup import DuplicateIntentGuard
from .expiry import IntentExpiryPolicy
from .factory import OrderIntentFactory
from .models import OrderIntent


@dataclass
class OrderIntentEngineStats:
    signals_received: int = 0
    intents_created: int = 0
    rejected_sizing: int = 0
    rejected_duplicate: int = 0
    rejected_expired: int = 0
    published: int = 0


class OrderIntentEngine:
    """Convert approved strategy signals into broker-independent order intents."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        intent_factory: OrderIntentFactory,
        duplicate_guard: DuplicateIntentGuard,
        expiry_policy: IntentExpiryPolicy,
        snapshot_provider: Callable[[str], MarketSnapshot],
        now: Callable[[], object],
    ) -> None:
        self.event_bus = event_bus
        self.intent_factory = intent_factory
        self.duplicate_guard = duplicate_guard
        self.expiry_policy = expiry_policy
        self.snapshot_provider = snapshot_provider
        self.now = now
        self.stats = OrderIntentEngineStats()
        self._unsubscribe = None

    def start(self) -> None:
        if self._unsubscribe is not None:
            raise RuntimeError("engine already started")
        self._unsubscribe = self.event_bus.subscribe("strategy.signal", self._handle_signal)

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _handle_signal(self, event: Event) -> None:
        signal = event.payload.get("signal")
        if not isinstance(signal, StrategySignal):
            raise TypeError("strategy.signal event requires StrategySignal")
        self.process(signal)

    def process(self, signal: StrategySignal) -> OrderIntent | None:
        self.stats.signals_received += 1
        snapshot = self.snapshot_provider(signal.symbol)
        intent = self.intent_factory.create(signal, snapshot)

        if intent is None:
            self.stats.rejected_sizing += 1
            return None

        self.stats.intents_created += 1

        if self.duplicate_guard.is_duplicate(intent):
            self.stats.rejected_duplicate += 1
            return None

        if self.expiry_policy.is_expired(intent, self.now()):
            self.stats.rejected_expired += 1
            return None

        self.event_bus.publish(Event(
            topic="order.intent",
            payload={"intent": intent},
            created_at=self.now(),
        ))
        self.stats.published += 1
        return intent
