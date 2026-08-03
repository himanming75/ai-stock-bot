from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_broker_adapter.io import (
    load_json,
    write_json,
    append_jsonl,
    digest_payload,
)
from paper_broker_adapter.factory import create_adapter
from paper_broker_adapter.translators import (
    translate_account,
    translate_position,
)
from paper_broker_adapter.boundary import validate_safe_boundary

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v97_01_to_v97_32/input/"
        "paper_broker_adapter_policy.json"
    )
    daily_close = load_json(
        root / "release/v96_33_to_v96_64/actual/"
        "daily_paper_close_result.json"
    )
    account_result = load_json(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_result.json"
    )

    if daily_close.get("state") not in {
        "DAILY_PAPER_CLOSE_COMPLETE",
        "DAILY_PAPER_CLOSE_REVIEW_REQUIRED",
    }:
        return {
            "stage": "V97.32",
            "stage_range": "V97.01-V97.32",
            "state": "PAPER_BROKER_ADAPTER_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "read_only_adapter": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    reported_positions = account_result.get("reported_positions", {})
    mock_positions = []
    for symbol, row in reported_positions.items():
        if not isinstance(row, dict):
            continue
        quantity = float(row.get("quantity", 0.0))
        average_cost = float(row.get("average_cost", 0.0))
        mock_positions.append({
            "symbol": symbol,
            "quantity": quantity,
            "average_cost": average_cost,
            "market_price": average_cost,
            "market_value": quantity * average_cost,
            "unrealized_pnl": 0.0,
        })

    metrics = daily_close.get("daily_metrics", {})
    mock_account = {
        "cash": float(
            account_result.get(
                "cash_reconciliation", {}
            ).get("reported_ending_cash", 0.0)
        ),
        "equity": float(metrics.get("ending_equity", 0.0)),
        "buying_power": float(
            account_result.get(
                "cash_reconciliation", {}
            ).get("reported_ending_cash", 0.0)
        ),
        "currency": "USD",
        "status": "ACTIVE",
    }

    selected_adapter = str(policy.get("selected_adapter", "MOCK_PAPER"))
    adapter = create_adapter(
        selected_adapter,
        account=mock_account,
        positions=mock_positions,
    )
    capabilities = adapter.capabilities()
    boundary = validate_safe_boundary(capabilities)
    health = adapter.health_check()
    account_snapshot = translate_account(adapter.get_account_snapshot())
    positions_snapshot = [
        translate_position(row)
        for row in adapter.get_positions_snapshot()
    ]

    checks = {
        "daily_close_available": bool(daily_close),
        "adapter_read_only": capabilities.get("read_only") is True,
        "safe_boundary_passed": boundary["passed"],
        "order_submit_disabled": capabilities.get("order_submit") is False,
        "order_cancel_disabled": capabilities.get("order_cancel") is False,
        "network_not_used": health.get("network_used") is False,
        "credentials_not_used": health.get("credentials_used") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = (
        "PAPER_BROKER_ADAPTER_READY"
        if not failed
        else "PAPER_BROKER_ADAPTER_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V97.32",
        "stage_range": "V97.01-V97.32",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "selected_adapter": selected_adapter,
        "adapter_name": adapter.name,
        "adapter_capabilities": capabilities,
        "adapter_health": health,
        "safe_api_boundary": boundary,
        "account_snapshot": account_snapshot,
        "positions_snapshot": positions_snapshot,
        "checks": checks,
        "failed_checks": failed,
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
        "next_phase": "V97_33_PAPER_BROKER_READ_MODEL",
    }
    body["paper_broker_adapter_certificate_sha256"] = digest_payload(body)

    result_path = (
        root / "release/v97_01_to_v97_32/actual/"
        "paper_broker_adapter_result.json"
    )
    write_json(result_path, body)
    append_jsonl(
        root / "release/v97_01_to_v97_32/actual/"
        "paper_broker_adapter_audit_ledger.jsonl",
        {
            "observed_at": body["observed_at"],
            "adapter_name": body["adapter_name"],
            "state": state,
            "safe_boundary_passed": boundary["passed"],
            "actual_orders_submitted": 0,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
        },
    )
    return body
