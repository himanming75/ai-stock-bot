from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from daily_paper_close.io import (
    load_json,
    write_json,
    write_text,
    append_jsonl,
    digest_payload,
)
from daily_paper_close.metrics import (
    daily_metrics,
    fill_summary,
    position_summary,
)
from daily_paper_close.gates import evaluate_close_gates
from daily_paper_close.report import render_markdown

def evaluate(root: Path, close_date: str = "") -> dict[str, Any]:
    policy = load_json(
        root / "release/v96_33_to_v96_64/input/daily_close_policy.json"
    )
    account = load_json(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_result.json"
    )
    simulation = load_json(
        root / "release/v95_01_to_v95_32/actual/"
        "paper_execution_simulation_result.json"
    )
    risk = load_json(
        root / "release/v92_33_to_v92_64/actual/"
        "enterprise_risk_center_result.json"
    )

    if account.get("state") not in {
        "PAPER_ACCOUNT_RECONCILIATION_PASS",
        "PAPER_ACCOUNT_RECONCILIATION_REVIEW_REQUIRED",
    }:
        return {
            "stage": "V96.64",
            "stage_range": "V96.33-V96.64",
            "state": "DAILY_PAPER_CLOSE_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    if not close_date:
        close_date = datetime.now(timezone.utc).date().isoformat()

    ending_equity = float(
        simulation.get(
            "ending_equity",
            account.get("equity_reconciliation", {}).get(
                "reported_equity", 0.0
            ),
        )
    )
    starting_equity = float(
        policy.get(
            "starting_equity_override",
            simulation.get("initial_cash", ending_equity),
        )
    )
    realized = float(account.get("realized_pnl", 0.0))
    unrealized = float(account.get("unrealized_pnl", 0.0))

    metrics = daily_metrics(
        starting_equity,
        ending_equity,
        realized,
        unrealized,
    )
    fills = fill_summary(simulation)
    positions = position_summary(account)
    gates = evaluate_close_gates(
        account,
        risk,
        simulation,
        policy,
    )

    state = (
        "DAILY_PAPER_CLOSE_COMPLETE"
        if gates["passed"]
        else "DAILY_PAPER_CLOSE_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V96.64",
        "stage_range": "V96.33-V96.64",
        "state": state,
        "status": "PASS",
        "close_date": close_date,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_simulation_cycle_id": simulation.get("cycle_id"),
        "daily_metrics": metrics,
        "fill_summary": fills,
        "position_summary": positions,
        "risk_summary": {
            "risk_approved": risk.get("risk_approved"),
            "risk_state": risk.get("state"),
            "failed_risk_checks": risk.get(
                "failed_risk_checks", []
            ),
        },
        "account_summary": {
            "reconciliation_state": account.get("state"),
            "integrity_passed": account.get(
                "integrity", {}
            ).get("passed"),
            "cash_reconciled": account.get(
                "cash_reconciliation", {}
            ).get("passed"),
            "positions_reconciled": account.get(
                "position_reconciliation", {}
            ).get("passed"),
            "equity_reconciled": account.get(
                "equity_reconciliation", {}
            ).get("passed"),
        },
        "close_gates": gates,
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
        "next_phase": "V97_01_PAPER_BROKER_ADAPTER",
    }
    body["daily_close_certificate_sha256"] = digest_payload(body)

    result_path = (
        root / "release/v96_33_to_v96_64/actual/"
        "daily_paper_close_result.json"
    )
    report_path = (
        root / "release/v96_33_to_v96_64/actual/"
        "daily_paper_close_report.md"
    )
    write_json(result_path, body)
    write_text(report_path, render_markdown(body))
    append_jsonl(
        root / "release/v96_33_to_v96_64/actual/"
        "daily_paper_close_ledger.jsonl",
        {
            "close_date": close_date,
            "state": state,
            "ending_equity": metrics["ending_equity"],
            "daily_pnl": metrics["daily_pnl"],
            "daily_return_pct": metrics["daily_return_pct"],
            "gate_passed": gates["passed"],
        },
    )
    return body
