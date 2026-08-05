from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

from alpaca_paper_read.adapter import AlpacaPaperReadAdapter
from alpaca_paper_read.config import ReadConfig
from alpaca_paper_read.http_client import ReadOnlyHttpClient
from broker_integration.execution_config import load_execution_config
from broker_integration.execution_http import AlpacaPaperExecutionHttp
from broker_integration.io import write_json
from broker_integration.p3_service import run_p3_sync


TERMINAL_STATES = {
    "filled", "canceled", "expired", "rejected", "suspended",
}
KNOWN_STATES = {
    "new", "accepted", "pending_new", "partially_filled", "filled",
    "canceled", "pending_cancel", "pending_replace", "replaced",
    "rejected", "expired", "suspended", "accepted_for_bidding",
    "stopped", "calculated",
}


def build_clients():
    config = load_execution_config()
    read_config = ReadConfig(
        api_key=config.api_key,
        secret_key=config.secret_key,
        base_url=config.base_url,
        timeout_seconds=config.timeout_seconds,
        maximum_attempts=config.maximum_attempts,
        backoff_seconds=config.backoff_seconds,
        actual_network_enabled=config.network_enabled,
    )
    return (
        config,
        AlpacaPaperReadAdapter(ReadOnlyHttpClient(read_config)),
        AlpacaPaperExecutionHttp(config),
    )


def get_order_by_client_id(http, client_order_id: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "client_order_id": client_order_id,
    })
    value, _ = http.request_json(
        "GET",
        f"/v2/orders:by_client_order_id?{query}",
    )
    if not isinstance(value, dict):
        raise RuntimeError("ORDER_RESPONSE_NOT_OBJECT")
    return value


def poll_order(
    http,
    client_order_id: str,
    timeout_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    latest = {}
    while time.time() <= deadline:
        latest = get_order_by_client_id(http, client_order_id)
        status = str(latest.get("status", "")).lower()
        if status in TERMINAL_STATES or status == "partially_filled":
            return latest
        time.sleep(poll_seconds)
    return latest


def write_p2_validation(
    root: Path,
    order: dict[str, Any],
) -> dict[str, Any]:
    status = str(order.get("status", "")).lower()
    checks = {
        "broker_order_id": bool(order.get("id")),
        "client_order_id": bool(order.get("client_order_id")),
        "paper_order_status_known": status in KNOWN_STATES,
        "paper_order_observed": status not in {"", "rejected"},
        "live_orders_zero": True,
    }
    validated = all(checks.values())
    result = {
        "stage": "P2_ACTUAL_VALIDATION",
        "validated": validated,
        "status": "PASS" if validated else "FAIL",
        "checks": checks,
        "order": order,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "actual_paper_orders_observed": 1 if validated else 0,
        "actual_live_orders_submitted": 0,
    }
    write_json(
        root / "release/p2_actual_paper_execution/actual/"
               "p2_actual_validation.json",
        result,
    )
    return result


def write_p3_validation(
    root: Path,
    *,
    order: dict[str, Any],
    read_adapter,
) -> dict[str, Any]:
    account = read_adapter.get_account()
    positions = read_adapter.get_positions()
    open_orders = read_adapter.get_open_orders()

    local_portfolio = {
        "cash": account.get("cash", "0"),
        "equity": account.get("equity", "0"),
    }
    local_positions = [
        {
            "symbol": value.get("symbol", ""),
            "qty": value.get("qty", "0"),
        }
        for value in positions
    ]

    actual_root = (
        root / "release/p3_order_fill_portfolio_sync/actual"
    )
    sync_result = run_p3_sync(
        broker_account=account,
        broker_positions=positions,
        broker_orders=[order],
        local_portfolio=local_portfolio,
        local_positions=local_positions,
        fill_registry_path=actual_root / "actual_fill_registry.json",
        fill_ledger_path=actual_root / "actual_fill_ledger.jsonl",
        order_state_ledger_path=(
            actual_root / "actual_order_state_ledger.jsonl"
        ),
        drift_ledger_path=actual_root / "actual_drift_ledger.jsonl",
        latest_result_path=actual_root / "actual_p3_sync_result.json",
        position_tolerance=Decimal("0.000001"),
        account_tolerance=Decimal("1.00"),
    )

    order_status = str(order.get("status", "")).lower()
    checks = {
        "order_status_known": order_status in KNOWN_STATES,
        "account_read": bool(account),
        "positions_read": isinstance(positions, list),
        "open_orders_read": isinstance(open_orders, list),
        "reconciliation_passed": (
            sync_result.get("reconciliation_passed") is True
        ),
        "live_orders_zero": True,
    }
    validated = all(checks.values())
    result = {
        "stage": "P3_ACTUAL_VALIDATION",
        "validated": validated,
        "status": "PASS" if validated else "FAIL",
        "checks": checks,
        "order": order,
        "account": account,
        "positions": positions,
        "open_orders": open_orders,
        "sync_result": sync_result,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "actual_live_orders_submitted": 0,
    }
    write_json(
        actual_root / "p3_actual_validation.json",
        result,
    )
    return result


def validation_status(root: Path) -> dict[str, Any]:
    paths = {
        "p2": root / "release/p2_actual_paper_execution/actual/"
                     "p2_actual_validation.json",
        "p3": root / "release/p3_order_fill_portfolio_sync/actual/"
                     "p3_actual_validation.json",
        "p4": root / "release/p4_autonomous_paper_runtime/actual/"
                     "p4_actual_validation.json",
    }
    values = {}
    for key, path in paths.items():
        values[key] = (
            json.loads(path.read_text(encoding="utf-8-sig"))
            if path.exists()
            else {"validated": False}
        )
    return {
        "p2_actual_validated": values["p2"].get("validated") is True,
        "p3_actual_validated": values["p3"].get("validated") is True,
        "p4_actual_validated": values["p4"].get("validated") is True,
    }
