from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from final_system_integration.io import load_json,write_json,append_jsonl,digest
from final_system_integration.registry import collect
from final_system_integration.pipeline import build_pipeline
from final_system_integration.safety import evaluate_safety
from final_system_integration.readiness import calculate_readiness
from final_system_integration.checkpoint import save_checkpoint
from final_system_integration.dashboard import build_dashboard

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v105_01_to_v105_32/input/"
        "final_integration_policy.json"
    )
    actual_dir=root/"release/v105_01_to_v105_32/actual"

    modules=collect(root)
    pipeline=build_pipeline(modules)
    safety=evaluate_safety(modules)
    readiness=calculate_readiness(modules,pipeline,safety)

    integration_id=digest({
        "modules":[
            {"module_id":row["module_id"],"state":row["state"],"ready":row["ready"]}
            for row in modules
        ],
        "policy_version":policy.get("policy_version"),
    })[:24]
    checkpoint=save_checkpoint(
        actual_dir/"final_integration_checkpoint.json",
        integration_id,
        readiness,
        pipeline,
    )
    dashboard=build_dashboard(modules,pipeline,safety,readiness)

    state=(
        "FINAL_SYSTEM_INTEGRATION_READY"
        if readiness["passed"]
        else "FINAL_SYSTEM_INTEGRATION_REVIEW_REQUIRED"
    )
    observed_at=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V105.32",
        "stage_range":"V105.01-V105.32",
        "state":state,
        "status":"PASS",
        "observed_at":observed_at,
        "integration_id":integration_id,
        "module_registry":modules,
        "pipeline":pipeline,
        "safety":safety,
        "readiness":readiness,
        "dashboard_snapshot":dashboard,
        "checkpoint":checkpoint,
        "final_release_eligible":readiness["passed"],
        "production_release_created":False,
        "approval_granted":False,
        "execution_authorized":False,
        "manual_approval_required":True,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "actual_orders_submitted":0,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "paper_only":True,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "background_service_running":False,
        "windows_task_enabled":False,
        "next_phase":"V105_33_PRODUCTION_READINESS_FINAL_RELEASE",
    }
    body["final_integration_certificate_sha256"]=digest(body)

    write_json(actual_dir/"final_system_integration_result.json",body)
    write_json(actual_dir/"final_integration_dashboard_snapshot.json",dashboard)
    append_jsonl(
        actual_dir/"final_system_integration_ledger.jsonl",
        {
            "observed_at":observed_at,
            "integration_id":integration_id,
            "state":state,
            "readiness_score":readiness["readiness_score"],
            "ready_module_count":readiness["ready_module_count"],
            "module_count":readiness["module_count"],
            "pipeline_ready_steps":pipeline["ready_steps"],
            "pipeline_total_steps":pipeline["total_steps"],
            "safety_passed":safety["passed"],
            "final_release_eligible":readiness["passed"],
            "actual_orders_submitted":0,
        },
    )
    return body
