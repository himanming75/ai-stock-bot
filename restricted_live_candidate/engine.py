from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from restricted_live_candidate.io import load_json,write_json,append_jsonl,digest
from restricted_live_candidate.account import normalize_account,normalize_positions,normalize_orders
from restricted_live_candidate.candidates import build
from restricted_live_candidate.gate import evaluate as evaluate_gate
from restricted_live_candidate.reconcile import compare
from restricted_live_candidate.gateway import evaluate as evaluate_gateway

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v129_01_to_v130_64/input/restricted_live_candidate_policy.json")
    fixture=load_json(root/"release/v129_01_to_v130_64/input/live_readonly_fixture.json")
    source=load_json(root/"release/v127_01_to_v128_64/actual/micro_live_readiness_result.json")
    actual=root/"release/v129_01_to_v130_64/actual"

    ready=source.get("state") in {
        "MICRO_LIVE_MANUAL_APPROVAL_READINESS_READY",
        "MICRO_LIVE_READINESS_REVIEW_REQUIRED",
    }
    if not ready:
        body={
            "stage":"V130.64","stage_range":"V129.01-V130.64",
            "state":"RESTRICTED_LIVE_CANDIDATE_SOURCE_REQUIRED","status":"PASS",
            "actual_live_orders_submitted":0,
            "next_phase":"V131_CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW",
        }
        body["result_sha256"]=digest(body)
        write_json(actual/"restricted_live_candidate_result.json",body)
        return body

    account=normalize_account(fixture.get("account",{}))
    positions=normalize_positions(fixture.get("positions",[]))
    orders=normalize_orders(fixture.get("orders",[]))
    candidates=build(source)
    reconciliation=compare(candidates,positions,orders)
    gate=evaluate_gate(candidates,account,positions,orders,policy)
    gateway=evaluate_gateway(gate,policy)

    state=(
        "RESTRICTED_AUTOMATIC_LIVE_CANDIDATE_READY"
        if gate.get("passed") and reconciliation.get("passed")
        else "RESTRICTED_AUTOMATIC_LIVE_CANDIDATE_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V130.64","stage_range":"V129.01-V130.64",
        "state":state,"status":"PASS","observed_at":observed,
        "readiness_id":digest({
            "source":source.get("readiness_id"),
            "account":account,"candidates":candidates,
        })[:24],
        "source_readiness_id":source.get("readiness_id"),
        "live_account_snapshot":account,
        "live_position_snapshot":positions,
        "live_order_snapshot":orders,
        "restricted_live_candidates":candidates,
        "reconciliation":reconciliation,
        "restricted_gate":gate,
        "live_gateway":gateway,
        "real_live_network_attempted":False,
        "real_live_read_only_snapshot_fetched":False,
        "fixture_live_snapshot_used":True,
        "live_network_write_enabled":False,
        "live_submission_enabled":False,
        "manual_approval_complete":False,
        "approval_token_valid":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V131_CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"restricted_live_candidate_result.json",body)
    write_json(actual/"live_account_snapshot.json",account)
    write_json(actual/"restricted_candidate_gate.json",gate)
    write_json(actual/"live_candidate_reconciliation.json",reconciliation)
    write_json(actual/"live_gateway_report.json",gateway)
    append_jsonl(actual/"restricted_live_candidate_audit_ledger.jsonl",{
        "observed_at":observed,
        "readiness_id":body["readiness_id"],
        "state":state,
        "candidate_count":len(candidates),
        "eligible_count":gate.get("eligible_count"),
        "actual_live_orders_submitted":0,
    })
    return body
