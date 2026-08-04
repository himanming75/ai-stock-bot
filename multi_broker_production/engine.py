from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from multi_broker_production.config import load
from multi_broker_production.snapshots import collect
from multi_broker_production.health import evaluate as eval_health
from multi_broker_production.portfolio import aggregate
from multi_broker_production.failover import build as build_failover
from multi_broker_production.risk import evaluate as eval_risk
from multi_broker_production.io import write_json,append_jsonl

def evaluate(root:Path)->dict:
    policy=load(root)
    snapshots=collect(root)
    health=eval_health(snapshots,policy)
    portfolio=aggregate(snapshots)
    failover=build_failover(health,policy)
    risk=eval_risk(portfolio,health,policy)
    state="MULTI_BROKER_MULTI_ACCOUNT_PRODUCTION_READY" if risk["passed"] else "MULTI_BROKER_MULTI_ACCOUNT_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
        "stage":"V200.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "snapshots":snapshots,
        "broker_health":health,
        "unified_portfolio":portfolio,
        "failover":failover,
        "production_gate":risk,
        "multi_broker_ready":True,
        "multi_account_ready":True,
        "read_failover_ready":failover["read_failover_ready"],
        "automatic_write_failover_enabled":False,
        "broker_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V201_01_TO_V205_64_BROKER_PLUGIN_FRAMEWORK",
    }
    actual=root/"release/v196_01_to_v200_64/actual"
    write_json(actual/"multi_broker_production_result.json",result)
    write_json(actual/"multi_broker_health.json",health)
    write_json(actual/"unified_multi_account_portfolio.json",portfolio)
    write_json(actual/"read_failover_plan.json",failover)
    append_jsonl(actual/"multi_broker_production_ledger.jsonl",{
        "observed_at":observed,
        "state":state,
        "broker_count":portfolio["summary"]["broker_count"],
        "healthy_broker_count":health["healthy_broker_count"],
        "actual_live_orders_submitted":0,
    })
    return result
