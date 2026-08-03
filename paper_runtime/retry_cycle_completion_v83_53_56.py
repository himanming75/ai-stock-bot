from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def certificate_id(trigger_id: str, execution_id: str, observed_at: str) -> str:
    raw = f"{trigger_id}|{execution_id}|{observed_at}".encode("utf-8")
    return "retry-cycle-cert-" + hashlib.sha256(raw).hexdigest()[:20]


def run_retry_cycle_completion(
    *,
    runner_result_path: Path,
    runner_completion_path: Path,
    runner_recovery_path: Path,
    retry_policy_result_path: Path,
    retry_plan_path: Path,
    original_recovery_path: Path,
    trigger_plan_path: Path,
    policy_path: Path,
    completion_ledger_path: Path,
    certificate_path: Path,
    dashboard_path: Path,
    result_path: Path,
    finalize: bool = False,
    observed_at_override: str = "",
) -> dict[str, Any]:
    observed = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    observed_iso = observed.isoformat()

    issues: list[dict[str, Any]] = []
    values: dict[str, dict[str, Any]] = {}
    for name, path in {
        "runner_result": runner_result_path,
        "runner_completion": runner_completion_path,
        "runner_recovery": runner_recovery_path,
        "retry_policy_result": retry_policy_result_path,
        "retry_plan": retry_plan_path,
        "original_recovery": original_recovery_path,
        "trigger_plan": trigger_plan_path,
        "policy": policy_path,
    }.items():
        try:
            values[name] = load_json(path)
        except Exception as exc:
            values[name] = {}
            issues.append({
                "code": f"INVALID_{name.upper()}",
                "blocking": True,
                "detail": str(exc),
            })

    policy = values["policy"]
    if not policy:
        issues.append({
            "code": "RETRY_COMPLETION_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    for code, passed in (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        ("BROKER_WRITE_MUST_BE_DISABLED",
         not bool(policy.get("broker_write_enabled", True))),
        ("ORDER_SUBMISSION_MUST_BE_DISABLED",
         not bool(policy.get("order_submission_enabled", True))),
        ("LIVE_TRADING_MUST_BE_DISABLED",
         not bool(policy.get("live_trading_enabled", True))),
        ("EXTERNAL_NETWORK_MUST_BE_DISABLED",
         not bool(policy.get("external_network_enabled", True))),
    ):
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "retry cycle completion safety policy failed",
            })

    runner_result = values["runner_result"]
    runner_completion = values["runner_completion"]
    runner_recovery = values["runner_recovery"]
    retry_policy = values["retry_policy_result"]
    retry_plan = values["retry_plan"]
    original_recovery = values["original_recovery"]
    trigger_plan = values["trigger_plan"]

    attempts_used = int(retry_policy.get("attempts_used", 0) or 0)
    max_attempts = int(retry_policy.get("max_retry_attempts", 3) or 3)
    attempts_remaining = max(max_attempts - attempts_used, 0)
    budget_exhausted = attempts_used >= max_attempts

    runner_state = str(runner_result.get("state", ""))
    trigger_id = str(
        retry_plan.get(
            "trigger_id",
            original_recovery.get(
                "trigger_id",
                trigger_plan.get("trigger_id", ""),
            ),
        )
    )
    execution_id = str(
        runner_completion.get(
            "execution_id",
            runner_recovery.get(
                "execution_id",
                runner_result.get("execution_id", ""),
            ),
        )
    )

    state = "RETRY_CYCLE_WAIT_RUNNER_RESULT"
    status = "PASS"
    certificate_written = False
    ledger_written = False
    manual_intervention_required = False

    if any(item.get("blocking") for item in issues):
        state = "RETRY_CYCLE_SAFE_MODE"
        status = "BLOCKED"
    elif not runner_result:
        state = "RETRY_CYCLE_WAIT_RUNNER_RESULT"
    elif runner_state == "SUPERVISED_REENTRY_RUNNER_COMPLETED":
        state = "RETRY_CYCLE_COMPLETED"
    elif runner_state == "SUPERVISED_REENTRY_RUNNER_RECOVERY_REQUIRED":
        if budget_exhausted:
            state = "RETRY_CYCLE_BUDGET_EXHAUSTED"
            manual_intervention_required = True
        else:
            state = "RETRY_CYCLE_FAILED_RETRY_AVAILABLE"
    elif runner_state in {
        "SUPERVISED_REENTRY_RUNNER_WAIT_PLAN",
        "SUPERVISED_REENTRY_RUNNER_DRY_RUN_READY",
        "SUPERVISED_REENTRY_RUNNER_DRY_RUN_COMPLETE",
    }:
        state = "RETRY_CYCLE_WAIT_RUNNER_RESULT"
    else:
        state = "RETRY_CYCLE_UNRESOLVED"
        manual_intervention_required = True

    if finalize:
        finalizable_states = {
            "RETRY_CYCLE_COMPLETED",
            "RETRY_CYCLE_BUDGET_EXHAUSTED",
            "RETRY_CYCLE_FAILED_RETRY_AVAILABLE",
        }
        if state not in finalizable_states:
            issues.append({
                "code": "RETRY_CYCLE_NOT_FINALIZABLE",
                "blocking": True,
                "detail": state,
            })
            state = "RETRY_CYCLE_SAFE_MODE"
            status = "BLOCKED"
        else:
            cert_id = certificate_id(
                trigger_id,
                execution_id,
                observed_iso,
            )
            certificate = {
                "stage": "V83.56",
                "certificate_id": cert_id,
                "certificate_type": "RETRY_CYCLE_COMPLETION_CERTIFICATE",
                "state": state,
                "trigger_id": trigger_id,
                "retry_plan_id": str(retry_plan.get("retry_plan_id", "")),
                "execution_id": execution_id,
                "attempts_used": attempts_used,
                "attempts_remaining": attempts_remaining,
                "max_retry_attempts": max_attempts,
                "budget_exhausted": budget_exhausted,
                "manual_intervention_required": (
                    manual_intervention_required
                ),
                "runner_return_code": runner_result.get("return_code"),
                "runner_timed_out": bool(
                    runner_result.get("timed_out", False)
                ),
                "paper_only": True,
                "actual_paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "issued_at": observed_iso,
            }
            write_json(certificate_path, certificate)
            append_jsonl(completion_ledger_path, {
                **certificate,
                "event": "RETRY_CYCLE_FINALIZED",
            })
            certificate_written = True
            ledger_written = True

    dashboard = {
        "stage": "V83.56",
        "state": state,
        "status": status,
        "retry_cycle_completion_state": state,
        "finalize_requested": finalize,
        "trigger_id": trigger_id,
        "execution_id": execution_id,
        "attempts_used": attempts_used,
        "attempts_remaining": attempts_remaining,
        "max_retry_attempts": max_attempts,
        "budget_exhausted": budget_exhausted,
        "manual_intervention_required": manual_intervention_required,
        "certificate_written": certificate_written,
        "ledger_written": ledger_written,
        "operator_supervision_required": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "paper_only": True,
        "observed_at": observed_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "stage_range": "V83.53-V83.56",
        "implementation_type": (
            "RETRY_CYCLE_COMPLETION_AND_FINAL_CERTIFICATE"
        ),
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V83_57_FULL_SCHEDULE_TO_COMPLETION_ORCHESTRATOR"
            if status == "PASS"
            else "V83_53_TO_V83_56_RECOVER"
        ),
        "validation_mode": "LOCAL_RETRY_CYCLE_COMPLETION_ONLY",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
