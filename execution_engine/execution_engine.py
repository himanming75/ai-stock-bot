from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from runtime_engine import Event, EventBus

from .adapter_models import ExecutionResult, ExecutionStatus
from .models import OrderIntent
from .paper_adapter import PaperExecutionAdapter


@dataclass
class PaperExecutionEngineStats:
    intents_received: int = 0
    requests_created: int = 0
    accepted: int = 0
    rejected: int = 0
    updates_published: int = 0


class PaperExecutionEngine:
    """EventBus bridge from order intents to paper execution updates."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        adapter: PaperExecutionAdapter,
        now: Callable[[], object],
    ) -> None:
        self.event_bus = event_bus
        self.adapter = adapter
        self.now = now
        self.stats = PaperExecutionEngineStats()
        self._unsubscribe = None

    def start(self) -> None:
        if self._unsubscribe is not None:
            raise RuntimeError("engine already started")
        self._unsubscribe = self.event_bus.subscribe("order.intent", self._handle_intent)

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _handle_intent(self, event: Event) -> None:
        intent = event.payload.get("intent")
        if not isinstance(intent, OrderIntent):
            raise TypeError("order.intent event requires OrderIntent")
        self.process(intent)

    def process(self, intent: OrderIntent) -> ExecutionResult:
        self.stats.intents_received += 1
        request, result = self.adapter.submit(intent, self.now())
        self.stats.requests_created += 1
        if result.status == ExecutionStatus.ACCEPTED:
            self.stats.accepted += 1
        elif result.status == ExecutionStatus.REJECTED:
            self.stats.rejected += 1

        self.event_bus.publish(Event(
            topic="execution.request",
            payload={"request": request},
            created_at=self.now(),
        ))
        self.event_bus.publish(Event(
            topic="execution.update",
            payload={"result": result},
            created_at=self.now(),
        ))
        self.stats.updates_published += 1
        return result
