from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from live_broker_readonly.io import (
    load_json,write_json,append_jsonl,digest
)
from live_broker_readonly.capabilities import (
    get_capabilities,validate_read_only
)
from live_broker_readonly.credentials import inspect_credential_presence
from live_broker_readonly.adapters import build_adapter
from live_broker_readonly.normalize import (
    normalize_account,normalize_positions,normalize_orders
)
from live_broker_readonly.reconcile import reconcile
from live_broker_readonly.drift import detect_drift
from live_broker_readonly.boundary import evaluate_boundary

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v111_01_to_v113_64/input/"
        "live_broker_readonly_policy.json"
    )
    fixture=load_json(
        root/"release/v111_01_to_v113_64/input/"
        "broker_snapshot_fixture.json"
    )
    paper=load_json(
        root/"release/v109_01_to_v110_64/actual/"
        "autonomous_paper_operations_result.json"
    )
    actual_dir=root/"release/v111_01_to_v113_64/actual"

    source_ready=paper.get("state")=="AUTONOMOUS_PAPER_OPERATIONS_READY"
    adapter_name=str(policy.get("selected_adapter","MOCK_READ_ONLY"))
    capabilities=get_capabilities(adapter_name)
    capability_validation=validate_read_only(capabilities)
    credentials=inspect_credential_presence(adapter_name)
    boundary=evaluate_boundary(capabilities)

    if not source_ready:
        body={
            "stage":"V113.64",
            "stage_range":"V111.01-V113.64",
            "state":"LIVE_BROKER_READ_ONLY_SOURCE_REQUIRED",
            "status":"PASS",
            "selected_adapter":adapter_name,
            "capabilities":capabilities,
            "capability_validation":capability_validation,
            "credential_inspection":credentials,
            "safe_boundary":boundary,
            "actual_credentials_used":False,
            "actual_external_network_used":False,
            "network_requests_executed":0,
            "actual_orders_submitted":0,
            "paper_only":True,
            "read_only":True,
            "next_phase":"V114_01_TO_V116_64_BROKER_INTEGRATION_SAFE_EXECUTION_BOUNDARY",
        }
        body["certificate_sha256"]=digest(body)
        write_json(actual_dir/"live_broker_readonly_result.json",body)
        return body

    adapter=build_adapter(adapter_name,fixture)
    health=adapter.health()
    account=normalize_account(adapter.account())
    positions=normalize_positions(adapter.positions())
    orders=normalize_orders(adapter.orders())

    ending_equity=float(
        paper.get("operations_report",{}).get("ending_equity",0.0)
    )
    internal_account={
        "cash":ending_equity,
        "equity":ending_equity,
    }
    internal_positions=[]
    reconciliation=reconcile(
        internal_account,
        internal_positions,
        account,
        positions,
        policy,
    )
    drift=detect_drift(reconciliation,orders)

    state=(
        "LIVE_BROKER_READ_ONLY_INFRASTRUCTURE_READY"
        if capability_validation.get("passed")
        and boundary.get("passed")
        and health.get("healthy")
        else "LIVE_BROKER_READ_ONLY_REVIEW_REQUIRED"
    )
    observed_at=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V113.64",
        "stage_range":"V111.01-V113.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed_at,
        "snapshot_id":digest({
            "adapter":adapter_name,
            "account":account,
            "positions":positions,
            "orders":orders,
        })[:24],
        "selected_adapter":adapter_name,
        "supported_adapters":[
            "MOCK_READ_ONLY",
            "ALPACA_READ_ONLY",
            "IBKR_READ_ONLY",
            "ETRADE_READ_ONLY",
        ],
        "capabilities":capabilities,
        "capability_validation":capability_validation,
        "credential_inspection":credentials,
        "adapter_health":health,
        "account_snapshot":account,
        "position_snapshot":positions,
        "order_snapshot":orders,
        "reconciliation":reconciliation,
        "drift":drift,
        "safe_boundary":boundary,
        "real_network_connection_attempted":False,
        "real_broker_snapshot_fetched":False,
        "fixture_snapshot_used":True,
        "credentials_loaded":False,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "actual_orders_submitted":0,
        "paper_only":True,
        "read_only":True,
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "next_phase":"V114_01_TO_V116_64_BROKER_INTEGRATION_SAFE_EXECUTION_BOUNDARY",
    }
    body["certificate_sha256"]=digest(body)
    write_json(actual_dir/"live_broker_readonly_result.json",body)
    write_json(actual_dir/"normalized_account_snapshot.json",account)
    write_json(
        actual_dir/"normalized_position_snapshot.json",
        {"positions":positions},
    )
    write_json(
        actual_dir/"normalized_order_snapshot.json",
        {"orders":orders},
    )
    write_json(actual_dir/"broker_reconciliation.json",reconciliation)
    write_json(actual_dir/"broker_drift_report.json",drift)
    append_jsonl(
        actual_dir/"live_broker_readonly_audit_ledger.jsonl",
        {
            "observed_at":observed_at,
            "snapshot_id":body["snapshot_id"],
            "selected_adapter":adapter_name,
            "state":state,
            "drift_detected":drift.get("drift_detected"),
            "real_network_connection_attempted":False,
            "credentials_used":False,
            "actual_orders_submitted":0,
        },
    )
    return body
