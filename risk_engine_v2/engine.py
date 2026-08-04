from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from risk_engine_v2.io import load_json,write_json,append_jsonl
from risk_engine_v2.config import load
from risk_engine_v2.kill_switch import load as load_kill
from risk_engine_v2.gate import evaluate as eval_gate

def evaluate(root:Path)->dict:
    policy=load(root)
    state=load_json(root/"release/v206_01_to_v210_64/input/risk_state.json")
    candidate=load_json(root/"release/v206_01_to_v210_64/input/risk_candidate.json")
    kill=load_kill(root)
    gate=eval_gate(policy,state,candidate,kill)
    state_name="RISK_ENGINE_V2_READY" if gate["passed"] else "RISK_ENGINE_V2_HARD_BLOCKED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
      "stage":"V210.64",
      "state":state_name,
      "status":"PASS",
      "observed_at":observed,
      "policy":policy,
      "risk_state":state,
      "candidate":candidate,
      "kill_switch":kill,
      "risk_gate":gate,
      "trading_allowed":gate["passed"],
      "execution_authorized":False,
      "broker_write_enabled":False,
      "live_submission_enabled":False,
      "actual_live_orders_submitted":0,
      "next_phase":"V211_01_TO_V215_64_AI_STRATEGY_ENSEMBLE",
    }
    actual=root/"release/v206_01_to_v210_64/actual"
    write_json(actual/"risk_engine_v2_result.json",result)
    write_json(actual/"risk_engine_v2_gate.json",gate)
    append_jsonl(actual/"risk_engine_v2_audit_ledger.jsonl",{
      "observed_at":observed,"state":state_name,
      "gate_passed":gate["passed"],
      "drawdown_pct":gate["metrics"]["drawdown_pct"],
      "daily_loss_pct":gate["metrics"]["daily_loss_pct"],
      "actual_live_orders_submitted":0,
    })
    return result
