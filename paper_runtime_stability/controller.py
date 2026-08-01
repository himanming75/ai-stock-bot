from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from .models import StabilityAction, StabilityResult, WatchdogStatus


@dataclass(frozen=True)
class OperationalStabilityConfig:
    cycle_timeout_seconds: float = 30.0
    heartbeat_timeout_seconds: float = 120.0
    max_consecutive_failures: int = 3
    max_recovery_attempts: int = 2
    initial_backoff_seconds: float = 5.0
    max_backoff_seconds: float = 60.0
    backoff_multiplier: float = 3.0

    def validate(self) -> None:
        if self.cycle_timeout_seconds <= 0:
            raise ValueError("cycle timeout must be positive")
        if self.heartbeat_timeout_seconds <= 0:
            raise ValueError("heartbeat timeout must be positive")
        if self.max_consecutive_failures < 1:
            raise ValueError("max consecutive failures must be positive")
        if self.max_recovery_attempts < 0:
            raise ValueError("max recovery attempts cannot be negative")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial backoff cannot be negative")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max backoff must be >= initial backoff")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff multiplier must be >= 1")


@dataclass
class OperationalStabilityStats:
    cycles_attempted: int = 0
    cycles_completed: int = 0
    cycle_failures: int = 0
    cycle_timeouts: int = 0
    recovery_attempts: int = 0
    recoveries_succeeded: int = 0
    circuit_open_count: int = 0
    watchdog_timeouts: int = 0
    graceful_shutdowns: int = 0
    recovery_snapshots: int = 0
    max_observed_consecutive_failures: int = 0

    def to_json_dict(self) -> dict[str, int]:
        return asdict(self)


class OperationalStabilityController:
    def __init__(
        self,
        *,
        runtime: Any,
        config: OperationalStabilityConfig,
        monotonic: Callable[[], float],
        sleep: Callable[[float], None],
    ) -> None:
        config.validate()
        self.runtime = runtime
        self.config = config
        self.monotonic = monotonic
        self.sleep = sleep
        self.stats = OperationalStabilityStats()
        self.consecutive_failures = 0
        self.circuit_open = False
        self.last_heartbeat_at = monotonic()
        self.shutdown_requested = False
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.actual_paper_orders_submitted = 0
        self.live_orders_submitted = 0

    def heartbeat(self) -> WatchdogStatus:
        if self.shutdown_requested:
            return WatchdogStatus.STOPPED
        self.last_heartbeat_at = self.monotonic()
        if hasattr(self.runtime, "heartbeat"):
            self.runtime.heartbeat()
        return WatchdogStatus.HEALTHY

    def check_watchdog(self) -> WatchdogStatus:
        if self.shutdown_requested:
            return WatchdogStatus.STOPPED
        age = self.monotonic() - self.last_heartbeat_at
        if age > self.config.heartbeat_timeout_seconds:
            self.stats.watchdog_timeouts += 1
            self.circuit_open = True
            self._save_recovery()
            return WatchdogStatus.STALE
        return WatchdogStatus.HEALTHY

    def run_cycle(self, *args, **kwargs) -> StabilityResult:
        if self.shutdown_requested:
            raise RuntimeError("shutdown already requested")
        if self.circuit_open:
            self.stats.circuit_open_count += 1
            return self._result(
                StabilityAction.CIRCUIT_OPEN,
                0.0,
                "circuit breaker is open",
            )

        self.stats.cycles_attempted += 1
        started = self.monotonic()
        try:
            result = self.runtime.run_cycle(*args, **kwargs)
            elapsed = self.monotonic() - started
            if elapsed > self.config.cycle_timeout_seconds:
                self.stats.cycle_timeouts += 1
                raise TimeoutError(
                    f"cycle exceeded {self.config.cycle_timeout_seconds} seconds"
                )

            completed = bool(
                result.get("cycle_completed", result.get("completed", False))
                if isinstance(result, dict)
                else getattr(result, "cycle_completed",
                    getattr(result, "completed", False))
            )
            if not completed:
                raise RuntimeError("runtime cycle did not complete")

            self.stats.cycles_completed += 1
            self.consecutive_failures = 0
            self.last_heartbeat_at = self.monotonic()
            return self._result(
                StabilityAction.CYCLE_COMPLETED,
                0.0,
                "cycle completed",
            )
        except Exception as exc:
            self.stats.cycle_failures += 1
            self.consecutive_failures += 1
            self.stats.max_observed_consecutive_failures = max(
                self.stats.max_observed_consecutive_failures,
                self.consecutive_failures,
            )
            self._save_recovery()

            if self.consecutive_failures >= self.config.max_consecutive_failures:
                self.circuit_open = True
                self.stats.circuit_open_count += 1
                return self._result(
                    StabilityAction.CIRCUIT_OPEN,
                    0.0,
                    f"{type(exc).__name__}: {exc}",
                )

            backoff = self._backoff_seconds(self.consecutive_failures)
            self.sleep(backoff)
            return self._result(
                StabilityAction.CYCLE_FAILED,
                backoff,
                f"{type(exc).__name__}: {exc}",
            )

    def attempt_recovery(self) -> StabilityResult:
        if not self.circuit_open:
            return self._result(
                StabilityAction.RECOVERED,
                0.0,
                "recovery not required",
            )

        last_error: Exception | None = None
        for attempt in range(1, self.config.max_recovery_attempts + 1):
            self.stats.recovery_attempts += 1
            try:
                if hasattr(self.runtime, "recover"):
                    self.runtime.recover()
                self.circuit_open = False
                self.consecutive_failures = 0
                self.stats.recoveries_succeeded += 1
                self.last_heartbeat_at = self.monotonic()
                return self._result(
                    StabilityAction.RECOVERED,
                    0.0,
                    f"recovered on attempt {attempt}",
                )
            except Exception as exc:
                last_error = exc
                if attempt < self.config.max_recovery_attempts:
                    self.sleep(self._backoff_seconds(attempt))

        return self._result(
            StabilityAction.CIRCUIT_OPEN,
            0.0,
            f"recovery failed: {last_error}",
        )

    def graceful_shutdown(self) -> StabilityResult:
        if not self.shutdown_requested:
            self.shutdown_requested = True
            self._save_recovery()
            if hasattr(self.runtime, "stop"):
                self.runtime.stop()
            self.stats.graceful_shutdowns += 1
        return self._result(
            StabilityAction.SHUTDOWN,
            0.0,
            "graceful shutdown complete",
        )

    def _backoff_seconds(self, failure_number: int) -> float:
        value = self.config.initial_backoff_seconds * (
            self.config.backoff_multiplier ** max(failure_number - 1, 0)
        )
        return min(value, self.config.max_backoff_seconds)

    def _save_recovery(self) -> None:
        if hasattr(self.runtime, "save_recovery"):
            self.runtime.save_recovery()
            self.stats.recovery_snapshots += 1

    def _runtime_state(self) -> str:
        state = getattr(self.runtime, "state", "UNKNOWN")
        return getattr(state, "value", str(state))

    def _result(
        self,
        action: StabilityAction,
        backoff_seconds: float,
        detail: str,
    ) -> StabilityResult:
        return StabilityResult(
            status="PASS",
            action=action,
            cycle_number=self.stats.cycles_attempted,
            consecutive_failures=self.consecutive_failures,
            backoff_seconds=backoff_seconds,
            runtime_state=self._runtime_state(),
            detail=detail,
        )
