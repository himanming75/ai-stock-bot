from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeStressResult:
    cycles_requested: int
    cycles_completed: int
    restart_count: int
    recovery_count: int
    event_count: int
    failures: int
    final_state: str


class RuntimeStressRunner:
    def __init__(self, runtime_factory) -> None:
        self.runtime_factory = runtime_factory

    def run(
        self,
        *,
        cycles: int,
        restart_every: int,
    ) -> RuntimeStressResult:
        if cycles < 1:
            raise ValueError("cycles must be positive")
        if restart_every < 1:
            raise ValueError("restart_every must be positive")

        runtime = self.runtime_factory()
        runtime.start()
        completed = 0
        restarts = 0
        recoveries = 0
        events = ["PREPARE", "START_SESSION"]
        failures = 0

        for index in range(1, cycles + 1):
            try:
                runtime.run_cycle()
                completed += 1
                events.append("RUN_CYCLE")
            except Exception:
                failures += 1
                raise

            if index % restart_every == 0 and index < cycles:
                runtime.save_recovery()
                runtime.stop()
                restarts += 1

                runtime = self.runtime_factory()
                runtime.recover()
                recoveries += 1
                runtime.start()
                events.append("RECOVER_SESSION")

        runtime.save_recovery()
        runtime.close_session()
        runtime.stop()
        events.extend(["CLOSE_SESSION", "STOPPED"])

        return RuntimeStressResult(
            cycles_requested=cycles,
            cycles_completed=completed,
            restart_count=restarts,
            recovery_count=recoveries,
            event_count=len(events),
            failures=failures,
            final_state=runtime.state,
        )
