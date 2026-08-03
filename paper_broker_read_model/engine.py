from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_broker_read_model.io import (
    load_json,
    write_json,
    append_jsonl,
    digest_payload,
)
from paper_broker_read_model.models import (
    normalize_account,
    normalize_positions,
    internal_account_from_ledger,
    internal_positions_from_ledger,
)
from paper_broker_read_model.reconciliation import (
    reconcile_account,
    reconcile_positions,
)
from paper_broker_read_model.freshness import evaluate_snapshot_freshness
from paper_broker_read_model.integrity import evaluate_integrity

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v97_33_to_v97_64/input/"
        "paper_broker_read_model_policy.json"
    )
    adapter = load_json(
        root / "release/v97_01_to_v97_32/actual/"
        "paper_broker_adapter_result.json"
    )
    account_result = load_json(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_result.json"
    )

    if adapter.get("state") not in {
        "PAPER_BROKER_ADAPTER_READY",
        "PAPER_BROKER_ADAPTER_REVIEW_REQUIRED",
    }:
        return {
            "stage": "V97.64",
            "stage_range": "V97.33-V97.64",
            "state": "PAPER_BROKER_READ_MODEL_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "read_only_adapter": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    broker_account = normalize_account(adapter.get("account_snapshot", {}))
    broker_positions = normalize_positions(
        adapter.get("positions_snapshot", [])
    )
    internal_account = internal_account_from_ledger(account_result)
    internal_positions = internal_positions_from_ledger(account_result)

    account_reconciliation = reconcile_account(
        broker_account,
        internal_account,
        policy,
    )
    position_reconciliation = reconcile_positions(
        broker_positions,
        internal_positions,
        policy,
    )
    freshness = evaluate_snapshot_freshness(
        str(adapter.get("observed_at", "")),
        int(policy.get("maximum_snapshot_age_seconds", 86400)),
    )
    integrity = evaluate_integrity(
        account_reconciliation,
        position_reconciliation,
        freshness,
        adapter,
    )
    state = (
        "PAPER_BROKER_SNAPSHOT_RECONCILIATION_PASS"
        if integrity["passed"]
        else "PAPER_BROKER_SNAPSHOT_RECONCILIATION_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V97.64",
        "stage_range": "V97.33-V97.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_adapter_name": adapter.get("adapter_name"),
        "broker_account_snapshot": broker_account,
        "internal_account_snapshot": internal_account,
        "broker_positions_snapshot": broker_positions,
        "internal_positions_snapshot": internal_positions,
        "account_reconciliation": account_reconciliation,
        "position_reconciliation": position_reconciliation,
        "snapshot_freshness": freshness,
        "integrity": integrity,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "read_only_adapter": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V98_01_AUTOMATED_BACKTEST_FRAMEWORK",
    }
    body["paper_broker_snapshot_certificate_sha256"] = digest_payload(body)

    write_json(
        root / "release/v97_33_to_v97_64/actual/"
        "paper_broker_snapshot_reconciliation_result.json",
        body,
    )
    append_jsonl(
        root / "release/v97_33_to_v97_64/actual/"
        "paper_broker_snapshot_reconciliation_ledger.jsonl",
        {
            "observed_at": body["observed_at"],
            "adapter_name": body["source_adapter_name"],
            "state": state,
            "account_reconciled": account_reconciliation["passed"],
            "positions_reconciled": position_reconciliation["passed"],
            "snapshot_fresh": freshness["passed"],
            "integrity_passed": integrity["passed"],
        },
    )
    return body
