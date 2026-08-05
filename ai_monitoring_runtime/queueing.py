from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SymbolTask:
    task_id: str
    symbol: str
    priority: int
    strategy_id: str

    def as_json(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "symbol": self.symbol,
            "priority": self.priority,
            "strategy_id": self.strategy_id,
        }


class SymbolQueue:
    def __init__(self) -> None:
        self._items: list[SymbolTask] = []

    def put(self, task: SymbolTask) -> None:
        if any(item.task_id == task.task_id for item in self._items):
            raise ValueError("DUPLICATE_TASK_ID")
        self._items.append(task)
        self._items.sort(key=lambda item: (-item.priority, item.symbol))

    def get(self) -> SymbolTask:
        if not self._items:
            raise IndexError("EMPTY_QUEUE")
        return self._items.pop(0)

    def size(self) -> int:
        return len(self._items)

    def snapshot(self) -> list[dict[str, Any]]:
        return [item.as_json() for item in self._items]
