from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from micro_live_readiness.io import load_json,write_json,append_jsonl,digest
from micro_live_readiness.candidates import build_candidates
from micro_live_readiness.limits import evaluate_all
from micro_live_readiness.approval import create_request,evaluate_request
from micro_live_readiness.token import inspect_token
from micro_live_readiness.gateway import evaluate_gateway
from micro_live_readiness.shadow_compare import compare

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v127_01_to_v128_64/input/micro_live_readiness_policy.json")
    source=load_json(root/"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json")
    actual=root/"release/v127_01_to_v128_64/actual"

    ready=source.get("state") in {
        "CONTINUOUS_PAPER_SHADOW_OFFLINE_READY",
        "CONTINUOUS_REAL_PAPER_SHADOW_READY",
        "CONTINUOUS_REAL_PAPER_CYCLE_SUBMITTED",
    }
    if not ready:
        body={
            "stage":"V128.64","stage_range":"V127.01-V128.64",
            "state":"MICRO_LIVE_READINESS_SOURCE_REQUIRED","status":"PASS",
            "actual_live_orders_submitted":0,"paper_only":True,
            "next_phase":"V129_RESTRICTED_AUTOMATIC_LIVE_CANDIDATE",
        }
        body["result_sha256"]=digest(body)
        write_json(actual/"micro_live_readiness_result.json",body)
        return body

    candidates=build_candidates(source,policy)
    limits=evaluate_all(candidates,policy)
    request=create_request(candidates,limits,policy)
    approval=evaluate_request(request)
    token=inspect_token(policy)
    gateway=evaluate_gateway(limits,approval,token,policy)
    comparison=compare(candidates,policy)

    state=(
        "MICRO_LIVE_MANUAL_APPROVAL_READINESS_READY"
        if candidates and limits.get("passed")
        else "MICRO_LIVE_READINESS_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V128.64","stage_range":"V127.01-V128.64",
        "state":state,"status":"PASS","observed_at":observed,
        "readiness_id":digest({
            "source_cycle":source.get("cycle_id"),
            "candidates":candidates,
            "policy_version":policy.get("policy_version"),
        })[:24],
        "source_cycle_id":source.get("cycle_id"),
        "live_order_candidates":candidates,
        "micro_live_limits":limits,
        "manual_approval_request":request,
        "manual_approval_status":approval,
        "approval_token_status":token,
        "live_gateway":gateway,
        "paper_vs_live_shadow_comparison":comparison,
        "two_step_manual_approval_required":True,
        "first_approval_granted":False,
        "second_approval_granted":False,
        "approval_token_issued":False,
        "live_network_enabled":False,
        "live_submission_enabled":False,
        "real_live_network_attempted":False,
        "real_live_submission_attempted":False,
        "actual_paper_orders_submitted":0,
        "actual_live_orders_submitted":0,
        "paper_only":True,
        "micro_live_ready_for_future_controlled_test":state=="MICRO_LIVE_MANUAL_APPROVAL_READINESS_READY",
        "next_phase":"V129_RESTRICTED_AUTOMATIC_LIVE_CANDIDATE",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"micro_live_readiness_result.json",body)
    write_json(actual/"live_order_candidates.json",{"candidates":candidates})
    write_json(actual/"micro_live_limit_report.json",limits)
    write_json(actual/"manual_approval_request.json",request)
    write_json(actual/"live_gateway_report.json",gateway)
    write_json(actual/"paper_vs_live_shadow_comparison.json",comparison)
    append_jsonl(actual/"micro_live_readiness_audit_ledger.jsonl",{
        "observed_at":observed,"readiness_id":body["readiness_id"],
        "state":state,"candidate_count":len(candidates),
        "eligible_count":limits.get("eligible_count"),
        "approval_token_issued":False,
        "actual_live_orders_submitted":0,
    })
    return body
