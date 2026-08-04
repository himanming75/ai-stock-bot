from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from continuous_autonomous_engine.io import (
    load_json,write_json,append_jsonl,digest
)
from continuous_autonomous_engine.source import (
    collect_sources,validate_sources
)
from continuous_autonomous_engine.session import select_next_session
from continuous_autonomous_engine.gates import evaluate_iteration_gates
from continuous_autonomous_engine.phases import initial_phases
from continuous_autonomous_engine.phase_executor import execute_phase
from continuous_autonomous_engine.checkpoint import save_checkpoint
from continuous_autonomous_engine.recovery import build_recovery
from continuous_autonomous_engine.state import resolve_state

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v104_01_to_v104_32/input/"
        "continuous_engine_policy.json"
    )
    actual_dir=root/"release/v104_01_to_v104_32/actual"
    sources=collect_sources(root)
    source_validation=validate_sources(sources)
    selected=select_next_session(sources["scheduler"])
    gates=evaluate_iteration_gates(sources,selected,policy)

    engine_id=digest({
        "scheduler_id":sources["scheduler"].get("scheduler_id"),
        "cycle_id":sources["cycle"].get("cycle_id"),
        "decision_id":sources["decision"].get("decision_id"),
        "selected_session_id":(
            (selected.get("session") or {}).get("session_id")
        ),
        "policy_version":policy.get("policy_version"),
    })[:24]

    context={
        "sources_valid":source_validation.get("passed") is True,
        "session_available":selected.get("session_available") is True,
        "cycle_valid":sources["cycle"].get("state") in {
            "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
            "AUTONOMOUS_CYCLE_HOLD",
            "AUTONOMOUS_CYCLE_REVIEW_REQUIRED",
            "AUTONOMOUS_CYCLE_BLOCKED",
        },
        "decision_valid":sources["decision"].get("status")=="PASS",
        "risk_rebalance_valid":(
            sources["risk"].get("pre_execution_gate",{}).get("passed") is True
            and sources["adaptive_rebalance"].get(
                "optimization_gate",{}
            ).get("passed") is True
        ),
        "paper_context_valid":(
            sources["decision"].get("execution_authorized",False) is False
            and sources["decision"].get("actual_orders_submitted",0)==0
        ),
        "checkpoint_enabled":policy.get("checkpoint_enabled") is True,
        "final_state_resolved":True,
    }

    phases=initial_phases()
    failed_phases=[]
    for index,phase in enumerate(phases):
        phases[index]=execute_phase(phase,context)
        if phases[index]["state"]!="COMPLETED":
            failed_phases.append(phases[index]["phase_id"])
            break

    resolved=resolve_state(
        source_validation,
        selected,
        gates,
        failed_phases,
        sources["cycle"].get("state"),
    )
    checkpoint=save_checkpoint(
        actual_dir/"continuous_engine_checkpoint.json",
        engine_id,
        selected,
        phases,
        resolved["state"],
    )
    recovery=build_recovery(
        source_validation,
        failed_phases,
        policy,
    )
    observed_at=datetime.now(timezone.utc).isoformat()

    body={
        "stage":"V104.32",
        "stage_range":"V104.01-V104.32",
        "state":resolved["state"],
        "status":"PASS",
        "observed_at":observed_at,
        "engine_id":engine_id,
        "engine_action":resolved["action"],
        "source_validation":source_validation,
        "selected_session":selected,
        "iteration_gates":gates,
        "phases":phases,
        "completed_phase_count":sum(
            1 for row in phases if row["state"]=="COMPLETED"
        ),
        "failed_phases":failed_phases,
        "checkpoint":checkpoint,
        "recovery":recovery,
        "iteration_count":1,
        "continuous_service_started":False,
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
        "continuous_loop_enabled":False,
        "windows_task_enabled":False,
        "next_phase":"V104_33_CONTINUOUS_SERVICE_RUNTIME",
    }
    body["continuous_engine_certificate_sha256"]=digest(body)

    write_json(
        actual_dir/"continuous_autonomous_engine_result.json",
        body,
    )
    append_jsonl(
        actual_dir/"continuous_autonomous_engine_ledger.jsonl",
        {
            "observed_at":observed_at,
            "engine_id":engine_id,
            "state":resolved["state"],
            "engine_action":resolved["action"],
            "selected_session_id":(
                (selected.get("session") or {}).get("session_id")
            ),
            "completed_phase_count":body["completed_phase_count"],
            "failed_phases":failed_phases,
            "recovery_required":recovery["recovery_required"],
            "checkpoint_generation":checkpoint["generation"],
            "actual_orders_submitted":0,
        },
    )
    return body
