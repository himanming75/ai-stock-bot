from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib

from .cycle_registry import LiveCycleRegistry
from .ledger import append_cycle
from .lock import LiveRuntimeLock
from .state import write_checkpoint, write_heartbeat


def _cycle_id(runtime_id: str, cycle_number: int) -> str:
    raw = f"{runtime_id}:{cycle_number}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def run_offline_live_runtime(
    *,
    root: Path,
    runtime_id: str,
    cycles: int,
    market_open: bool,
) -> dict[str, Any]:
    actual = root / "release/l5_live_autonomous_runtime_preparation/actual"
    lock = LiveRuntimeLock(actual / "runtime.lock.json")
    registry = LiveCycleRegistry(actual / "cycle_registry.json")

    if not market_open:
        return {
            "stage": "L5",
            "status": "PASS",
            "state": "LIVE_RUNTIME_BLOCKED_MARKET_CLOSED",
            "completed_cycle_count": 0,
            "actual_live_runtime_allowed": False,
            "actual_live_orders_submitted": 0,
            "actual_paper_orders_submitted": 0,
        }

    lock.acquire(runtime_id)
    completed = 0
    try:
        for cycle_number in range(1, cycles + 1):
            cycle_id = _cycle_id(runtime_id, cycle_number)
            registry.reserve(cycle_id)
            write_heartbeat(
                actual / "heartbeat.json",
                runtime_id=runtime_id,
                cycle_number=cycle_number,
                state="HEALTHY",
            )
            write_checkpoint(
                actual / "runtime_checkpoint.json",
                runtime_id=runtime_id,
                cycle_id=cycle_id,
                cycle_number=cycle_number,
                state="L5_CYCLE_COMPLETE",
            )
            append_cycle(
                actual / "cycle_ledger.jsonl",
                {
                    "record_type": "LIVE_RUNTIME_OFFLINE_CYCLE",
                    "runtime_id": runtime_id,
                    "cycle_id": cycle_id,
                    "cycle_number": cycle_number,
                    "broker_network_used": False,
                    "broker_submission_attempted": False,
                },
            )
            completed += 1
    finally:
        lock.release()

    return {
        "stage": "L5",
        "status": "PASS",
        "state": "LIVE_AUTONOMOUS_RUNTIME_PREPARED",
        "runtime_id": runtime_id,
        "completed_cycle_count": completed,
        "actual_live_runtime_allowed": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "automatic_order_replay_enabled": False,
        "automatic_broker_restart_enabled": False,
        "actual_live_orders_submitted": 0,
        "actual_paper_orders_submitted": 0,
        "next_fixed_stage": (
            "L5_ACTUAL_AFTER_L4_ACTUAL_RECONCILIATION"
        ),
    }
