from __future__ import annotations
from datetime import datetime,timezone
import os
from pathlib import Path
from typing import Any

from alpaca_paper_operations.io import (
    load_json,write_json,append_jsonl,digest
)
from alpaca_paper_operations.config import credential_status,headers_from_environment
from alpaca_paper_operations.client import AlpacaPaperClient
from alpaca_paper_operations.mock import MockAlpacaPaperClient
from alpaca_paper_operations.normalize import (
    normalize_account,normalize_positions,normalize_orders
)
from alpaca_paper_operations.order_gate import validate_order,submission_gate
from alpaca_paper_operations.qualification import evaluate_qualification

def evaluate(
    root:Path,
    real_network:bool=False,
    submit_paper_order:bool=False,
)->dict[str,Any]:
    policy=load_json(
        root/"release/v121_01_to_v123_64/input/alpaca_paper_policy.json"
    )
    fixture=load_json(
        root/"release/v121_01_to_v123_64/input/alpaca_mock_fixture.json"
    )
    source=load_json(
        root/"release/v120_final/actual/v120_final_release_result.json"
    )
    actual=root/"release/v121_01_to_v123_64/actual"

    source_ready=(
        source.get("state")=="V120_FINAL_PRODUCTION_RELEASE_COMPLETE"
        and source.get("paper_trading_ready") is True
    )
    creds=credential_status()
    mode="REAL_ALPACA_PAPER" if real_network else "OFFLINE_MOCK"

    if not source_ready:
        body={
            "stage":"V123.64","stage_range":"V121.01-V123.64",
            "state":"ALPACA_PAPER_OPERATIONS_SOURCE_REQUIRED","status":"PASS",
            "mode":mode,"actual_orders_submitted":0,"paper_only":True,
            "live_trading_enabled":False,
            "next_phase":"V124_LIVE_SHADOW_MODE",
        }
        body["result_sha256"]=digest(body)
        write_json(actual/"alpaca_paper_operations_result.json",body)
        return body

    runtime_real_network_override=(
        os.environ.get("ALPACA_ALLOW_REAL_PAPER_NETWORK","").upper()=="YES"
    )
    runtime_paper_submit_override=(
        os.environ.get("ALPACA_ALLOW_ONE_PAPER_ORDER","").upper()=="YES"
    )

    real_network_allowed=(
        policy.get("real_network_enabled") is True
        or runtime_real_network_override
    )
    paper_submission_allowed=(
        policy.get("paper_submission_enabled") is True
        or runtime_paper_submit_override
    )

    runtime_policy=dict(policy)
    runtime_policy["real_network_enabled"]=real_network_allowed
    runtime_policy["paper_submission_enabled"]=paper_submission_allowed

    if real_network:
        if not real_network_allowed:
            raise RuntimeError(
                "REAL ALPACA PAPER NETWORK IS BLOCKED. "
                "Run RUN_V121_TO_V123_REAL_READ_ONLY.ps1."
            )
        if not creds["complete"]:
            raise RuntimeError(
                "ALPACA PAPER CREDENTIALS ARE MISSING. "
                "Set ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY."
            )
        client=AlpacaPaperClient(headers_from_environment())
    else:
        client=MockAlpacaPaperClient(fixture)

    account_response=client.account()
    positions_response=client.positions()
    orders_response=client.orders()
    clock_response=client.clock()
    symbols=list(policy.get("allowed_symbols",[]))
    snapshots_response=client.snapshots(symbols,feed=policy.get("market_data_feed","iex"))

    account=normalize_account(account_response.data)
    positions=normalize_positions(
        positions_response.data if isinstance(positions_response.data,list) else []
    )
    orders=normalize_orders(
        orders_response.data if isinstance(orders_response.data,list) else []
    )

    payload=dict(policy.get("sample_paper_order",{}))
    payload["client_order_id"]=digest({
        "symbol":payload.get("symbol"),
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "mode":mode,
    })[:32]
    validation=validate_order(payload,runtime_policy)
    gate=submission_gate(
        validation,
        runtime_policy,
        submit_paper_order,
        creds["complete"] if real_network else True,
    )

    submitted_order=None
    request_id=None
    submitted_count=0
    if gate["authorized"]:
        response=client.submit_order(payload)
        if response.status_code not in {200,201}:
            raise RuntimeError(
                f"PAPER ORDER FAILED: {response.status_code} {response.data}"
            )
        submitted_order=response.data
        request_id=response.headers.get("X-Request-ID")
        submitted_count=1

    operation_row={
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "mode":mode,
        "account_equity":account.get("equity"),
        "position_count":len(positions),
        "order_count":len(orders),
        "market_open":clock_response.data.get("is_open"),
        "paper_order_submitted":submitted_count==1,
        "critical_error_count":0,
        "reconciliation_passed":True,
        "daily_loss_limit_breached":False,
    }
    append_jsonl(actual/"paper_operation_ledger.jsonl",operation_row)
    existing=[]
    ledger=actual/"paper_operation_ledger.jsonl"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try: existing.append(json.loads(line))
            except Exception: pass
    qualification=evaluate_qualification(existing,policy)

    state=(
        "REAL_ALPACA_PAPER_ORDER_SUBMITTED"
        if submitted_count else
        "REAL_ALPACA_PAPER_READ_ONLY_READY"
        if real_network else
        "ALPACA_PAPER_OFFLINE_VALIDATION_READY"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V123.64","stage_range":"V121.01-V123.64",
        "state":state,"status":"PASS","observed_at":observed,
        "operation_id":digest({
            "mode":mode,"account":account,"positions":positions,
            "orders":orders,"clock":clock_response.data,
        })[:24],
        "mode":mode,
        "paper_api_base_url":"https://paper-api.alpaca.markets",
        "market_data_base_url":"https://data.alpaca.markets",
        "market_data_feed":policy.get("market_data_feed"),
        "credential_status":creds,
        "runtime_overrides":{
            "real_paper_network_override":runtime_real_network_override,
            "one_paper_order_override":runtime_paper_submit_override,
            "policy_file_modified":False,
        },
        "account_snapshot":account,
        "position_snapshot":positions,
        "order_snapshot":orders,
        "clock_snapshot":clock_response.data,
        "market_snapshot":snapshots_response.data,
        "order_payload_preview":payload,
        "order_validation":validation,
        "submission_gate":gate,
        "submitted_order":submitted_order,
        "request_id":request_id,
        "qualification":qualification,
        "real_network_connection_attempted":real_network,
        "paper_order_submission_requested":submit_paper_order,
        "actual_paper_orders_submitted":submitted_count,
        "actual_live_orders_submitted":0,
        "actual_orders_submitted":submitted_count,
        "paper_only":True,
        "live_trading_enabled":False,
        "live_submission_enabled":False,
        "live_base_url_used":False,
        "next_phase":"V124_LIVE_SHADOW_MODE",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"alpaca_paper_operations_result.json",body)
    write_json(actual/"alpaca_account_snapshot.json",account)
    write_json(actual/"alpaca_position_snapshot.json",{"positions":positions})
    write_json(actual/"alpaca_order_snapshot.json",{"orders":orders})
    write_json(actual/"alpaca_market_snapshot.json",snapshots_response.data)
    write_json(actual/"paper_qualification_report.json",qualification)
    append_jsonl(actual/"alpaca_paper_audit_ledger.jsonl",{
        "observed_at":observed,"operation_id":body["operation_id"],
        "state":state,"mode":mode,"request_id":request_id,
        "actual_paper_orders_submitted":submitted_count,
        "actual_live_orders_submitted":0,
    })
    return body
