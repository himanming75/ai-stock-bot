from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Callable

TaskCallback = Callable[[], None]


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: float
    callback: TaskCallback
    next_run_at: datetime
    enabled: bool = True
    run_count: int = 0
    last_run_at: datetime | None = None

    def validate(self) -> None:
        if not self.name:
            raise ValueError("task name is required")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")


class Scheduler:
    """Deterministic interval scheduler. It never creates background threads."""

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._lock = RLock()

    def add_interval(
        self,
        *,
        name: str,
        interval_seconds: float,
        first_run_at: datetime,
        callback: TaskCallback,
    ) -> ScheduledTask:
        task = ScheduledTask(name, interval_seconds, callback, first_run_at)
        task.validate()
        with self._lock:
            if name in self._tasks:
                raise ValueError(f"task already exists: {name}")
            self._tasks[name] = task
        return task

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._tasks.pop(name, None) is not None

    def due(self, now: datetime) -> list[ScheduledTask]:
        with self._lock:
            return sorted(
                [t for t in self._tasks.values() if t.enabled and t.next_run_at <= now],
                key=lambda task: (task.next_run_at, task.name),
            )

    def run_due(self, now: datetime) -> list[str]:
        executed: list[str] = []
        for task in self.due(now):
            task.callback()
            task.run_count += 1
            task.last_run_at = now
            while task.next_run_at <= now:
                task.next_run_at += timedelta(seconds=task.interval_seconds)
            executed.append(task.name)
        return executed

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return [
                {
                    "name": t.name,
                    "interval_seconds": t.interval_seconds,
                    "next_run_at": t.next_run_at.isoformat(),
                    "enabled": t.enabled,
                    "run_count": t.run_count,
                    "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                }
                for t in sorted(self._tasks.values(), key=lambda task: task.name)
            ]
