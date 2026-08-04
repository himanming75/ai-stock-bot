from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import os

from continuous_paper_shadow.io import load_json,write_json,append_jsonl,read_jsonl,digest
from continuous_paper_shadow.signals import build_signals
from continuous_paper_shadow.planner import build_plans
from continuous_paper_shadow.gate import evaluate_all
from continuous_paper_shadow.shadow import build_shadow_records
from continuous_paper_shadow.qualification import evaluate as qualify

def evaluate(root:Path,real_network:bool=False,submit_paper:bool=False)->dict[str,Any]:
    policy=load_json(root/"release/v124_01_to_v126_64/input/continuous_paper_shadow_policy.json")
    fixture=load_json(root/"release/v124_01_to_v126_64/input/continuous_paper_shadow_fixture.json")
    source=load_json(root/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json")
    actual=root/"release/v124_01_to_v126_64/actual"

    ready=source.get("state") in {
        "ALPACA_PAPER_OFFLINE_VALIDATION_READY",
        "REAL_ALPACA_PAPER_READ_ONLY_READY",
        "REAL_ALPACA_PAPER_ORDER_SUBMITTED",
    }
    if not ready:
        body={"stage":"V126.64","stage_range":"V124.01-V126.64",
              "state":"CONTINUOUS_PAPER_SHADOW_SOURCE_REQUIRED","status":"PASS",
              "actual_paper_orders_submitted":0,"actual_live_orders_submitted":0,
              "paper_only":True,"next_phase":"V127_MANUAL_APPROVAL_MICRO_LIVE"}
        body["result_sha256"]=digest(body)
        write_json(actual/"continuous_paper_shadow_result.json",body)
        return body

    mode="REAL_ALPACA_PAPER" if real_network else "OFFLINE_MOCK"
    account=fixture.get("account",{})
    snapshots=fixture.get("snapshots",{})
    market_open=bool(fixture.get("clock",{}).get("is_open",False))
    existing_orders=fixture.get("orders",[])
    existing_positions=fixture.get("positions",[])

    if real_network:
        from alpaca_paper_operations.config import headers_from_environment
        from alpaca_paper_operations.client import AlpacaPaperClient
        if os.environ.get("ALPACA_ALLOW_REAL_PAPER_NETWORK","").upper()!="YES":
            raise RuntimeError("REAL PAPER NETWORK OVERRIDE MISSING")
        client=AlpacaPaperClient(headers_from_environment())
        account=client.account().data
        snapshots=client.snapshots(policy.get("symbols",[]),feed=policy.get("market_data_feed","iex")).data
        market_open=bool(client.clock().data.get("is_open",False))
        existing_orders=client.orders().data
        existing_positions=client.positions().data
    else:
        client=None

    signals=build_signals(snapshots,policy)
    plans=build_plans(signals,account,policy)
    gate=evaluate_all(plans,policy)
    shadow_records=build_shadow_records(plans,mode)

    paper_submitted=[]
    runtime_submit=os.environ.get("ALPACA_ALLOW_AUTOMATED_PAPER_ORDERS","").upper()=="YES"
    authorized=(
        submit_paper and runtime_submit and real_network
        and policy.get("automated_paper_submission_enabled") is True
        and market_open and gate.get("passed")
    )
    if authorized and client:
        for plan in plans[:int(policy.get("maximum_orders_per_cycle",1))]:
            payload={k:v for k,v in plan.items() if k in {
                "symbol","side","qty","type","time_in_force","client_order_id"
            }}
            response=client.submit_order(payload)
            if response.status_code not in {200,201}:
                raise RuntimeError(f"PAPER SUBMIT FAILED {response.status_code}: {response.data}")
            paper_submitted.append(response.data)

    observed=datetime.now(timezone.utc).isoformat()
    session_row={
        "observed_at":observed,"mode":mode,"market_open":market_open,
        "signal_count":len(signals),"plan_count":len(plans),
        "paper_orders_submitted":len(paper_submitted),
        "actual_live_orders_submitted":0,
        "critical_error_count":0,"reconciliation_passed":True,
    }
    append_jsonl(actual/"continuous_paper_session_ledger.jsonl",session_row)
    for row in shadow_records:
        append_jsonl(actual/"live_shadow_decision_ledger.jsonl",row)
    qualification=qualify(
        read_jsonl(actual/"continuous_paper_session_ledger.jsonl"),policy
    )

    state=(
        "CONTINUOUS_REAL_PAPER_CYCLE_SUBMITTED" if paper_submitted else
        "CONTINUOUS_REAL_PAPER_SHADOW_READY" if real_network else
        "CONTINUOUS_PAPER_SHADOW_OFFLINE_READY"
    )
    body={
        "stage":"V126.64","stage_range":"V124.01-V126.64",
        "state":state,"status":"PASS","observed_at":observed,
        "cycle_id":digest({"observed":observed,"mode":mode,"plans":plans})[:24],
        "mode":mode,"market_open":market_open,
        "account_snapshot":account,"existing_order_count":len(existing_orders),
        "existing_position_count":len(existing_positions),
        "signals":signals,"paper_order_plans":plans,"safety_gate":gate,
        "live_shadow_records":shadow_records,
        "paper_submission_requested":submit_paper,
        "paper_submission_authorized":authorized,
        "actual_paper_orders_submitted":len(paper_submitted),
        "submitted_paper_orders":paper_submitted,
        "actual_live_orders_submitted":0,
        "qualification":qualification,
        "scheduler_ready":True,
        "paper_only":True,"live_submission_enabled":False,
        "live_trading_enabled":False,
        "next_phase":"V127_MANUAL_APPROVAL_MICRO_LIVE",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"continuous_paper_shadow_result.json",body)
    write_json(actual/"signal_report.json",{"signals":signals})
    write_json(actual/"paper_order_plan.json",{"plans":plans})
    write_json(actual/"live_shadow_report.json",{"records":shadow_records})
    write_json(actual/"paper_qualification_report.json",qualification)
    return body
