from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from runtime_engine import Event, EventBus

from .freshness import FreshnessMonitor, FreshnessStatus
from .models import Bar, MarketDataMessage, Quote, Trade
from .sequence import SequenceDecision, SequenceGuard
from .subscriptions import SubscriptionRegistry


@dataclass
class RoutingStats:
    received: int = 0
    published: int = 0
    unsubscribed: int = 0
    duplicates: int = 0
    out_of_order: int = 0
    stale: int = 0
    future: int = 0


class MarketDataRouter:
    def __init__(
        self,
        *,
        event_bus: EventBus,
        subscriptions: SubscriptionRegistry,
        sequence_guard: SequenceGuard,
        freshness_monitor: FreshnessMonitor,
        now: Callable[[], datetime],
    ):
        self.event_bus = event_bus
        self.subscriptions = subscriptions
        self.sequence_guard = sequence_guard
        self.freshness_monitor = freshness_monitor
        self.now = now
        self.stats = RoutingStats()

    @staticmethod
    def kind(message: MarketDataMessage) -> str:
        if isinstance(message, Quote):
            return "quote"
        if isinstance(message, Trade):
            return "trade"
        if isinstance(message, Bar):
            return "bar"
        raise TypeError("unsupported market-data message")

    def route(self, message: MarketDataMessage) -> bool:
        self.stats.received += 1
        kind = self.kind(message)
        if not self.subscriptions.accepts(kind, message.symbol):
            self.stats.unsubscribed += 1
            return False

        decision = self.sequence_guard.check(message)
        if decision == SequenceDecision.DUPLICATE:
            self.stats.duplicates += 1
            return False
        if decision == SequenceDecision.OUT_OF_ORDER:
            self.stats.out_of_order += 1
            return False

        freshness = self.freshness_monitor.status(message_time=message.timestamp, now=self.now())
        if freshness == FreshnessStatus.STALE:
            self.stats.stale += 1
            return False
        if freshness == FreshnessStatus.FUTURE:
            self.stats.future += 1
            return False

        self.event_bus.publish(Event(
            topic=f"market_data.{kind}",
            payload={"message": message, "sequence_decision": decision.value},
            created_at=self.now(),
        ))
        self.stats.published += 1
        return True
