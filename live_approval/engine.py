from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from live_approval.io import load_json,write_json,append_jsonl
from live_approval.config import load
from live_approval.credentials import inspect
from live_approval.snapshot import build as build_snapshot
from live_approval.comparison import compare
from live_approval.approval import create

def evaluate(root:Path)->dict[str,Any]:
    policy=load(root)
    credentials=inspect()
    qualification=load_json(root/"release/v161_01_to_v165_64/actual/paper_qualification_result.json")
    paper=load_json(root/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json")
    candidate=load_json(root/"release/v129_01_to_v130_64/actual/restricted_live_candidate_result.json")
    live=build_snapshot(root)
    paper_account=paper.get("account_snapshot",{})
    comparison=compare(paper_account,live.get("account",{}))
    candidates=candidate.get("restricted_live_candidates",[])
    selected=candidates[0] if candidates else {}
    approval=create(root,selected,qualification)
    qpassed=qualification.get("qualification",{}).get("passed") is True
    state="LIVE_READ_ONLY_APPROVAL_READY" if qpassed and approval.get("eligible_for_review") else "LIVE_READ_ONLY_APPROVAL_BLOCKED"
    result={
        "stage":"V170.64","state":state,"status":"PASS",
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "policy":policy,
        "credentials":credentials,
        "qualification_state":qualification.get("state","NOT_AVAILABLE"),
        "qualification_passed":qpassed,
        "paper_account":paper_account,
        "live_read_only_snapshot":live,
        "paper_live_comparison":comparison,
        "selected_candidate":selected,
        "approval_request":approval,
        "live_read_only_enabled":policy.get("live_read_only_enabled") is True,
        "actual_live_network_attempted":False,
        "actual_live_write_attempted":False,
        "execution_authorized":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V171_01_TO_V175_64_CONTROLLED_MICRO_LIVE",
    }
    actual=root/"release/v166_01_to_v170_64/actual"
    write_json(actual/"live_read_only_approval_result.json",result)
    write_json(actual/"live_read_only_snapshot.json",live)
    write_json(actual/"paper_live_comparison.json",comparison)
    append_jsonl(actual/"live_readonly_audit_ledger.jsonl",{
        "observed_at":result["observed_at"],"state":state,
        "qualification_passed":qpassed,
        "actual_live_network_attempted":False,
        "actual_live_orders_submitted":0,
    })
    return result
