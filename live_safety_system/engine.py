from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from live_safety_system.io import (
    load_json,write_json,append_jsonl,digest
)
from live_safety_system.kill_switch import evaluate_kill_switch
from live_safety_system.loss_limits import evaluate_loss_limits
from live_safety_system.exposure import evaluate_exposure
from live_safety_system.anomaly import detect_anomalies
from live_safety_system.emergency import build_emergency_action
from live_safety_system.resume import build_resume_gate
from live_safety_system.certificate import build_certificate

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v117_01_to_v119_64/input/"
        "live_safety_policy.json"
    )
    telemetry=load_json(
        root/"release/v117_01_to_v119_64/input/"
        "safety_telemetry_fixture.json"
    )
    execution=load_json(
        root/"release/v114_01_to_v116_64/actual/"
        "broker_safe_execution_result.json"
    )
    actual_dir=root/"release/v117_01_to_v119_64/actual"

    source_ready=(
        execution.get("state")
        =="BROKER_INTEGRATION_SAFE_EXECUTION_BOUNDARY_READY"
    )
    if not source_ready:
        body={
            "stage":"V119.64",
            "stage_range":"V117.01-V119.64",
            "state":"LIVE_SAFETY_SYSTEM_SOURCE_REQUIRED",
            "status":"PASS",
            "actual_orders_submitted":0,
            "paper_only":True,
            "live_trading_enabled":False,
            "next_phase":"V120_FINAL_PRODUCTION_RELEASE",
        }
        body["certificate_sha256"]=digest(body)
        write_json(actual_dir/"live_safety_system_result.json",body)
        return body

    kill_switch=evaluate_kill_switch(policy,telemetry)
    loss_limits=evaluate_loss_limits(policy,telemetry)
    exposure=evaluate_exposure(policy,execution,telemetry)
    anomaly=detect_anomalies(policy,telemetry)
    emergency=build_emergency_action(
        kill_switch,loss_limits,exposure,anomaly
    )
    resume=build_resume_gate(emergency,telemetry)
    safety_passed=(
        not kill_switch.get("triggered")
        and loss_limits.get("passed")
        and exposure.get("passed")
        and anomaly.get("passed")
        and not emergency.get("emergency_shutdown_required")
    )
    state=(
        "LIVE_SAFETY_SYSTEM_READY"
        if safety_passed
        else "LIVE_SAFETY_SYSTEM_EMERGENCY_BLOCKED"
    )
    certificate=build_certificate(
        safety_passed,kill_switch,emergency,resume
    )
    observed_at=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V119.64",
        "stage_range":"V117.01-V119.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed_at,
        "safety_assessment_id":digest({
            "execution_package_id":execution.get("execution_package_id"),
            "telemetry":telemetry,
            "policy_version":policy.get("policy_version"),
        })[:24],
        "source_execution_package_id":execution.get(
            "execution_package_id"
        ),
        "kill_switch":kill_switch,
        "loss_limits":loss_limits,
        "exposure":exposure,
        "anomaly_detection":anomaly,
        "emergency_action":emergency,
        "resume_gate":resume,
        "safety_certificate":certificate,
        "safety_passed":safety_passed,
        "manual_approval_required":True,
        "approval_granted":False,
        "approval_token_issued":False,
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "emergency_cancel_requests_executed":0,
        "emergency_flatten_requests_executed":0,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "actual_orders_submitted":0,
        "paper_only":True,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "next_phase":"V120_FINAL_PRODUCTION_RELEASE",
    }
    body["certificate_sha256"]=digest(body)
    write_json(actual_dir/"live_safety_system_result.json",body)
    write_json(actual_dir/"kill_switch_report.json",kill_switch)
    write_json(actual_dir/"loss_limit_report.json",loss_limits)
    write_json(actual_dir/"exposure_limit_report.json",exposure)
    write_json(actual_dir/"anomaly_report.json",anomaly)
    write_json(actual_dir/"emergency_action_report.json",emergency)
    write_json(actual_dir/"resume_gate_report.json",resume)
    write_json(actual_dir/"live_safety_certificate.json",certificate)
    append_jsonl(
        actual_dir/"live_safety_audit_ledger.jsonl",
        {
            "observed_at":observed_at,
            "safety_assessment_id":body["safety_assessment_id"],
            "state":state,
            "safety_passed":safety_passed,
            "kill_switch_triggered":kill_switch.get("triggered"),
            "emergency_shutdown_required":emergency.get(
                "emergency_shutdown_required"
            ),
            "resume_allowed":resume.get("resume_allowed"),
            "actual_orders_submitted":0,
        },
    )
    return body
