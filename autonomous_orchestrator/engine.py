from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from autonomous_orchestrator.io import load_json,write_json,append_jsonl,digest
from autonomous_orchestrator.market import inspect
from autonomous_orchestrator.scanner import scan
from autonomous_orchestrator.selector import select
from autonomous_orchestrator.planner import build as build_plans
from autonomous_orchestrator.execution import simulate
from autonomous_orchestrator.positions import apply
from autonomous_orchestrator.performance import summarize
from autonomous_orchestrator.checkpoint import build as build_checkpoint

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v137_01_to_v139_64/input/autonomous_orchestrator_policy.json")
    fixture=load_json(root/"release/v137_01_to_v139_64/input/autonomous_orchestrator_fixture.json")
    risk=load_json(root/"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json")
    actual=root/"release/v137_01_to_v139_64/actual"
    previous=load_json(actual/"autonomous_checkpoint.json")

    source_ready=risk.get("state") in {
        "DYNAMIC_LIVE_RISK_ENGINE_READY",
        "DYNAMIC_LIVE_RISK_REVIEW_REQUIRED",
    }
    if not source_ready:
        body={
            "stage":"V139.64","stage_range":"V137.01-V139.64",
            "state":"AUTONOMOUS_ORCHESTRATOR_SOURCE_REQUIRED","status":"PASS",
            "actual_live_orders_submitted":0,
            "next_phase":"V140_FINAL_AUTONOMOUS_RELEASE",
        }
        body["result_sha256"]=digest(body)
        write_json(actual/"autonomous_orchestrator_result.json",body)
        return body

    market=inspect(fixture)
    signals=scan(fixture,policy)
    candidates=select(signals,policy)
    risk_passed=risk.get("risk_gate",{}).get("passed") is True
    plans=build_plans(candidates,risk) if risk_passed else []

    cycle_id=digest({
        "session_date":fixture.get("session_date"),
        "market":market,
        "candidates":candidates,
        "risk_id":risk.get("risk_assessment_id"),
    })[:24]
    duplicate=previous.get("cycle_id")==cycle_id
    execution=simulate(plans,market.get("market_open",False),policy) if not duplicate else {
        "paper_execution_authorized":False,
        "paper_orders_submitted":0,
        "paper_fills":[],
        "actual_live_orders_submitted":0,
        "live_submission_attempted":False,
    }
    positions=apply(execution.get("paper_fills",[]))
    performance=summarize(float(fixture.get("account",{}).get("equity",0)),positions)

    if duplicate:
        state="AUTONOMOUS_TRADING_DUPLICATE_CYCLE_BLOCKED"
    elif not market.get("market_open"):
        state="AUTONOMOUS_TRADING_MARKET_CLOSED"
    elif not candidates:
        state="AUTONOMOUS_TRADING_NO_SIGNAL"
    elif not risk_passed:
        state="AUTONOMOUS_TRADING_RISK_BLOCKED"
    elif execution.get("paper_orders_submitted",0)>0:
        state="AUTONOMOUS_PAPER_TRADING_CYCLE_COMPLETE"
    else:
        state="AUTONOMOUS_TRADING_READY_NO_EXECUTION"

    checkpoint=build_checkpoint(cycle_id,state,positions,previous)
    write_json(actual/"autonomous_checkpoint.json",checkpoint)

    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V139.64","stage_range":"V137.01-V139.64",
        "state":state,"status":"PASS","observed_at":observed,
        "cycle_id":cycle_id,
        "duplicate_cycle":duplicate,
        "market":market,
        "signals":signals,
        "selected_candidates":candidates,
        "risk_source_state":risk.get("state"),
        "risk_gate_passed":risk_passed,
        "paper_order_plans":plans,
        "paper_execution":execution,
        "positions":positions,
        "performance":performance,
        "checkpoint":checkpoint,
        "autonomous_cycle_complete":state in {
            "AUTONOMOUS_PAPER_TRADING_CYCLE_COMPLETE",
            "AUTONOMOUS_TRADING_MARKET_CLOSED",
            "AUTONOMOUS_TRADING_NO_SIGNAL",
            "AUTONOMOUS_TRADING_RISK_BLOCKED",
            "AUTONOMOUS_TRADING_DUPLICATE_CYCLE_BLOCKED",
        },
        "paper_only":True,
        "live_network_enabled":False,
        "live_submission_enabled":False,
        "real_live_network_attempted":False,
        "real_live_submission_attempted":False,
        "actual_paper_orders_submitted":execution.get("paper_orders_submitted",0),
        "actual_live_orders_submitted":0,
        "next_phase":"V140_FINAL_AUTONOMOUS_RELEASE",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"autonomous_orchestrator_result.json",body)
    write_json(actual/"market_scan_report.json",{"market":market,"signals":signals})
    write_json(actual/"selected_candidates.json",{"candidates":candidates})
    write_json(actual/"paper_order_plan.json",{"plans":plans})
    write_json(actual/"position_snapshot.json",{"positions":positions})
    write_json(actual/"daily_performance.json",performance)
    append_jsonl(actual/"autonomous_cycle_ledger.jsonl",{
        "observed_at":observed,
        "cycle_id":cycle_id,
        "state":state,
        "paper_orders_submitted":execution.get("paper_orders_submitted",0),
        "actual_live_orders_submitted":0,
    })
    return body
