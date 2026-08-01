from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionIdempotencyGuard:
    _seen_intent_ids: set[str] = None
    _seen_client_order_ids: set[str] = None

    def __post_init__(self) -> None:
        if self._seen_intent_ids is None:
            self._seen_intent_ids = set()
        if self._seen_client_order_ids is None:
            self._seen_client_order_ids = set()

    def register(self, *, intent_id: str, client_order_id: str) -> bool:
        if intent_id in self._seen_intent_ids or client_order_id in self._seen_client_order_ids:
            return False
        self._seen_intent_ids.add(intent_id)
        self._seen_client_order_ids.add(client_order_id)
        return True
