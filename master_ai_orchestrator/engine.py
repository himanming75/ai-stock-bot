from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from master_ai_orchestrator.io import load_json, write_json, append_jsonl, digest
from master_ai_orchestrator.registry import collect_modules
from master_ai_orchestrator.dependencies import evaluate_dependencies
from master_ai_orchestrator.workflow import build_workflow
from master_ai_orchestrator.safety import evaluate_safety
from master_ai_orchestrator.health import evaluate_health
from master_ai_orchestrator.checkpoint import build_checkpoint
from master_ai_orchestrator.recovery import build_recovery_plan

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v102_01_to_v102_32/input/"
        "master_orchestrator_policy.json"
    )
    modules = collect_modules(root)
    dependencies = evaluate_dependencies(modules)
    workflow = build_workflow(modules)
    safety = evaluate_safety(modules)
    health = evaluate_health(modules, dependencies, workflow, safety)
    recovery = build_recovery_plan(modules, policy)

    state = (
        "MASTER_AI_ORCHESTRATOR_READY"
        if health["passed"]
        else "MASTER_AI_ORCHESTRATOR_REVIEW_REQUIRED"
    )
    observed_at = datetime.now(timezone.utc).isoformat()
    orchestration_id = digest({
        "modules": modules,
        "policy": policy,
        "workflow_order": workflow["workflow_order"],
    })[:24]
    checkpoint = build_checkpoint(root, orchestration_id, workflow)

    body = {
        "stage": "V102.32",
        "stage_range": "V102.01-V102.32",
        "state": state,
        "status": "PASS",
        "observed_at": observed_at,
        "orchestration_id": orchestration_id,
        "module_registry": modules,
        "dependency_graph": dependencies,
        "workflow": workflow,
        "health": health,
        "safety_lock": safety,
        "recovery_plan": recovery,
        "checkpoint": checkpoint,
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
        "next_phase": "V102_33_AUTONOMOUS_DECISION_ENGINE",
    }
    body["master_orchestrator_certificate_sha256"] = digest(body)

    write_json(
        root / "release/v102_01_to_v102_32/actual/"
        "master_ai_orchestrator_result.json",
        body,
    )
    append_jsonl(
        root / "release/v102_01_to_v102_32/actual/"
        "master_ai_orchestrator_ledger.jsonl",
        {
            "observed_at": observed_at,
            "orchestration_id": orchestration_id,
            "state": state,
            "ready_module_count": health["ready_module_count"],
            "required_module_count": health["required_module_count"],
            "module_readiness_pct": health["module_readiness_pct"],
            "workflow_passed": workflow["passed"],
            "safety_passed": safety["passed"],
            "recovery_required": recovery["recovery_required"],
            "checkpoint_generation": checkpoint["generation"],
        },
    )
    return body
