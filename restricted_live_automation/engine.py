from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from restricted_live_automation.io import load_json,write_json,append_jsonl,digest
from restricted_live_automation.config import load
from restricted_live_automation.gate import evaluate as eval_gate
from restricted_live_automation.plan import build as build_plan

def evaluate(root:Path)->dict[str,Any]:
    policy=load(root)
    qualification=load_json(root/"release/v161_01_to_v165_64/actual/paper_qualification_result.json")
    micro=load_json(root/"release/v171_01_to_v175_64/actual/controlled_micro_live_result.json")
    candidate=micro.get("candidate",{})
    gate=eval_gate(policy,qualification,micro,candidate)
    plan=build_plan(candidate,gate)
    state="RESTRICTED_LIVE_AUTOMATION_DRY_RUN_READY" if gate["passed"] else "RESTRICTED_LIVE_AUTOMATION_HARD_BLOCKED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
      "stage":"V180.64",
      "state":state,
      "status":"PASS",
      "observed_at":observed,
      "review_id":digest({"candidate":candidate,"gate":gate})[:24],
      "policy":policy,
      "candidate":candidate,
      "qualification_state":qualification.get("state","NOT_AVAILABLE"),
      "micro_live_state":micro.get("state","NOT_AVAILABLE"),
      "restricted_gate":gate,
      "automation_plan":plan,
      "restricted_automation_ready":gate["passed"],
      "execution_authorized":False,
      "automatic_submission_enabled":False,
      "live_network_enabled":False,
      "live_write_enabled":False,
      "live_submission_enabled":False,
      "actual_live_network_attempted":False,
      "actual_live_write_attempted":False,
      "actual_live_orders_submitted":0,
      "next_phase":"V181_01_TO_V185_64_PORTFOLIO_AND_BROKER_ADAPTER_FOUNDATION"
    }
    actual=root/"release/v176_01_to_v180_64/actual"
    write_json(actual/"restricted_live_automation_result.json",result)
    write_json(actual/"restricted_live_automation_gate.json",gate)
    write_json(actual/"restricted_live_automation_plan.json",plan)
    append_jsonl(actual/"restricted_live_automation_audit_ledger.jsonl",{
      "observed_at":observed,"state":state,
      "gate_passed":gate["passed"],
      "execution_authorized":False,
      "actual_live_orders_submitted":0
    })
    return result
