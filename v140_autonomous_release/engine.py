from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from v140_autonomous_release.io import load_json,write_json,append_jsonl,digest
from v140_autonomous_release.integration import collect,summarize
from v140_autonomous_release.safety import evaluate as evaluate_safety
from v140_autonomous_release.certificate import build as build_certificate

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v140_final/input/v140_release_policy.json")
    sources=collect(root)
    summary=summarize(sources)
    safety=evaluate_safety(sources,policy)
    certificate=build_certificate(safety,summary)
    observed=datetime.now(timezone.utc).isoformat()

    state=(
        "V140_FINAL_AUTONOMOUS_RELEASE_COMPLETE"
        if safety.get("passed")
        else "V140_FINAL_AUTONOMOUS_RELEASE_REVIEW_REQUIRED"
    )
    body={
        "stage":"V140.00",
        "stage_range":"V121.01-V140.00",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "release_id":digest({"summary":summary,"policy":policy})[:24],
        "source_summary":summary,
        "safety_gate":safety,
        "release_certificate":certificate,
        "development_complete":safety.get("passed") is True,
        "paper_trading_ready":safety.get("passed") is True,
        "autonomous_paper_orchestrator_ready":safety.get("passed") is True,
        "web_controller_ready_for_development":safety.get("passed") is True,
        "live_trading_ready":False,
        "live_execution_authorized":False,
        "live_network_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V141_01_WEB_CONTROLLER_FOUNDATION",
    }
    body["result_sha256"]=digest(body)
    actual=root/"release/v140_final/actual"
    write_json(actual/"v140_final_release_result.json",body)
    write_json(actual/"v140_source_summary.json",summary)
    write_json(actual/"v140_safety_gate.json",safety)
    write_json(actual/"v140_completion_certificate.json",certificate)
    append_jsonl(actual/"v140_release_ledger.jsonl",{
        "observed_at":observed,
        "release_id":body["release_id"],
        "state":state,
        "development_complete":body["development_complete"],
        "actual_live_orders_submitted":0,
    })
    return body
