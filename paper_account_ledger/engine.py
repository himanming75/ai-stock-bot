from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_account_ledger.io import (
    load_json,
    write_json,
    append_jsonl,
    digest_payload,
)
from paper_account_ledger.ledger import (
    build_cash_entries,
    build_position_entries,
    aggregate_positions,
)
from paper_account_ledger.reconciliation import (
    find_duplicate_fill_ids,
    reconcile_cash,
    reconcile_positions,
    reconcile_equity,
)
from paper_account_ledger.integrity import evaluate_integrity

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v96_01_to_v96_32/input/account_reconciliation_policy.json"
    )
    simulation = load_json(
        root / "release/v95_01_to_v95_32/actual/"
        "paper_execution_simulation_result.json"
    )
    lifecycle = load_json(
        root / "release/v95_33_to_v95_64/actual/"
        "paper_position_lifecycle_result.json"
    )

    if simulation.get("state") != "PAPER_EXECUTION_SIMULATION_COMPLETED":
        return {
            "stage": "V96.32",
            "stage_range": "V96.01-V96.32",
            "state": "PAPER_ACCOUNT_LEDGER_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    tolerance = float(policy.get("cash_tolerance", 0.01))
    quantity_tolerance = float(policy.get("quantity_tolerance", 0.000001))
    equity_tolerance = float(policy.get("equity_tolerance", 0.01))

    cash_entries = build_cash_entries(simulation, lifecycle)
    position_entries = build_position_entries(simulation, lifecycle)
    calculated_positions = aggregate_positions(position_entries)

    portfolio = simulation.get("portfolio", {})
    reported_positions = lifecycle.get(
        "updated_position_state", {}
    ).get("positions", {})
    if not reported_positions:
        reported_positions = portfolio.get("positions", {})

    cash_rec = reconcile_cash(
        cash_entries,
        float(simulation.get("ending_cash", portfolio.get("cash", 0.0))),
        tolerance,
    )
    position_rec = reconcile_positions(
        calculated_positions,
        reported_positions,
        quantity_tolerance,
    )
    equity_rec = reconcile_equity(
        float(simulation.get("ending_cash", portfolio.get("cash", 0.0))),
        float(portfolio.get("market_value", 0.0)),
        float(simulation.get("ending_equity", portfolio.get("equity", 0.0))),
        equity_tolerance,
    )

    duplicate_fill_ids = find_duplicate_fill_ids(
        simulation.get("fills", [])
    )
    realized_pnl = float(lifecycle.get("total_realized_pnl", 0.0))
    unrealized_pnl = float(portfolio.get("unrealized_pnl", 0.0))
    integrity = evaluate_integrity(
        duplicate_fill_ids,
        cash_rec,
        position_rec,
        equity_rec,
        realized_pnl,
        unrealized_pnl,
    )

    state = (
        "PAPER_ACCOUNT_RECONCILIATION_PASS"
        if integrity["passed"]
        else "PAPER_ACCOUNT_RECONCILIATION_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V96.32",
        "stage_range": "V96.01-V96.32",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_simulation_cycle_id": simulation.get("cycle_id"),
        "cash_ledger_entries": cash_entries,
        "position_ledger_entries": position_entries,
        "calculated_positions": calculated_positions,
        "reported_positions": reported_positions,
        "cash_reconciliation": cash_rec,
        "position_reconciliation": position_rec,
        "equity_reconciliation": equity_rec,
        "duplicate_fill_ids": duplicate_fill_ids,
        "realized_pnl": round(realized_pnl, 4),
        "unrealized_pnl": round(unrealized_pnl, 4),
        "total_pnl": round(realized_pnl + unrealized_pnl, 4),
        "integrity": integrity,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V96_33_DAILY_PAPER_CLOSE",
    }
    body["paper_account_certificate_sha256"] = digest_payload(body)

    write_json(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_result.json",
        body,
    )
    append_jsonl(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_ledger.jsonl",
        {
            "observed_at": body["observed_at"],
            "cycle_id": body["source_simulation_cycle_id"],
            "state": state,
            "integrity_passed": integrity["passed"],
            "total_pnl": body["total_pnl"],
        },
    )
    return body
