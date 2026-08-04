from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from continuous_service_runtime.io import (
    load_json, write_json, append_jsonl, digest
)
from continuous_service_runtime.state_machine import transition
from continuous_service_runtime.heartbeat import heartbeat
from continuous_service_runtime.scheduler import scheduler_tick
from continuous_service_runtime.checkpoint import save_checkpoint
from continuous_service_runtime.recovery import build_recovery
from continuous_service_runtime.shutdown import graceful_shutdown

def run_runtime(
    root: Path,
    max_ticks: int | None = None,
) -> dict[str, Any]:
    policy = load_json(
        root / "release/v104_33_to_v104_64/input/"
        "continuous_runtime_policy.json"
    )
    core = load_json(
        root / "release/v104_01_to_v104_32/actual/"
        "continuous_autonomous_engine_result.json"
    )
    actual_dir = root / "release/v104_33_to_v104_64/actual"
    checkpoint_path = actual_dir / "continuous_runtime_checkpoint.json"

    if max_ticks is None:
        max_ticks = int(policy.get("default_max_ticks", 3))
    max_ticks = max(1, min(max_ticks, int(policy.get("maximum_ticks_per_run", 10))))

    runtime_id = digest({
        "engine_id": core.get("engine_id"),
        "policy_version": policy.get("policy_version"),
        "max_ticks": max_ticks,
    })[:24]

    state = "IDLE"
    events = []
    heartbeats = []
    ticks = []
    errors = []

    first = transition(state, "WAITING")
    state = first["state"]
    events.append({"event": "RUNTIME_START", **first})

    for index in range(1, max_ticks + 1):
        hb = heartbeat(index, state)
        heartbeats.append(hb)
        append_jsonl(actual_dir / "continuous_runtime_ledger.jsonl", {
            "event": "HEARTBEAT",
            **hb,
            "runtime_id": runtime_id,
        })

        tick = scheduler_tick(core)
        tick["tick_number"] = index
        ticks.append(tick)

        if tick["action"] == "PROCESS_SELECTED_SESSION":
            step = transition(state, "RUNNING")
            state = step["state"]
            events.append({"event": "RUNTIME_RUNNING", **step})
            back = transition(state, "WAITING")
            state = back["state"]
            events.append({"event": "RUNTIME_WAITING", **back})
        elif tick["action"] == "WAIT_FOR_MANUAL_APPROVAL":
            state = "WAITING"
            events.append({
                "event": "MANUAL_APPROVAL_WAIT",
                "state": state,
                "tick_number": index,
            })
        else:
            state = "WAITING"
            events.append({
                "event": "SCHEDULER_IDLE",
                "state": state,
                "tick_number": index,
            })

        append_jsonl(actual_dir / "continuous_runtime_ledger.jsonl", {
            "event": "SCHEDULER_TICK",
            **tick,
            "runtime_id": runtime_id,
            "runtime_state": state,
        })

    checkpoint = save_checkpoint(
        checkpoint_path,
        runtime_id,
        state,
        len(ticks),
        len(heartbeats),
    )
    recovery = build_recovery(state, errors, policy)
    shutdown = graceful_shutdown("CONTROLLED_MAX_TICKS_REACHED")

    observed_at = datetime.now(timezone.utc).isoformat()
    body = {
        "stage": "V104.64",
        "stage_range": "V104.33-V104.64",
        "state": "CONTINUOUS_SERVICE_RUNTIME_READY",
        "status": "PASS",
        "observed_at": observed_at,
        "runtime_id": runtime_id,
        "source_engine_id": core.get("engine_id"),
        "source_engine_state": core.get("state"),
        "max_ticks": max_ticks,
        "tick_count": len(ticks),
        "heartbeat_count": len(heartbeats),
        "runtime_events": events,
        "scheduler_ticks": ticks,
        "heartbeats": heartbeats,
        "checkpoint": checkpoint,
        "recovery": recovery,
        "shutdown": shutdown,
        "runtime_started": True,
        "runtime_stopped_cleanly": True,
        "background_service_installed": False,
        "background_service_running": False,
        "approval_granted": False,
        "execution_authorized": False,
        "manual_approval_required": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "unbounded_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V105_01_FINAL_INTEGRATION",
    }
    body["continuous_runtime_certificate_sha256"] = digest(body)

    write_json(
        actual_dir / "continuous_service_runtime_result.json",
        body,
    )
    append_jsonl(
        actual_dir / "continuous_runtime_ledger.jsonl",
        {
            "event": "RUNTIME_STOP",
            "runtime_id": runtime_id,
            "observed_at": observed_at,
            "state": body["state"],
            "tick_count": len(ticks),
            "heartbeat_count": len(heartbeats),
            "runtime_stopped_cleanly": True,
            "actual_orders_submitted": 0,
        },
    )
    return body
