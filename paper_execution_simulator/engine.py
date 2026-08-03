from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import random
from typing import Any

from paper_execution_simulator.io import load_json, write_json, append_jsonl, digest_payload
from paper_execution_simulator.cycle import build_cycle_id, read_completed_cycles
from paper_execution_simulator.fills import simulate_fill
from paper_execution_simulator.portfolio import apply_fill, mark_to_market

def simulate(root: Path, simulation_date: str = "") -> dict[str, Any]:
    policy = load_json(
        root / "release/v95_01_to_v95_32/input/paper_execution_simulator_policy.json"
    )
    source = load_json(
        root / "release/v94_33_to_v94_64/actual/paper_execution_plan.json"
    )
    prices = load_json(
        root / "release/v95_01_to_v95_32/input/simulation_mark_prices.json"
    )
    ledger_path = root / "release/v95_01_to_v95_32/actual/paper_execution_cycle_ledger.jsonl"

    plans = source.get("paper_order_plans", [])
    eligible = [row for row in plans if row.get("state") == "PLANNED"]
    if not eligible:
        return {
            "stage": "V95.32",
            "stage_range": "V95.01-V95.32",
            "state": "PAPER_EXECUTION_SIMULATOR_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    if not simulation_date:
        simulation_date = datetime.now(timezone.utc).date().isoformat()

    cycle_id = build_cycle_id(source, simulation_date)
    prior_lines = ledger_path.read_text(encoding="utf-8").splitlines() if ledger_path.exists() else []
    completed_cycles = read_completed_cycles(prior_lines)
    duplicate_cycle = cycle_id in completed_cycles

    if duplicate_cycle:
        body = {
            "stage": "V95.32",
            "stage_range": "V95.01-V95.32",
            "state": "PAPER_EXECUTION_SIMULATION_DUPLICATE_CYCLE_BLOCKED",
            "status": "PASS",
            "simulation_date": simulation_date,
            "cycle_id": cycle_id,
            "duplicate_cycle": True,
            "fills": [],
            "actual_orders_submitted": 0,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "next_phase": "V95_01_WAIT_NEW_SIMULATION_DATE",
        }
        body["paper_simulation_certificate_sha256"] = digest_payload(body)
        write_json(root / "release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json", body)
        return body

    initial_cash = float(policy.get("initial_cash", 100000.0))
    cash = initial_cash
    positions: dict[str, dict[str, float]] = {}
    rng = random.Random(int(policy.get("random_seed", 950132)))
    fills = []

    for index, plan in enumerate(eligible, 1):
        fill = simulate_fill(plan, policy, rng)
        cash, positions = apply_fill(cash, positions, plan, fill)
        record = {
            "fill_id": f"{cycle_id}-{index:03d}",
            "cycle_id": cycle_id,
            "strategy_id": plan.get("strategy_id"),
            "symbol": plan.get("symbol"),
            "side": plan.get("side"),
            **fill,
        }
        fills.append(record)
        append_jsonl(
            root / "release/v95_01_to_v95_32/actual/paper_fill_ledger.jsonl",
            record,
        )

    portfolio = mark_to_market(
        cash,
        positions,
        {str(k): float(v) for k, v in prices.items()},
    )
    filled_count = sum(1 for row in fills if row["state"] == "FILLED")
    partial_count = sum(1 for row in fills if row["state"] == "PARTIALLY_FILLED")
    not_filled_count = sum(1 for row in fills if row["state"] == "NOT_FILLED")
    total_commission = sum(float(row["commission"]) for row in fills)
    total_gross_notional = sum(float(row["gross_notional"]) for row in fills)

    body = {
        "stage": "V95.32",
        "stage_range": "V95.01-V95.32",
        "state": "PAPER_EXECUTION_SIMULATION_COMPLETED",
        "status": "PASS",
        "simulation_date": simulation_date,
        "cycle_id": cycle_id,
        "duplicate_cycle": False,
        "source_plan_state": source.get("state"),
        "source_plan_count": len(eligible),
        "fills": fills,
        "fill_summary": {
            "filled_count": filled_count,
            "partial_fill_count": partial_count,
            "not_filled_count": not_filled_count,
            "total_commission": round(total_commission, 4),
            "total_gross_notional": round(total_gross_notional, 4),
        },
        "portfolio": portfolio,
        "initial_cash": initial_cash,
        "ending_cash": portfolio["cash"],
        "ending_equity": portfolio["equity"],
        "simulated_orders_processed": len(eligible),
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
        "next_phase": "V95_33_PAPER_POSITION_LIFECYCLE",
    }
    body["paper_simulation_certificate_sha256"] = digest_payload(body)

    write_json(
        root / "release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json",
        body,
    )
    append_jsonl(ledger_path, {
        "cycle_id": cycle_id,
        "simulation_date": simulation_date,
        "cycle_state": "COMPLETED",
        "ending_equity": portfolio["equity"],
        "fill_count": len(fills),
    })
    return body
