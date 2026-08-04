from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from controlled_micro_live.io import load_json,write_json,append_jsonl
from controlled_micro_live.config import load
from controlled_micro_live.kill_switch import load as load_kill_switch
from controlled_micro_live.token import issue,inspect
from controlled_micro_live.dry_run import build as build_dry_run
from controlled_micro_live.reconcile import build_plan

def evaluate(root:Path)->dict[str,Any]:
    policy=load(root)
    qualification=load_json(root/"release/v161_01_to_v165_64/actual/paper_qualification_result.json")
    approval_result=load_json(root/"release/v166_01_to_v170_64/actual/live_read_only_approval_result.json")
    approval=load_json(root/"release/v166_01_to_v170_64/actual/live_approval_request.json")
    candidate=approval_result.get("selected_candidate",{})
    kill_switch=load_kill_switch(root)
    qualification_passed=qualification.get("qualification",{}).get("passed") is True
    approval_approved=approval.get("approved") is True
    qty=float(candidate.get("quantity",candidate.get("qty",0)) or 0)
    notional=float(candidate.get("estimated_notional",0) or 0)

    token=issue(root,candidate,approval,qualification_passed)
    token_status=inspect(root,candidate)
    checks={
        "qualification_passed":qualification_passed,
        "approval_approved":approval_approved,
        "candidate_present":bool(candidate),
        "quantity_exactly_one":qty==1,
        "notional_within_limit":0<notional<=policy["maximum_order_notional"],
        "kill_switch_clear":kill_switch.get("enabled") is False,
        "approval_token_valid":token_status.get("valid") is True,
        "dry_run_only":policy.get("dry_run_only") is True,
        "live_network_disabled":policy.get("live_network_enabled") is False,
        "live_write_disabled":policy.get("live_write_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    dry_run=build_dry_run(root,candidate,checks)
    reconciliation=build_plan(candidate)
    readiness=not failed
    state="CONTROLLED_MICRO_LIVE_DRY_RUN_READY" if readiness else "CONTROLLED_MICRO_LIVE_HARD_BLOCKED"
    result={
        "stage":"V175.64","state":state,"status":"PASS",
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "candidate":candidate,
        "policy":policy,
        "kill_switch":kill_switch,
        "approval_token":token,
        "approval_token_status":token_status,
        "readiness_gate":{"passed":readiness,"checks":checks,"failed":failed},
        "dry_run_receipt":dry_run,
        "broker_reconciliation_plan":reconciliation,
        "micro_live_execution_ready":False,
        "dry_run_ready":readiness,
        "execution_authorized":False,
        "live_network_enabled":False,
        "live_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_network_attempted":False,
        "actual_live_write_attempted":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V176_01_TO_V180_64_RESTRICTED_LIVE_AUTOMATION_REVIEW",
    }
    actual=root/"release/v171_01_to_v175_64/actual"
    write_json(actual/"controlled_micro_live_result.json",result)
    write_json(actual/"micro_live_readiness_gate.json",result["readiness_gate"])
    write_json(actual/"broker_reconciliation_plan.json",reconciliation)
    append_jsonl(actual/"controlled_micro_live_audit_ledger.jsonl",{
        "observed_at":result["observed_at"],"state":state,
        "readiness_passed":readiness,"execution_authorized":False,
        "actual_live_orders_submitted":0,
    })
    return result
