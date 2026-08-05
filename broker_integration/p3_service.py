from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .io import append_jsonl, write_json
from .p3_accounting import compare_account, compare_positions
from .p3_fill_registry import register_fill
from .p3_models import normalize_order


def run_p3_sync(
    *,
    broker_account: dict[str, Any],
    broker_positions: list[dict[str, Any]],
    broker_orders: list[dict[str, Any]],
    local_portfolio: dict[str, Any],
    local_positions: list[dict[str, Any]],
    fill_registry_path: Path,
    fill_ledger_path: Path,
    order_state_ledger_path: Path,
    drift_ledger_path: Path,
    latest_result_path: Path,
    position_tolerance: Decimal = Decimal("0.000001"),
    account_tolerance: Decimal = Decimal("1.00"),
) -> dict[str, Any]:
    observed_at = datetime.now(timezone.utc).isoformat()
    normalized_orders = [
        normalize_order(value).as_dict()
        for value in broker_orders
    ]

    new_fill_count = 0
    duplicate_fill_count = 0
    unknown_states = sorted({
        value["status"]
        for value in normalized_orders
        if value["status_known"] is False
    })

    for order in normalized_orders:
        append_jsonl(order_state_ledger_path, {
            "observed_at": observed_at,
            **order,
        })
        if order["status"] in {"partially_filled", "filled"}:
            created, key = register_fill(fill_registry_path, order)
            if created:
                new_fill_count += 1
                append_jsonl(fill_ledger_path, {
                    "observed_at": observed_at,
                    "fill_key": key,
                    **order,
                })
            else:
                duplicate_fill_count += 1

    position_drifts = compare_positions(
        broker_positions,
        local_positions,
        position_tolerance,
    )
    account_drifts = compare_account(
        broker_account,
        local_portfolio,
        account_tolerance,
    )

    for drift in position_drifts + account_drifts:
        append_jsonl(drift_ledger_path, {
            "observed_at": observed_at,
            **drift,
        })

    blockers = []
    if unknown_states:
        blockers.append("UNKNOWN_ORDER_STATE")
    if position_drifts:
        blockers.append("POSITION_RECONCILIATION_DRIFT")
    if account_drifts:
        blockers.append("ACCOUNT_RECONCILIATION_DRIFT")

    reconciliation_passed = not blockers
    result = {
        "stage": "P3",
        "state": (
            "ORDER_FILL_PORTFOLIO_SYNC_READY"
            if reconciliation_passed
            else "ORDER_FILL_PORTFOLIO_SYNC_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": observed_at,
        "normalized_orders": normalized_orders,
        "new_fill_count": new_fill_count,
        "duplicate_fill_count": duplicate_fill_count,
        "unknown_order_states": unknown_states,
        "position_drifts": position_drifts,
        "account_drifts": account_drifts,
        "reconciliation_passed": reconciliation_passed,
        "new_order_submission_allowed": reconciliation_passed,
        "fail_closed": not reconciliation_passed,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": "P4_AUTONOMOUS_PAPER_RUNTIME",
    }
    write_json(latest_result_path, result)
    return result
