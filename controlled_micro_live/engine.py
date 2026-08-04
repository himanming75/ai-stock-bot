from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from controlled_micro_live.io import load_json,write_json,append_jsonl,digest
from controlled_micro_live.approval import build_approval
from controlled_micro_live.token import issue_simulated_token
from controlled_micro_live.kill_switch import evaluate as evaluate_kill_switch
from controlled_micro_live.payload import build_payload
from controlled_micro_live.simulator import simulate
from controlled_micro_live.review import evaluate as evaluate_review

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v131_01_to_v133_64/input/controlled_micro_live_policy.json")
    source=load_json(root/"release/v129_01_to_v130_64/actual/restricted_live_candidate_result.json")
    actual=root/"release/v131_01_to_v133_64/actual"

    ready=source.get("state") in {
        "RESTRICTED_AUTOMATIC_LIVE_CANDIDATE_READY",
        "RESTRICTED_AUTOMATIC_LIVE_CANDIDATE_REVIEW_REQUIRED",
    }
    candidates=source.get("restricted_live_candidates",[]) if ready else []
    candidate=candidates[0] if candidates else {}

    if not ready:
        body={
            "stage":"V133.64","stage_range":"V131.01-V133.64",
            "state":"CONTROLLED_MICRO_LIVE_SOURCE_REQUIRED","status":"PASS",
            "actual_live_orders_submitted":0,
            "next_phase":"V134_01_TO_V136_64_DYNAMIC_LIVE_RISK_ENGINE",
        }
        body["result_sha256"]=digest(body)
        write_json(actual/"controlled_micro_live_result.json",body)
        return body

    approval=build_approval(candidate,policy) if candidate else {}
    token=issue_simulated_token(approval,policy) if approval else {
        "token_present":False,"token_valid":False,"token_used":False,
        "token_single_use":True,"token_expired":False,
        "token_replay_detected":False,"live_token":False,
        "simulation_only":True,
    }
    kill_switch=evaluate_kill_switch(policy,candidate) if candidate else {
        "passed":False,"checks":{},"failed":["candidate_missing"],
        "state":"KILL_SWITCH_BLOCKED",
    }
    payload=build_payload(candidate) if candidate else {}
    simulation=simulate(payload,policy) if payload else {
        "simulated_status":"not_run",
        "actual_broker_request_sent":False,
        "actual_live_order_submitted":False,
    }
    review=evaluate_review(
        candidate,approval,token,kill_switch,payload,simulation,policy
    )

    state=(
        "CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW_COMPLETE"
        if candidate and review.get("passed")
        else "CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    certificate={
        "certificate_type":"CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW",
        "issued_at":observed,
        "candidate_id":candidate.get("candidate_id"),
        "review_passed":review.get("passed"),
        "execution_authorized":False,
        "actual_live_orders_submitted":0,
    }
    certificate["certificate_sha256"]=digest(certificate)
    body={
        "stage":"V133.64","stage_range":"V131.01-V133.64",
        "state":state,"status":"PASS","observed_at":observed,
        "review_id":digest({
            "candidate":candidate,
            "policy_version":policy.get("policy_version"),
        })[:24],
        "source_readiness_id":source.get("readiness_id"),
        "candidate":candidate,
        "manual_approval_request":approval,
        "approval_token_status":token,
        "kill_switch":kill_switch,
        "live_order_payload_review":payload,
        "execution_simulation":simulation,
        "execution_review":review,
        "review_certificate":certificate,
        "two_step_manual_approval_required":True,
        "first_approval_granted":False,
        "second_approval_granted":False,
        "live_approval_token_issued":False,
        "live_network_enabled":False,
        "live_submission_enabled":False,
        "real_live_network_attempted":False,
        "real_live_submission_attempted":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V134_01_TO_V136_64_DYNAMIC_LIVE_RISK_ENGINE",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"controlled_micro_live_result.json",body)
    write_json(actual/"manual_approval_request.json",approval)
    write_json(actual/"approval_token_status.json",token)
    write_json(actual/"kill_switch_report.json",kill_switch)
    write_json(actual/"live_order_payload_review.json",payload)
    write_json(actual/"execution_simulation.json",simulation)
    write_json(actual/"execution_review_certificate.json",certificate)
    append_jsonl(actual/"approval_ledger.jsonl",{
        "observed_at":observed,
        "candidate_id":candidate.get("candidate_id"),
        "first_approval_granted":False,
        "second_approval_granted":False,
    })
    append_jsonl(actual/"token_ledger.jsonl",{
        "observed_at":observed,
        "token_present":token.get("token_present"),
        "live_token":False,
        "token_used":token.get("token_used"),
    })
    append_jsonl(actual/"execution_review_ledger.jsonl",{
        "observed_at":observed,
        "review_id":body["review_id"],
        "state":state,
        "actual_live_orders_submitted":0,
    })
    return body
