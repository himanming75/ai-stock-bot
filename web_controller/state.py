from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from web_controller.io import load_json,write_json,tail_jsonl

RESULTS={
    "v140":"release/v140_final/actual/v140_final_release_result.json",
    "paper":"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json",
    "shadow":"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json",
    "risk":"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json",
    "orchestrator":"release/v137_01_to_v139_64/actual/autonomous_orchestrator_result.json",
}

def emergency_path(root:Path)->Path:
    return root/"release/v141_01_to_v145_64/control/emergency_stop.json"

def get_emergency(root:Path)->dict[str,Any]:
    value=load_json(emergency_path(root))
    if not value:
        value={
            "enabled":True,
            "reason":"DEFAULT_SAFE_START",
            "updated_at":datetime.now(timezone.utc).isoformat(),
        }
        write_json(emergency_path(root),value)
    return value

def set_emergency(root:Path,enabled:bool,reason:str)->dict[str,Any]:
    value={
        "enabled":enabled,
        "reason":reason or ("MANUAL_STOP" if enabled else "MANUAL_CLEAR"),
        "updated_at":datetime.now(timezone.utc).isoformat(),
    }
    write_json(emergency_path(root),value)
    return value

def build_dashboard(root:Path)->dict[str,Any]:
    values={name:load_json(root/path) for name,path in RESULTS.items()}
    paper=values["paper"]
    orchestrator=values["orchestrator"]
    risk=values["risk"]
    emergency=get_emergency(root)
    return {
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "release":{
            "state":values["v140"].get("state","NOT_AVAILABLE"),
            "development_complete":values["v140"].get("development_complete",False),
            "paper_trading_ready":values["v140"].get("paper_trading_ready",False),
            "live_trading_ready":values["v140"].get("live_trading_ready",False),
        },
        "paper_account":paper.get("account_snapshot",{}),
        "paper_positions":paper.get("position_snapshot",[]),
        "paper_orders":paper.get("order_snapshot",[]),
        "market_open":paper.get("clock_snapshot",{}).get("is_open"),
        "shadow":{
            "state":values["shadow"].get("state","NOT_AVAILABLE"),
            "signal_count":len(values["shadow"].get("signals",[])),
            "plan_count":len(values["shadow"].get("paper_order_plans",[])),
            "qualification":values["shadow"].get("qualification",{}),
        },
        "risk":{
            "state":risk.get("state","NOT_AVAILABLE"),
            "gate":risk.get("risk_gate",{}),
            "sizing":risk.get("dynamic_sizing",{}),
            "loss_limits":risk.get("loss_limits",{}),
        },
        "orchestrator":{
            "state":orchestrator.get("state","NOT_AVAILABLE"),
            "cycle_id":orchestrator.get("cycle_id"),
            "signal_count":len(orchestrator.get("signals",[])),
            "candidate_count":len(orchestrator.get("selected_candidates",[])),
            "paper_orders_submitted":orchestrator.get("actual_paper_orders_submitted",0),
            "live_orders_submitted":orchestrator.get("actual_live_orders_submitted",0),
            "performance":orchestrator.get("performance",{}),
        },
        "emergency_stop":emergency,
        "safety":{
            "live_network_enabled":False,
            "live_submission_enabled":False,
            "actual_live_orders_submitted":0,
            "local_bind_only":True,
        },
    }

def get_logs(root:Path)->dict[str,Any]:
    return {
        "v140_release":tail_jsonl(root/"release/v140_final/actual/v140_release_ledger.jsonl"),
        "paper_operations":tail_jsonl(root/"release/v121_01_to_v123_64/actual/alpaca_paper_audit_ledger.jsonl"),
        "shadow_cycles":tail_jsonl(root/"release/v124_01_to_v126_64/actual/continuous_paper_session_ledger.jsonl"),
        "risk":tail_jsonl(root/"release/v134_01_to_v136_64/actual/dynamic_live_risk_ledger.jsonl"),
        "autonomous_cycles":tail_jsonl(root/"release/v137_01_to_v139_64/actual/autonomous_cycle_ledger.jsonl"),
    }
