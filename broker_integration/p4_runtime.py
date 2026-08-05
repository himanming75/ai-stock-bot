from __future__ import annotations
from datetime import datetime, timezone
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .p4_cycle_guard import reserve_cycle, update_cycle
from .p4_health import health_check
from .p4_lock import acquire_lock, release_lock
from .p4_runtime_models import RuntimePolicy
from .p4_state import append_jsonl, write_checkpoint, write_heartbeat


class AutonomousPaperRuntime:
    def __init__(
        self,
        *,
        root: Path,
        policy: RuntimePolicy,
        paths: dict[str, Path],
        market_clock_reader: Callable[[], dict[str, Any]],
        kill_switch_reader: Callable[[], dict[str, Any]],
        validation_reader: Callable[[], dict[str, bool]],
        cycle_executor: Callable[[dict[str, Any]], dict[str, Any]],
        sleeper: Callable[[float], None] = time.sleep,
        runtime_id: str | None = None,
    ) -> None:
        policy.validate()
        self.root = root
        self.policy = policy
        self.paths = paths
        self.market_clock_reader = market_clock_reader
        self.kill_switch_reader = kill_switch_reader
        self.validation_reader = validation_reader
        self.cycle_executor = cycle_executor
        self.sleeper = sleeper
        self.runtime_id = runtime_id or f"p4-{uuid.uuid4().hex}"

    def run(self) -> dict[str, Any]:
        acquire_lock(self.paths["lock"], self.runtime_id)
        cycle_results: list[dict[str, Any]] = []
        session_blockers: list[str] = []

        try:
            for cycle_number in range(
                1,
                self.policy.maximum_cycles_per_session + 1,
            ):
                now = datetime.now(timezone.utc)
                trading_day = now.date().isoformat()
                created, identifier = reserve_cycle(
                    self.paths["cycle_registry"],
                    runtime_id=self.runtime_id,
                    cycle_number=cycle_number,
                    trading_day=trading_day,
                )
                if not created:
                    session_blockers.append("DUPLICATE_CYCLE")
                    write_checkpoint(
                        self.paths["checkpoint"],
                        runtime_id=self.runtime_id,
                        cycle_number=cycle_number,
                        cycle_id=identifier,
                        state="P4_RUNTIME_BLOCKED",
                        blockers=session_blockers,
                    )
                    break

                market_clock = self.market_clock_reader()
                kill_switch = self.kill_switch_reader()
                validations = self.validation_reader()
                health = health_check(
                    root=self.root,
                    kill_switch=kill_switch,
                    market_clock=market_clock,
                    p2_actual_validated=validations.get(
                        "p2_actual_validated",
                        False,
                    ),
                    p3_actual_validated=validations.get(
                        "p3_actual_validated",
                        False,
                    ),
                    require_market_open=self.policy.require_market_open,
                    require_p2_actual_validation=(
                        self.policy.require_p2_actual_validation
                    ),
                    require_p3_actual_validation=(
                        self.policy.require_p3_actual_validation
                    ),
                )

                write_heartbeat(
                    self.paths["heartbeat"],
                    runtime_id=self.runtime_id,
                    cycle_number=cycle_number,
                    state=(
                        "HEALTHY"
                        if health["healthy"]
                        else "BLOCKED"
                    ),
                )

                if not health["healthy"]:
                    update_cycle(
                        self.paths["cycle_registry"],
                        identifier,
                        state="BLOCKED",
                        blockers=health["failed"],
                    )
                    session_blockers.extend(health["failed"])
                    write_checkpoint(
                        self.paths["checkpoint"],
                        runtime_id=self.runtime_id,
                        cycle_number=cycle_number,
                        cycle_id=identifier,
                        state="P4_RUNTIME_BLOCKED",
                        blockers=health["failed"],
                    )
                    cycle_results.append({
                        "cycle_number": cycle_number,
                        "cycle_id": identifier,
                        "executed": False,
                        "health": health,
                    })
                    break

                context = {
                    "runtime_id": self.runtime_id,
                    "cycle_number": cycle_number,
                    "cycle_id": identifier,
                    "market_clock": market_clock,
                    "observed_at": now.isoformat(),
                }
                cycle_result = self.cycle_executor(context)

                failed_closed = (
                    cycle_result.get("status") != "PASS"
                    or cycle_result.get("reconciliation_passed") is False
                    or cycle_result.get("new_order_submission_allowed") is False
                )
                if failed_closed:
                    blockers = cycle_result.get(
                        "blockers",
                        ["CYCLE_FAIL_CLOSED"],
                    )
                    update_cycle(
                        self.paths["cycle_registry"],
                        identifier,
                        state="BLOCKED",
                        blockers=blockers,
                    )
                    write_checkpoint(
                        self.paths["checkpoint"],
                        runtime_id=self.runtime_id,
                        cycle_number=cycle_number,
                        cycle_id=identifier,
                        state="P4_RUNTIME_BLOCKED",
                        blockers=blockers,
                    )
                    cycle_results.append(cycle_result)
                    session_blockers.extend(blockers)
                    break

                update_cycle(
                    self.paths["cycle_registry"],
                    identifier,
                    state="COMPLETE",
                )
                write_checkpoint(
                    self.paths["checkpoint"],
                    runtime_id=self.runtime_id,
                    cycle_number=cycle_number,
                    cycle_id=identifier,
                    state="P4_CYCLE_COMPLETE",
                    blockers=[],
                )
                append_jsonl(
                    self.paths["cycle_ledger"],
                    {
                        **context,
                        "cycle_result": cycle_result,
                    },
                )
                cycle_results.append(cycle_result)

                if cycle_number < self.policy.maximum_cycles_per_session:
                    self.sleeper(self.policy.cycle_interval_seconds)

            status = "PASS" if not session_blockers else "BLOCKED"
            return {
                "stage": "P4",
                "state": (
                    "AUTONOMOUS_PAPER_RUNTIME_SESSION_COMPLETE"
                    if status == "PASS"
                    else "AUTONOMOUS_PAPER_RUNTIME_BLOCKED"
                ),
                "status": status,
                "runtime_id": self.runtime_id,
                "completed_cycle_count": sum(
                    1
                    for value in cycle_results
                    if value.get("status") == "PASS"
                ),
                "cycle_result_count": len(cycle_results),
                "blockers": sorted(set(session_blockers)),
                "broker_write_enabled": False,
                "paper_submission_enabled": False,
                "live_submission_enabled": False,
                "actual_paper_orders_submitted": 0,
                "actual_live_orders_submitted": 0,
                "next_fixed_stage": "P5_PAPER_LONG_RUN_QUALIFICATION",
            }
        finally:
            release_lock(self.paths["lock"], self.runtime_id)
