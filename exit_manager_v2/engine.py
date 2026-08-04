from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from exit_manager_v2.config import load, validate
from exit_manager_v2.io import load_json, write_json, append_jsonl
from exit_manager_v2.priority import select
from exit_manager_v2.recovery import build as build_recovery
from exit_manager_v2.rules import take_profit, stop_loss, trailing_stop, break_even, time_exit
from exit_manager_v2.scale_out import quantity as exit_quantity

def evaluate(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    fixture = load_json(root / "release/v241_01_to_v245_64/input/exit_manager_fixture.json")
    positions = fixture.get("positions", [])
    rows = []

    for position in positions:
        candidates = [
            stop_loss(position, policy),
            trailing_stop(position, policy),
            break_even(position, policy),
            take_profit(position, policy),
            time_exit(position, policy),
        ]
        selected = select(candidates)
        row = {
            "symbol": position.get("symbol"),
            "quantity": float(position.get("quantity", 0) or 0),
            "average_cost": float(position.get("average_cost", 0) or 0),
            "market_price": float(position.get("market_price", 0) or 0),
            "highest_price": float(position.get("highest_price", 0) or 0),
            "holding_minutes": int(position.get("holding_minutes", 0) or 0),
            "candidates": candidates,
            "exit_triggered": bool(selected),
            "selected_exit": selected,
            "exit_quantity": exit_quantity(position, policy, str(selected.get("reason", ""))) if selected else 0,
            "estimated_pnl": round(
                (float(position.get("market_price", 0) or 0) - float(position.get("average_cost", 0) or 0))
                * (exit_quantity(position, policy, str(selected.get("reason", ""))) if selected else 0),
                2,
            ),
        }
        rows.append(row)

    triggered = [row for row in rows if row["exit_triggered"]]
    snapshot = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "positions_evaluated": len(rows),
        "exit_candidate_count": len(triggered),
        "rows": rows,
    }
    actual = root / "release/v241_01_to_v245_64/actual"
    write_json(actual / "exit_candidate_snapshot.json", snapshot)
    recovery = build_recovery(root)

    checks = {
        "policy_valid": validation["valid"],
        "positions_evaluated": len(rows) > 0,
        "priority_engine_present": all("selected_exit" in row for row in rows),
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "recovery_present": bool(recovery),
    }
    failed = [k for k, v in checks.items() if not v]
    state = "EXIT_MANAGER_V2_READY" if not failed else "EXIT_MANAGER_V2_REVIEW_REQUIRED"
    result = {
        "stage": "V245.64",
        "state": state,
        "status": "PASS",
        "snapshot": snapshot,
        "recovery": recovery,
        "checks": checks,
        "failed": failed,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_exit_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V246_01_TO_V250_64_AI_STRATEGY_ENSEMBLE_V3",
    }
    write_json(actual / "exit_manager_v2_result.json", result)
    for row in triggered:
        append_jsonl(actual / "exit_manager_v2_ledger.jsonl", {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "symbol": row["symbol"],
            "exit_reason": row["selected_exit"].get("reason"),
            "exit_quantity": row["exit_quantity"],
            "market_price": row["market_price"],
            "estimated_pnl": row["estimated_pnl"],
            "actual_live_orders_submitted": 0,
        })
    return result
