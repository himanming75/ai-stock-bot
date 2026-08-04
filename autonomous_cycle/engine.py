from __future__ import annotations
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from autonomous_cycle.io import (
    load_json, write_json, append_jsonl, read_jsonl, digest
)
from autonomous_cycle.model import initial_steps
from autonomous_cycle.identity import build_cycle_identity
from autonomous_cycle.dedup import detect_duplicate
from autonomous_cycle.lock import acquire_lock, release_lock
from autonomous_cycle.checkpoint import save_checkpoint
from autonomous_cycle.executor import execute_step
from autonomous_cycle.state import resolve_cycle_state

def evaluate(
    root: Path,
    cycle_date: str | None = None,
) -> dict[str, Any]:
    policy = load_json(
        root / "release/v103_01_to_v103_32/input/"
        "autonomous_cycle_policy.json"
    )
    decision = load_json(
        root / "release/v102_33_to_v102_64/actual/"
        "autonomous_decision_result.json"
    )
    actual_dir = root / "release/v103_01_to_v103_32/actual"
    ledger_path = actual_dir / "autonomous_cycle_ledger.jsonl"
    lock_path = actual_dir / "autonomous_cycle_lock.json"
    checkpoint_path = actual_dir / "autonomous_cycle_checkpoint.json"

    if cycle_date is None:
        cycle_date = date.today().isoformat()

    identity = build_cycle_identity(decision, policy, cycle_date)

    if (
        not decision
        or decision.get("status") != "PASS"
        or not decision.get("decision_id")
    ):
        observed_at = datetime.now(timezone.utc).isoformat()
        body = {
            "stage": "V103.32",
            "stage_range": "V103.01-V103.32",
            "state": "AUTONOMOUS_CYCLE_BLOCKED",
            "status": "PASS",
            "observed_at": observed_at,
            **identity,
            "source_decision_state": decision.get("state"),
            "source_decision": decision.get(
                "autonomous_decision", {}
            ).get("decision"),
            "cycle_action": "BLOCK_MISSING_OR_INVALID_SOURCE",
            "steps": [],
            "completed_step_count": 0,
            "failed_steps": ["VALIDATE_SOURCE_DECISION"],
            "duplicate": {
                "duplicate_cycle": False,
                "duplicate_match_count": 0,
                "previous_cycle_id": None,
                "previous_state": None,
            },
            "lock": {
                "acquired": False,
                "reason": "SOURCE_DECISION_INVALID",
            },
            "lock_release": {
                "released": False,
                "reason": "LOCK_NOT_ACQUIRED",
            },
            "checkpoint": {},
            "approval_eligible": False,
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
            "continuous_loop_enabled": False,
            "windows_task_enabled": False,
            "next_phase": "V103_33_MULTI_DAY_CYCLE_SCHEDULER",
        }
        body["autonomous_cycle_certificate_sha256"] = digest(body)
        write_json(actual_dir / "autonomous_cycle_result.json", body)
        append_jsonl(
            ledger_path,
            {
                "observed_at": observed_at,
                "cycle_id": identity["cycle_id"],
                "cycle_key": identity["cycle_key"],
                "cycle_date": cycle_date,
                "source_decision_id": identity["source_decision_id"],
                "source_decision": body["source_decision"],
                "state": body["state"],
                "cycle_action": body["cycle_action"],
                "completed_step_count": 0,
                "failed_steps": body["failed_steps"],
                "approval_granted": False,
                "execution_authorized": False,
                "actual_orders_submitted": 0,
            },
        )
        return body
    duplicate = detect_duplicate(
        identity["cycle_key"],
        read_jsonl(ledger_path),
    )

    if duplicate["duplicate_cycle"]:
        body = {
            "stage": "V103.32",
            "stage_range": "V103.01-V103.32",
            "state": "AUTONOMOUS_CYCLE_DUPLICATE_BLOCKED",
            "status": "PASS",
            **identity,
            "duplicate": duplicate,
            "actual_orders_submitted": 0,
            "execution_authorized": False,
            "manual_approval_required": True,
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "next_phase": "V103_33_MULTI_DAY_CYCLE_SCHEDULER",
        }
        body["autonomous_cycle_certificate_sha256"] = digest(body)
        write_json(actual_dir / "autonomous_cycle_result.json", body)
        return body

    final = resolve_cycle_state(decision)
    lock = acquire_lock(
        lock_path,
        identity["cycle_id"],
        int(policy.get("lock_timeout_seconds", 300)),
    )

    steps = initial_steps()
    context = {
        "source_status": decision.get("status"),
        "lock_acquired": lock.get("acquired") is True,
        "checkpoint_enabled": policy.get("checkpoint_enabled") is True,
        "manual_approval_required": True,
        "paper_only": True,
        "actual_orders_submitted": 0,
        "final_state": final["state"],
    }

    cycle = {
        **identity,
        "state": "AUTONOMOUS_CYCLE_RUNNING",
        "current_step": 0,
        "steps": steps,
    }
    checkpoint = save_checkpoint(checkpoint_path, cycle)

    failed_steps = []
    for index, step in enumerate(steps):
        cycle["current_step"] = index + 1
        executed = execute_step(step, context, policy)
        cycle["steps"][index] = executed
        checkpoint = save_checkpoint(checkpoint_path, cycle)
        if executed["state"] != "COMPLETED":
            failed_steps.append(executed["step_id"])
            break

    observed_at = datetime.now(timezone.utc).isoformat()
    if failed_steps:
        state = "AUTONOMOUS_CYCLE_RETRY_REQUIRED"
        cycle_action = "RETRY_FAILED_STEP"
    else:
        state = final["state"]
        cycle_action = final["cycle_action"]

    release = release_lock(lock_path, identity["cycle_id"])

    body = {
        "stage": "V103.32",
        "stage_range": "V103.01-V103.32",
        "state": state,
        "status": "PASS",
        "observed_at": observed_at,
        **identity,
        "source_decision_state": decision.get("state"),
        "source_decision": decision.get(
            "autonomous_decision", {}
        ).get("decision"),
        "cycle_action": cycle_action,
        "steps": cycle["steps"],
        "completed_step_count": sum(
            1 for row in cycle["steps"] if row["state"] == "COMPLETED"
        ),
        "failed_steps": failed_steps,
        "duplicate": duplicate,
        "lock": lock,
        "lock_release": release,
        "checkpoint": checkpoint,
        "approval_eligible": final["approval_eligible"],
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
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V103_33_MULTI_DAY_CYCLE_SCHEDULER",
    }
    body["autonomous_cycle_certificate_sha256"] = digest(body)

    write_json(actual_dir / "autonomous_cycle_result.json", body)
    append_jsonl(
        ledger_path,
        {
            "observed_at": observed_at,
            "cycle_id": identity["cycle_id"],
            "cycle_key": identity["cycle_key"],
            "cycle_date": cycle_date,
            "source_decision_id": identity["source_decision_id"],
            "source_decision": body["source_decision"],
            "state": state,
            "cycle_action": cycle_action,
            "completed_step_count": body["completed_step_count"],
            "failed_steps": failed_steps,
            "approval_granted": False,
            "execution_authorized": False,
            "actual_orders_submitted": 0,
        },
    )
    return body
