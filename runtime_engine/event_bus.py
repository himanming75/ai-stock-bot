from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any, Callable, Deque, DefaultDict
from uuid import uuid4

Handler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    topic: str
    payload: dict[str, Any]
    created_at: datetime
    event_id: str = field(default_factory=lambda: uuid4().hex)


class EventBus:
    """Small synchronous event bus with a bounded audit history."""

    def __init__(self, history_limit: int = 1_000) -> None:
        if history_limit < 1:
            raise ValueError("history_limit must be positive")
        self._handlers: DefaultDict[str, list[Handler]] = defaultdict(list)
        self._history: Deque[Event] = deque(maxlen=history_limit)
        self._lock = RLock()

    def subscribe(self, topic: str, handler: Handler) -> Callable[[], None]:
        if not topic:
            raise ValueError("topic is required")
        with self._lock:
            self._handlers[topic].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._handlers.get(topic, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def publish(self, event: Event) -> int:
        with self._lock:
            handlers = tuple(self._handlers.get(event.topic, ()))
            wildcard = tuple(self._handlers.get("*", ()))
            self._history.append(event)
        for handler in handlers + wildcard:
            handler(event)
        return len(handlers) + len(wildcard)

    def history(self, topic: str | None = None) -> list[Event]:
        with self._lock:
            events = list(self._history)
        return events if topic is None else [e for e in events if e.topic == topic]
