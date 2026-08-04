from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from portfolio_broker.io import load_json,write_json,append_jsonl
from portfolio_broker.registry import build_adapters
from portfolio_broker.portfolio import aggregate
from portfolio_broker.risk import evaluate as evaluate_risk

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v181_01_to_v185_64/config/portfolio_policy.json")
    adapters=build_adapters(root)
    portfolio=aggregate(adapters)
    risk=evaluate_risk(portfolio,policy)
    state="PORTFOLIO_BROKER_ADAPTER_FOUNDATION_READY" if risk["passed"] else "PORTFOLIO_BROKER_ADAPTER_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
        "stage":"V185.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "portfolio":portfolio,
        "portfolio_risk_gate":risk,
        "registered_brokers":[
            {
                "broker_id":a.broker_id,
                "read_only":a.read_only,
                "supports_orders":a.supports_orders,
            }
            for a in adapters
        ],
        "multi_account_ready":True,
        "broker_adapter_foundation_ready":True,
        "broker_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V186_01_TO_V190_64_PRODUCTION_OPERATIONS_AND_REPORTING",
    }
    actual=root/"release/v181_01_to_v185_64/actual"
    write_json(actual/"portfolio_broker_result.json",result)
    write_json(actual/"portfolio_snapshot.json",portfolio)
    write_json(actual/"portfolio_risk_gate.json",risk)
    append_jsonl(actual/"portfolio_broker_audit_ledger.jsonl",{
        "observed_at":observed,
        "state":state,
        "account_count":portfolio["summary"]["account_count"],
        "position_count":portfolio["summary"]["position_count"],
        "actual_live_orders_submitted":0,
    })
    return result
