from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from broker_safe_execution.io import (
    load_json,write_json,append_jsonl,digest
)
from broker_safe_execution.intents import build_order_intents
from broker_safe_execution.validation import validate_all
from broker_safe_execution.approval import build_manual_approval_package
from broker_safe_execution.translators import translate_intent
from broker_safe_execution.queue import build_queue
from broker_safe_execution.gateway import evaluate_gateway
from broker_safe_execution.sync import (
    simulate_fill_sync,simulate_position_sync,simulate_cancel_replace
)

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v114_01_to_v116_64/input/"
        "broker_safe_execution_policy.json"
    )
    source=load_json(
        root/"release/v111_01_to_v113_64/actual/"
        "live_broker_readonly_result.json"
    )
    actual_dir=root/"release/v114_01_to_v116_64/actual"

    source_ready=(
        source.get("state")
        =="LIVE_BROKER_READ_ONLY_INFRASTRUCTURE_READY"
        and source.get("read_only") is True
    )
    adapter_name=str(source.get("selected_adapter","MOCK_READ_ONLY"))

    if not source_ready:
        body={
            "stage":"V116.64",
            "stage_range":"V114.01-V116.64",
            "state":"BROKER_SAFE_EXECUTION_SOURCE_REQUIRED",
            "status":"PASS",
            "selected_adapter":adapter_name,
            "actual_credentials_used":False,
            "actual_external_network_used":False,
            "actual_orders_submitted":0,
            "paper_only":True,
            "live_trading_enabled":False,
            "next_phase":"V117_01_TO_V119_64_LIVE_SAFETY_SYSTEM",
        }
        body["certificate_sha256"]=digest(body)
        write_json(actual_dir/"broker_safe_execution_result.json",body)
        return body

    account_equity=float(
        source.get("account_snapshot",{}).get("equity",0.0)
    )
    intents=build_order_intents(account_equity,policy)
    validation=validate_all(intents,policy)
    approval=build_manual_approval_package(intents,validation)
    translated=[
        translate_intent(row,adapter_name) for row in intents
    ]
    queue=build_queue(intents,validation,translated)
    gateway=evaluate_gateway(approval,policy)
    fill_sync=simulate_fill_sync(queue)
    position_sync=simulate_position_sync()
    cancel_replace=simulate_cancel_replace(queue)

    state=(
        "BROKER_INTEGRATION_SAFE_EXECUTION_BOUNDARY_READY"
        if validation.get("passed") and gateway.get("passed")
        else "BROKER_INTEGRATION_SAFE_EXECUTION_REVIEW_REQUIRED"
    )
    observed_at=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V116.64",
        "stage_range":"V114.01-V116.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed_at,
        "execution_package_id":digest({
            "source_snapshot_id":source.get("snapshot_id"),
            "adapter_name":adapter_name,
            "intent_ids":[row.get("intent_id") for row in intents],
        })[:24],
        "source_snapshot_id":source.get("snapshot_id"),
        "selected_adapter":adapter_name,
        "account_equity":account_equity,
        "order_intents":intents,
        "validation":validation,
        "manual_approval_package":approval,
        "translated_payloads":translated,
        "execution_queue":queue,
        "safe_gateway":gateway,
        "fill_sync":fill_sync,
        "position_sync":position_sync,
        "cancel_replace":cancel_replace,
        "manual_approval_required":True,
        "approval_granted":False,
        "approval_token_issued":False,
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "real_broker_submission_attempted":False,
        "real_broker_sync_performed":False,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "actual_orders_submitted":0,
        "paper_only":True,
        "read_only_source":True,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "next_phase":"V117_01_TO_V119_64_LIVE_SAFETY_SYSTEM",
    }
    body["certificate_sha256"]=digest(body)
    write_json(actual_dir/"broker_safe_execution_result.json",body)
    write_json(actual_dir/"order_intents.json",{"intents":intents})
    write_json(actual_dir/"order_validation.json",validation)
    write_json(actual_dir/"manual_approval_package.json",approval)
    write_json(actual_dir/"execution_queue.json",queue)
    write_json(actual_dir/"safe_gateway_report.json",gateway)
    write_json(actual_dir/"fill_sync_report.json",fill_sync)
    write_json(actual_dir/"position_sync_report.json",position_sync)
    write_json(actual_dir/"cancel_replace_report.json",cancel_replace)
    append_jsonl(
        actual_dir/"broker_safe_execution_audit_ledger.jsonl",
        {
            "observed_at":observed_at,
            "execution_package_id":body["execution_package_id"],
            "state":state,
            "selected_adapter":adapter_name,
            "intent_count":len(intents),
            "valid_intent_count":validation.get("valid_count"),
            "approval_granted":False,
            "actual_orders_submitted":0,
        },
    )
    return body
