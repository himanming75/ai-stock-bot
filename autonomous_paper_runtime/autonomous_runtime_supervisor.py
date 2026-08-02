from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = [
    ("V139.02", "release/v139_02/actual/terminal_commit_handoff_result.json"),
    ("V139.03", "release/v139_03/actual/next_cycle_unlock_result.json"),
    ("V139.04", "release/v139_04/actual/recovery_validation_result.json"),
    ("V139.05", "release/v139_05/actual/autonomous_cycle_resume_result.json"),
    ("V139.06", "release/v139_06/actual/next_order_eligibility_result.json"),
    ("V139.07", "release/v139_07/actual/autonomous_paper_order_launch_result.json"),
    ("V139.08", "release/v139_08/actual/submitted_order_acceptance_verification_result.json"),
    ("V139.09", "release/v139_09/actual/active_order_lifecycle_monitor_result.json"),
    ("V139.10", "release/v139_10/actual/terminal_commit_cycle_completion_result.json"),
    ("V139.11-V139.15", "release/v139_11_to_v139_15/actual/ultra_fast_cycle_finalization_result.json"),
]

TERMINAL_READY_STATES = {
    "NEXT_CYCLE_BOOTSTRAP_READY",
}

WAIT_STATES = {
    "WAIT_TERMINAL_COMMIT",
    "WAIT_HANDOFF",
    "WAIT_UNLOCK",
    "WAIT_RECOVERY_VALIDATION",
    "WAIT_CYCLE_RESUME",
    "WAIT_ELIGIBILITY",
    "WAIT_SUBMISSION_RESULT",
    "WAIT_ACCEPTANCE",
    "WAIT_TERMINAL",
    "WAIT_CYCLE_COMPLETION",
    "ACTIVE_ORDER_MONITORING",
    "PARTIALLY_FILLED",
    "SUBMISSION_DISABLED",
    "WAIT_APPROVAL",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _runtime_cycle_id(bootstrap_id: str) -> str:
    return "runtime-" + hashlib.sha256(bootstrap_id.encode("utf-8")).hexdigest()[:24]


class AutonomousRuntimeSupervisor:
    def run(
        self,
        *,
        repository_root: Path,
        runtime_token_path: Path,
        supervisor_state_path: Path,
        lock_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        selected_stage = ""
        selected_state = ""
        selected_result_path = ""
        stage_results: list[dict[str, Any]] = []
        bootstrap_id = ""
        runtime_cycle_id = ""
        runtime_token_written = False
        duplicate_runtime = False

        if lock_path.exists():
            try:
                lock = _load_json(lock_path)
            except Exception as exc:
                lock = {}
                issues.append({"code": "INVALID_RUNTIME_LOCK", "blocking": True, "detail": str(exc)})
            if lock and not bool(lock.get("released", False)):
                issues.append({
                    "code": "RUNTIME_LOCK_ACTIVE",
                    "blocking": True,
                    "detail": "another supervisor execution is active or was not released",
                })

        if not issues:
            _atomic_write_json(lock_path, {
                "stage": "V140.01",
                "released": False,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            })

        try:
            for stage, relative_path in STAGES:
                path = repository_root / relative_path
                try:
                    result = _load_json(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    issues.append({
                        "code": "INVALID_STAGE_RESULT",
                        "blocking": True,
                        "stage": stage,
                        "detail": str(exc),
                    })
                    break

                if not result:
                    stage_results.append({
                        "stage": stage,
                        "path": str(path.resolve()),
                        "present": False,
                        "state": "",
                        "status": "",
                    })
                    continue

                state = str(result.get("state", "")).upper()
                status = str(result.get("status", "")).upper()
                safe_mode = bool(result.get("safe_mode_engaged", False))
                stage_results.append({
                    "stage": stage,
                    "path": str(path.resolve()),
                    "present": True,
                    "state": state,
                    "status": status,
                    "safe_mode_engaged": safe_mode,
                })

                if status == "BLOCKED" or safe_mode:
                    selected_stage = stage
                    selected_state = state or "SAFE_MODE"
                    selected_result_path = str(path.resolve())
                    issues.append({
                        "code": "DOWNSTREAM_SAFE_MODE",
                        "blocking": True,
                        "stage": stage,
                        "detail": f"stage is blocked: {selected_state}",
                    })
                    break

            if not issues:
                final_path = repository_root / STAGES[-1][1]
                final_result = _load_json(final_path)
                final_state = str(final_result.get("state", "")).upper() if final_result else ""

                if final_state in TERMINAL_READY_STATES and bool(final_result.get("next_cycle_bootstrap_ready", False)):
                    bootstrap_id = str(final_result.get("bootstrap_id", "")).strip()
                    bootstrap_token_path = repository_root / "release/v139_11_to_v139_15/actual/next_cycle_bootstrap_token.json"
                    bootstrap_token = _load_json(bootstrap_token_path)
                    if not bootstrap_id or bootstrap_token.get("bootstrap_id") != bootstrap_id:
                        issues.append({
                            "code": "BOOTSTRAP_TOKEN_MISMATCH",
                            "blocking": True,
                            "detail": "finalization result and bootstrap token do not match",
                        })
                    else:
                        runtime_cycle_id = _runtime_cycle_id(bootstrap_id)
                        token = {
                            "stage": "V140.01",
                            "runtime_cycle_id": runtime_cycle_id,
                            "bootstrap_id": bootstrap_id,
                            "runtime_ready": True,
                            "actual_submission_allowed": False,
                            "broker_network_allowed": False,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                        if runtime_token_path.exists():
                            existing = _load_json(runtime_token_path)
                            if existing.get("runtime_cycle_id") == runtime_cycle_id:
                                duplicate_runtime = True
                            else:
                                issues.append({
                                    "code": "RUNTIME_TOKEN_CONFLICT",
                                    "blocking": True,
                                    "detail": "existing runtime token belongs to another bootstrap",
                                })
                        else:
                            _atomic_write_json(runtime_token_path, token)
                            runtime_token_written = True
                else:
                    # Select the earliest present stage that is still waiting/active.
                    for item in stage_results:
                        if item.get("present") and item.get("state") in WAIT_STATES:
                            selected_stage = str(item["stage"])
                            selected_state = str(item["state"])
                            selected_result_path = str(item["path"])
                            break
                    if not selected_stage:
                        selected_stage = "V139.02"
                        selected_state = "WAIT_PIPELINE_INPUT"
                        selected_result_path = str((repository_root / STAGES[0][1]).resolve())

        finally:
            if lock_path.exists():
                _atomic_write_json(lock_path, {
                    "stage": "V140.01",
                    "released": True,
                    "released_at": datetime.now(timezone.utc).isoformat(),
                })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        runtime_ready = bool(
            runtime_cycle_id
            and (runtime_token_written or duplicate_runtime)
            and not safe_mode
        )

        if safe_mode:
            state = "RUNTIME_SUPERVISOR_SAFE_MODE"
            status = "BLOCKED"
        elif runtime_ready:
            state = "AUTONOMOUS_RUNTIME_READY"
            status = "PASS"
        else:
            state = "RUNTIME_WAITING"
            status = "PASS"

        supervisor_state = {
            "selected_stage": selected_stage,
            "selected_state": selected_state,
            "selected_result_path": selected_result_path,
            "runtime_ready": runtime_ready,
            "runtime_cycle_id": runtime_cycle_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_write_json(supervisor_state_path, supervisor_state)

        result = {
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "actual_paper_orders_submitted": 0,
            "blocking_issue_count": blocking,
            "bootstrap_id": bootstrap_id,
            "duplicate_runtime": duplicate_runtime,
            "implementation_type": "AUTONOMOUS_RUNTIME_SUPERVISOR",
            "issue_count": len(issues),
            "issues": issues,
            "live_orders_submitted": 0,
            "network_requests_executed": 0,
            "next_phase": (
                "V140_02_MARKET_SESSION_CONTROLLER"
                if runtime_ready and not safe_mode
                else selected_stage or "V140_01_WAIT"
            ),
            "result_path": str(result_path.resolve()),
            "runtime_cycle_id": runtime_cycle_id,
            "runtime_ready": runtime_ready,
            "runtime_token_path": str(runtime_token_path.resolve()),
            "runtime_token_written": runtime_token_written,
            "safe_mode_engaged": safe_mode,
            "selected_result_path": selected_result_path,
            "selected_stage": selected_stage,
            "selected_state": selected_state,
            "stage": "V140.01",
            "stage_results": stage_results,
            "state": state,
            "status": status,
            "supervisor_state_path": str(supervisor_state_path.resolve()),
            "validation_mode": "LOCAL_RUNTIME_SUPERVISOR_ONLY",
            "write_requests_executed": 0,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_write_json(result_path, result)
        return result
