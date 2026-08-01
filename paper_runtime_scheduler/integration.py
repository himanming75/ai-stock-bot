from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable

from paper_scheduler import SchedulerAction, SchedulerDecision


@dataclass(frozen=True)
class RuntimeSchedulerIntegrationConfig:
    allow_prepare_without_runtime_start: bool = True
    save_recovery_after_cycle: bool = True
    save_recovery_on_close: bool = True

    def validate(self) -> None:
        if not isinstance(self.allow_prepare_without_runtime_start, bool):
            raise ValueError("allow_prepare_without_runtime_start must be bool")
        if not isinstance(self.save_recovery_after_cycle, bool):
            raise ValueError("save_recovery_after_cycle must be bool")
        if not isinstance(self.save_recovery_on_close, bool):
            raise ValueError("save_recovery_on_close must be bool")


@dataclass
class RuntimeSchedulerStats:
    scheduler_decisions_received: int = 0
    prepares: int = 0
    sessions_started: int = 0
    cycles_dispatched: int = 0
    cycles_completed: int = 0
    sessions_recovered: int = 0
    sessions_closed: int = 0
    waits: int = 0
    skips: int = 0
    failures: int = 0
    recovery_snapshots: int = 0

    def to_json_dict(self) -> dict[str, int]:
        return asdict(self)


class PaperRuntimeSchedulerIntegration:
    """Maps scheduler actions onto the end-to-end paper runtime lifecycle."""

    def __init__(
        self,
        *,
        runtime: Any,
        config: RuntimeSchedulerIntegrationConfig,
        now: Callable[[], datetime],
    ) -> None:
        config.validate()
        self.runtime = runtime
        self.config = config
        self.now = now
        self.stats = RuntimeSchedulerStats()
        self.events: list[Any] = []
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.actual_paper_orders_submitted = 0
        self.live_orders_submitted = 0

    def handle(self, decision: SchedulerDecision):
        from .models import IntegrationEvent, IntegrationEventType, IntegrationResult

        self.stats.scheduler_decisions_received += 1
        try:
            if decision.action == SchedulerAction.PREPARE:
                return self._prepare(decision)
            if decision.action == SchedulerAction.START_SESSION:
                return self._start(decision)
            if decision.action == SchedulerAction.RUN_CYCLE:
                return self._run_cycle(decision)
            if decision.action == SchedulerAction.RECOVER_SESSION:
                return self._recover(decision)
            if decision.action == SchedulerAction.CLOSE_SESSION:
                return self._close(decision)
            if decision.action == SchedulerAction.SKIP_DAY:
                self.stats.skips += 1
                return self._result(
                    decision, IntegrationEventType.SKIPPED, False, False,
                    "scheduler_day_skipped",
                )
            self.stats.waits += 1
            return self._result(
                decision, IntegrationEventType.WAITING, False, False,
                "scheduler_wait",
            )
        except Exception as exc:
            self.stats.failures += 1
            event = IntegrationEvent(
                created_at=self.now(),
                event_type=IntegrationEventType.FAILED,
                scheduler_action=decision.action.value,
                runtime_state=self._runtime_state(),
                detail=f"{type(exc).__name__}: {exc}",
            )
            self.events.append(event)
            raise

    def _prepare(self, decision):
        from .models import IntegrationEventType
        self.stats.prepares += 1
        if hasattr(self.runtime, "prepare"):
            self.runtime.prepare()
        return self._result(
            decision, IntegrationEventType.PREPARED, False, False,
            "runtime_prepared",
        )

    def _start(self, decision):
        from .models import IntegrationEventType
        state = self._runtime_state()
        if state not in {"READY", "STOPPED", "CREATED"}:
            raise RuntimeError(f"runtime cannot start from state {state}")
        if hasattr(self.runtime, "start"):
            self.runtime.start()
        self.stats.sessions_started += 1
        return self._result(
            decision, IntegrationEventType.SESSION_STARTED, False, False,
            "runtime_session_started",
        )

    def _run_cycle(self, decision):
        from .models import IntegrationEventType
        if self._runtime_state() not in {"READY", "RUNNING"}:
            raise RuntimeError("runtime cycle requires READY or RUNNING state")

        self.stats.cycles_dispatched += 1
        cycle_result = self.runtime.run_cycle()
        completed = bool(
            cycle_result.get("cycle_completed", False)
            if isinstance(cycle_result, dict)
            else getattr(cycle_result, "cycle_completed", False)
        )
        if completed:
            self.stats.cycles_completed += 1

        recovery_saved = False
        if self.config.save_recovery_after_cycle and hasattr(self.runtime, "save_recovery"):
            self.runtime.save_recovery()
            self.stats.recovery_snapshots += 1
            recovery_saved = True

        return self._result(
            decision, IntegrationEventType.CYCLE_COMPLETED,
            completed, recovery_saved, "runtime_cycle_dispatched",
        )

    def _recover(self, decision):
        from .models import IntegrationEventType
        if hasattr(self.runtime, "recover"):
            self.runtime.recover()
        self.stats.sessions_recovered += 1
        return self._result(
            decision, IntegrationEventType.SESSION_RECOVERED,
            False, True, "runtime_session_recovered",
        )

    def _close(self, decision):
        from .models import IntegrationEventType
        recovery_saved = False
        if self.config.save_recovery_on_close and hasattr(self.runtime, "save_recovery"):
            self.runtime.save_recovery()
            self.stats.recovery_snapshots += 1
            recovery_saved = True
        if hasattr(self.runtime, "stop"):
            self.runtime.stop()
        self.stats.sessions_closed += 1
        return self._result(
            decision, IntegrationEventType.SESSION_CLOSED,
            False, recovery_saved, "runtime_session_closed",
        )

    def _result(self, decision, event_type, cycle_completed, recovery_saved, detail):
        from .models import IntegrationEvent, IntegrationResult
        event = IntegrationEvent(
            created_at=self.now(),
            event_type=event_type,
            scheduler_action=decision.action.value,
            runtime_state=self._runtime_state(),
            detail=detail,
        )
        self.events.append(event)
        return IntegrationResult(
            status="PASS",
            scheduler_action=decision.action.value,
            event_type=event_type,
            runtime_state=self._runtime_state(),
            cycle_completed=cycle_completed,
            recovery_saved=recovery_saved,
            detail=detail,
        )

    def _runtime_state(self) -> str:
        state = getattr(self.runtime, "state", "UNKNOWN")
        return getattr(state, "value", str(state))
