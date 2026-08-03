from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_position_lifecycle.io import load_json, write_json, append_jsonl, digest_payload
from paper_position_lifecycle.rules import evaluate_exit
from paper_position_lifecycle.accounting import close_position
from paper_position_lifecycle.state import build_position_state

def evaluate(root: Path, lifecycle_date: str = "") -> dict[str, Any]:
    policy = load_json(
        root / "release/v95_33_to_v95_64/input/position_lifecycle_policy.json"
    )
    marks = load_json(
        root / "release/v95_33_to_v95_64/input/lifecycle_mark_prices.json"
    )
    source = load_json(
        root / "release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json"
    )
    prior_state_path = (
        root / "release/v95_33_to_v95_64/actual/paper_position_state.json"
    )
    prior_state = load_json(prior_state_path)

    source_positions = source.get("portfolio", {}).get("positions", {})
    if not source_positions:
        return {
            "stage": "V95.64",
            "stage_range": "V95.33-V95.64",
            "state": "PAPER_POSITION_LIFECYCLE_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    if not lifecycle_date:
        lifecycle_date = datetime.now(timezone.utc).date().isoformat()

    state = build_position_state(source_positions, prior_state, lifecycle_date)
    decisions = []
    close_records = []
    updated_positions = {}

    for symbol, position in state["positions"].items():
        mark_price = float(marks.get(symbol, position["average_cost"]))
        decision = evaluate_exit(
            position,
            mark_price,
            int(position["holding_days"]),
            float(position["high_water_mark"]),
            policy,
        )
        decision_record = {
            "symbol": symbol,
            "lifecycle_date": lifecycle_date,
            "mark_price": round(mark_price, 4),
            "quantity": position["quantity"],
            "average_cost": position["average_cost"],
            "holding_days": position["holding_days"],
            **decision,
        }
        decisions.append(decision_record)

        if decision["action"] == "EXIT":
            close = close_position(
                symbol,
                position,
                mark_price,
                float(policy.get("commission_per_share", 0.0)),
            )
            close["exit_reason"] = decision["reason"]
            close["lifecycle_date"] = lifecycle_date
            close_records.append(close)
            append_jsonl(
                root / "release/v95_33_to_v95_64/actual/paper_position_close_ledger.jsonl",
                close,
            )
        else:
            position["high_water_mark"] = decision["effective_high_water_mark"]
            updated_positions[symbol] = position

    total_realized_pnl = sum(float(row["realized_pnl"]) for row in close_records)
    body = {
        "stage": "V95.64",
        "stage_range": "V95.33-V95.64",
        "state": (
            "PAPER_POSITION_LIFECYCLE_EXIT_ACTIONS_READY"
            if close_records
            else "PAPER_POSITION_LIFECYCLE_HOLD"
        ),
        "status": "PASS",
        "lifecycle_date": lifecycle_date,
        "source_simulation_state": source.get("state"),
        "position_decisions": decisions,
        "close_records": close_records,
        "open_position_count": len(updated_positions),
        "closed_position_count": len(close_records),
        "total_realized_pnl": round(total_realized_pnl, 4),
        "updated_position_state": {"positions": updated_positions},
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
        "next_phase": "V96_01_PAPER_ACCOUNT_LEDGER",
    }
    body["position_lifecycle_certificate_sha256"] = digest_payload(body)

    write_json(
        root / "release/v95_33_to_v95_64/actual/paper_position_lifecycle_result.json",
        body,
    )
    write_json(prior_state_path, {"positions": updated_positions})
    append_jsonl(
        root / "release/v95_33_to_v95_64/actual/paper_position_lifecycle_ledger.jsonl",
        {
            "lifecycle_date": lifecycle_date,
            "state": body["state"],
            "open_position_count": body["open_position_count"],
            "closed_position_count": body["closed_position_count"],
            "total_realized_pnl": body["total_realized_pnl"],
        },
    )
    return body
