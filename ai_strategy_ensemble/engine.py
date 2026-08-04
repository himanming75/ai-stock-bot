from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from ai_strategy_ensemble.io import load_json,write_json,append_jsonl
from ai_strategy_ensemble.config import load
from ai_strategy_ensemble.ranking import rank
from ai_strategy_ensemble.allocation import allocate
from ai_strategy_ensemble.signal import combine

def evaluate(root:Path)->dict:
    policy=load(root)
    performance=load_json(root/"release/v211_01_to_v215_64/input/strategy_performance.json").get("strategies",[])
    signals=load_json(root/"release/v211_01_to_v215_64/input/strategy_signals.json").get("signals",[])
    risk=load_json(root/"release/v206_01_to_v210_64/actual/risk_engine_v2_result.json")
    ranked=rank(performance,policy)
    allocations=allocate(ranked,policy)
    combined=combine(signals,allocations)
    risk_passed=risk.get("risk_gate",{}).get("passed") is True
    checks={
        "strategy_data_present":bool(performance),
        "rankings_created":bool(ranked),
        "eligible_strategy_present":any(row["eligible"] for row in ranked),
        "allocation_created":bool(allocations),
        "risk_gate_passed":risk_passed if policy.get("risk_gate_required") else True,
        "automatic_promotion_disabled":policy.get("automatic_strategy_promotion_enabled") is False,
        "automatic_order_submission_disabled":policy.get("automatic_order_submission_enabled") is False,
        "broker_write_disabled":policy.get("broker_write_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    ensemble_ready=all(checks[k] for k in ("strategy_data_present","rankings_created","eligible_strategy_present","allocation_created"))
    state="AI_STRATEGY_ENSEMBLE_READY" if ensemble_ready and not failed else "AI_STRATEGY_ENSEMBLE_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    champion=next((row for row in ranked if row["role"]=="CHAMPION"),None)
    result={
        "stage":"V215.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "champion":champion,
        "rankings":ranked,
        "allocations":allocations,
        "ensemble_signal":combined,
        "risk_gate_state":risk.get("state","NOT_AVAILABLE"),
        "risk_gate_passed":risk_passed,
        "checks":checks,
        "failed":failed,
        "strategy_promotion_authorized":False,
        "execution_authorized":False,
        "automatic_order_submission_enabled":False,
        "broker_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V216_01_TO_V220_64_FINAL_PRODUCTION_RELEASE",
    }
    actual=root/"release/v211_01_to_v215_64/actual"
    write_json(actual/"ai_strategy_ensemble_result.json",result)
    write_json(actual/"strategy_rankings.json",{"rankings":ranked})
    write_json(actual/"strategy_allocations.json",{"allocations":allocations})
    write_json(actual/"ensemble_signal.json",combined)
    append_jsonl(actual/"strategy_ensemble_audit_ledger.jsonl",{
        "observed_at":observed,
        "state":state,
        "champion":champion.get("strategy_id") if champion else None,
        "risk_gate_passed":risk_passed,
        "actual_live_orders_submitted":0,
    })
    return result
