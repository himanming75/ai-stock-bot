from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .clock import Clock
from .event_bus import Event, EventBus
from .heartbeat import HeartbeatMonitor, HeartbeatStatus
from .recovery import JsonRecoveryStore, RecoverySnapshot
from .scheduler import Scheduler


class RuntimeState(str, Enum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RuntimeConfig:
    heartbeat_interval_seconds: float = 10
    heartbeat_stale_after_seconds: float = 30
    recovery_interval_seconds: float = 30
    network_write_enabled: bool = False
    paper_order_submission_enabled: bool = False
    live_trading_enabled: bool = False

    def validate(self) -> None:
        if self.heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat interval must be positive")
        if self.heartbeat_stale_after_seconds < self.heartbeat_interval_seconds:
            raise ValueError("stale threshold must be >= heartbeat interval")
        if self.recovery_interval_seconds <= 0:
            raise ValueError("recovery interval must be positive")
        if self.network_write_enabled or self.paper_order_submission_enabled or self.live_trading_enabled:
            raise ValueError("V101 runtime foundation must remain write-disabled")


class RuntimeManager:
    """Single-threaded runtime coordinator with explicit ticks and shutdown."""

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        clock: Clock,
        event_bus: EventBus,
        scheduler: Scheduler,
        recovery_store: JsonRecoveryStore,
    ) -> None:
        config.validate()
        self.config = config
        self.clock = clock
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.recovery_store = recovery_store
        self.heartbeat = HeartbeatMonitor(config.heartbeat_stale_after_seconds)
        self.state = RuntimeState.CREATED
        self.tick_count = 0
        self.failure: str | None = None

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.event_bus.publish(Event(topic=topic, payload=payload, created_at=self.clock.now()))

    def start(self) -> None:
        if self.state not in {RuntimeState.CREATED, RuntimeState.STOPPED}:
            raise RuntimeError(f"cannot start from {self.state}")
        self.state = RuntimeState.STARTING
        now = self.clock.now()
        self.scheduler = Scheduler()
        self.scheduler.add_interval(
            name="heartbeat",
            interval_seconds=self.config.heartbeat_interval_seconds,
            first_run_at=now,
            callback=lambda: self.heartbeat.beat(self.clock.now()),
        )
        self.scheduler.add_interval(
            name="recovery_snapshot",
            interval_seconds=self.config.recovery_interval_seconds,
            first_run_at=now,
            callback=self.save_recovery,
        )
        self.state = RuntimeState.RUNNING
        self._publish("runtime.started", {"state": self.state.value})

    def tick(self) -> list[str]:
        if self.state != RuntimeState.RUNNING:
            raise RuntimeError("runtime is not running")
        now = self.clock.now()
        try:
            executed = self.scheduler.run_due(now)
            self.tick_count += 1
            self._publish("runtime.tick", {"tick_count": self.tick_count, "tasks": executed})
            if self.heartbeat.status(now) == HeartbeatStatus.STALE:
                raise RuntimeError("heartbeat is stale")
            return executed
        except Exception as exc:
            self.state = RuntimeState.FAILED
            self.failure = str(exc)
            self._publish("runtime.failed", {"error": self.failure})
            raise

    def save_recovery(self) -> RecoverySnapshot:
        snapshot = RecoverySnapshot(
            state=self.state.value,
            captured_at=self.clock.now(),
            heartbeat_count=self.heartbeat.beat_count,
            scheduler=self.scheduler.snapshot(),
            metadata={
                "tick_count": self.tick_count,
                "network_write_enabled": self.config.network_write_enabled,
                "paper_order_submission_enabled": self.config.paper_order_submission_enabled,
                "live_trading_enabled": self.config.live_trading_enabled,
            },
        )
        self.recovery_store.save(snapshot)
        return snapshot

    def shutdown(self, reason: str = "NORMAL") -> None:
        if self.state in {RuntimeState.STOPPED, RuntimeState.CREATED}:
            self.state = RuntimeState.STOPPED
            return
        self.state = RuntimeState.STOPPING
        self.save_recovery()
        self.state = RuntimeState.STOPPED
        self._publish("runtime.stopped", {"reason": reason, "state": self.state.value})

    def health(self) -> dict[str, Any]:
        now = self.clock.now()
        return {
            "state": self.state.value,
            "tick_count": self.tick_count,
            "heartbeat_status": self.heartbeat.status(now).value,
            "heartbeat_count": self.heartbeat.beat_count,
            "failure": self.failure,
            "network_write_enabled": self.config.network_write_enabled,
            "paper_order_submission_enabled": self.config.paper_order_submission_enabled,
            "live_trading_enabled": self.config.live_trading_enabled,
        }
