from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from paper_runtime_stability import StabilityAction, WatchdogStatus
from paper_scheduler import SchedulerAction

from .models import (
    ContinuousRuntimeAction,
    ContinuousRuntimeResult,
    ContinuousRuntimeState,
)


@dataclass(frozen=True)
class ContinuousRuntimeConfig:
    max_ticks: int = 1000
    heartbeat_every_ticks: int = 1
    stop_on_session_close: bool = True
    stop_on_skip_day: bool = True
    recover_on_circuit_open: bool = True

    def validate(self) -> None:
        if not 1 <= self.max_ticks <= 100000:
            raise ValueError("max_ticks must be between 1 and 100000")
        if not 1 <= self.heartbeat_every_ticks <= 10000:
            raise ValueError("heartbeat_every_ticks must be between 1 and 10000")
        if not isinstance(self.stop_on_session_close, bool):
            raise ValueError("stop_on_session_close must be bool")
        if not isinstance(self.stop_on_skip_day, bool):
            raise ValueError("stop_on_skip_day must be bool")
        if not isinstance(self.recover_on_circuit_open, bool):
            raise ValueError("recover_on_circuit_open must be bool")


@dataclass
class ContinuousRuntimeStats:
    ticks_started: int = 0
    ticks_completed: int = 0
    scheduler_decisions: int = 0
    cycles_requested: int = 0
    cycles_completed: int = 0
    waits: int = 0
    skips: int = 0
    heartbeat_calls: int = 0
    watchdog_checks: int = 0
    recoveries_requested: int = 0
    recoveries_completed: int = 0
    stop_requests: int = 0
    graceful_shutdowns: int = 0
    failures: int = 0

    def to_json_dict(self) -> dict[str, int]:
        return asdict(self)


class ContinuousPaperRuntime:
    """Single-threaded continuous loop joining scheduler, integration, and stability."""

    def __init__(
        self,
        *,
        scheduler: Any,
        integration: Any,
        stability: Any,
        config: ContinuousRuntimeConfig,
        sleep: Callable[[float], None],
    ) -> None:
        config.validate()
        self.scheduler = scheduler
        self.integration = integration
        self.stability = stability
        self.config = config
        self.sleep = sleep
        self.state = ContinuousRuntimeState.CREATED
        self.stats = ContinuousRuntimeStats()
        self.stop_requested = False
        self.last_result: ContinuousRuntimeResult | None = None

    @property
    def network_requests_executed(self) -> int:
        return int(getattr(self.stability, "network_requests_executed", 0))

    @property
    def write_requests_executed(self) -> int:
        return int(getattr(self.stability, "write_requests_executed", 0))

    @property
    def actual_paper_orders_submitted(self) -> int:
        return int(getattr(self.stability, "actual_paper_orders_submitted", 0))

    @property
    def live_orders_submitted(self) -> int:
        return int(getattr(self.stability, "live_orders_submitted", 0))

    def start(self) -> ContinuousRuntimeResult:
        if self.state not in {
            ContinuousRuntimeState.CREATED,
            ContinuousRuntimeState.STOPPED,
        }:
            raise RuntimeError(f"cannot start from {self.state.value}")
        self.state = ContinuousRuntimeState.RUNNING
        self.stop_requested = False
        return self._result(
            ContinuousRuntimeAction.STARTED,
            "continuous runtime started",
        )

    def request_stop(self) -> ContinuousRuntimeResult:
        if not self.stop_requested:
            self.stop_requested = True
            self.stats.stop_requests += 1
        return self._result(
            ContinuousRuntimeAction.STOP_REQUESTED,
            "stop requested",
        )

    def run(self) -> ContinuousRuntimeResult:
        if self.state != ContinuousRuntimeState.RUNNING:
            raise RuntimeError("continuous runtime must be started before run")

        for _ in range(self.config.max_ticks):
            if self.stop_requested:
                break
            self.tick()

        return self.shutdown()

    def tick(self) -> ContinuousRuntimeResult:
        if self.state != ContinuousRuntimeState.RUNNING:
            raise RuntimeError("tick requires RUNNING state")
        if self.stop_requested:
            return self._result(
                ContinuousRuntimeAction.STOP_REQUESTED,
                "tick skipped because stop was requested",
            )

        self.stats.ticks_started += 1
        tick_number = self.stats.ticks_started

        try:
            self.stats.watchdog_checks += 1
            watchdog = self.stability.check_watchdog()
            if watchdog == WatchdogStatus.STALE:
                if not self.config.recover_on_circuit_open:
                    raise RuntimeError("watchdog stale")
                recovery = self._recover()
                self.stats.ticks_completed += 1
                return recovery

            if tick_number % self.config.heartbeat_every_ticks == 0:
                self.stability.heartbeat()
                self.stats.heartbeat_calls += 1

            decision = self.scheduler.tick()
            self.stats.scheduler_decisions += 1

            if decision.action == SchedulerAction.RUN_CYCLE:
                self.stats.cycles_requested += 1
                stability_result = self.stability.run_cycle()
                if stability_result.action == StabilityAction.CYCLE_COMPLETED:
                    self.stats.cycles_completed += 1
                    self.integration.handle(decision)
                    result = self._result(
                        ContinuousRuntimeAction.TICK_COMPLETED,
                        "runtime cycle completed",
                    )
                elif stability_result.action == StabilityAction.CIRCUIT_OPEN:
                    result = self._recover()
                else:
                    result = self._result(
                        ContinuousRuntimeAction.WAITED,
                        f"cycle deferred: {stability_result.action.value}",
                    )
            else:
                integration_result = self.integration.handle(decision)
                if decision.action == SchedulerAction.CLOSE_SESSION:
                    result = self._result(
                        ContinuousRuntimeAction.SESSION_CLOSED,
                        integration_result.detail,
                    )
                    if self.config.stop_on_session_close:
                        self.request_stop()
                elif decision.action == SchedulerAction.SKIP_DAY:
                    self.stats.skips += 1
                    result = self._result(
                        ContinuousRuntimeAction.SKIPPED,
                        integration_result.detail,
                    )
                    if self.config.stop_on_skip_day:
                        self.request_stop()
                else:
                    self.stats.waits += 1
                    result = self._result(
                        ContinuousRuntimeAction.WAITED,
                        integration_result.detail,
                    )

            delay = max(0, int(getattr(decision, "next_wakeup_seconds", 0)))
            if delay and not self.stop_requested:
                self.sleep(delay)

            self.stats.ticks_completed += 1
            return result
        except Exception as exc:
            self.stats.failures += 1
            self.state = ContinuousRuntimeState.FAILED
            self.last_result = self._result(
                ContinuousRuntimeAction.FAILED,
                f"{type(exc).__name__}: {exc}",
            )
            raise

    def restart(self) -> ContinuousRuntimeResult:
        if self.state not in {
            ContinuousRuntimeState.CREATED,
            ContinuousRuntimeState.STOPPED,
            ContinuousRuntimeState.FAILED,
        }:
            raise RuntimeError(f"cannot restart from {self.state.value}")

        self.state = ContinuousRuntimeState.RECOVERING
        decision = self.scheduler.recover()
        self.stats.scheduler_decisions += 1
        self.integration.handle(decision)
        self.stats.recoveries_requested += 1

        recovery_result = self.stability.attempt_recovery()
        if recovery_result.action == StabilityAction.CIRCUIT_OPEN:
            self.state = ContinuousRuntimeState.FAILED
            raise RuntimeError("stability recovery failed")

        self.stats.recoveries_completed += 1
        self.state = ContinuousRuntimeState.RUNNING
        self.stop_requested = False
        return self._result(
            ContinuousRuntimeAction.RECOVERED,
            "continuous runtime restarted and recovered",
        )

    def shutdown(self) -> ContinuousRuntimeResult:
        if self.state == ContinuousRuntimeState.STOPPED:
            return self._result(
                ContinuousRuntimeAction.STOPPED,
                "continuous runtime already stopped",
            )

        self.state = ContinuousRuntimeState.STOPPING
        self.stability.graceful_shutdown()
        self.stats.graceful_shutdowns += 1
        self.state = ContinuousRuntimeState.STOPPED
        return self._result(
            ContinuousRuntimeAction.STOPPED,
            "continuous runtime stopped",
        )

    def _recover(self) -> ContinuousRuntimeResult:
        self.state = ContinuousRuntimeState.RECOVERING
        self.stats.recoveries_requested += 1
        recovery = self.stability.attempt_recovery()
        if recovery.action == StabilityAction.CIRCUIT_OPEN:
            self.state = ContinuousRuntimeState.FAILED
            raise RuntimeError("automatic recovery failed")
        self.stats.recoveries_completed += 1
        self.state = ContinuousRuntimeState.RUNNING
        return self._result(
            ContinuousRuntimeAction.RECOVERED,
            "automatic recovery completed",
        )

    def _result(
        self,
        action: ContinuousRuntimeAction,
        detail: str,
    ) -> ContinuousRuntimeResult:
        result = ContinuousRuntimeResult(
            status="PASS",
            action=action,
            state=self.state,
            tick_number=self.stats.ticks_started,
            cycles_completed=self.stats.cycles_completed,
            detail=detail,
        )
        self.last_result = result
        return result
