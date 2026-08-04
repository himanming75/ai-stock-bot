from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from position_manager_v2.config import load, validate
from position_manager_v2.exposure import calculate
from position_manager_v2.io import load_json, write_json, append_jsonl
from position_manager_v2.positions import apply_buy, apply_sell, mark
from position_manager_v2.recovery import build as build_recovery

def evaluate(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    fixture = load_json(root / "release/v236_01_to_v240_64/input/position_manager_fixture.json")
    cash = float(fixture.get("cash", 0) or 0)
    positions = []

    for row in fixture.get("positions", []):
        position = {
            "symbol": row.get("symbol"),
            "sector": row.get("sector", "UNKNOWN"),
            "quantity": 0.0,
            "average_cost": 0.0,
            "realized_pnl": 0.0,
        }
        for event in row.get("events", []):
            if str(event.get("side", "")).upper() == "BUY":
                position = apply_buy(position, event.get("quantity", 0), event.get("price", 0))
            else:
                position = apply_sell(position, event.get("quantity", 0), event.get("price", 0))
        position = mark(position, row.get("market_price", 0))
        if position["quantity"] > 0:
            positions.append(position)

    exposure = calculate(positions, cash)
    open_positions = len(positions)
    max_symbol = max([x["weight_pct"] for x in exposure["symbol_exposure"]] or [0])
    max_sector = max([x["weight_pct"] for x in exposure["sector_exposure"]] or [0])

    checks = {
        "policy_valid": validation["valid"],
        "position_count_within_limit": open_positions <= int(policy["maximum_positions"]),
        "symbol_exposure_within_limit": max_symbol <= float(policy["maximum_symbol_weight_pct"]),
        "sector_exposure_within_limit": max_sector <= float(policy["maximum_sector_weight_pct"]),
        "cash_buffer_within_limit": exposure["cash_weight_pct"] >= float(policy["minimum_cash_buffer_pct"]),
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [k for k, v in checks.items() if not v]
    state = "POSITION_MANAGER_V2_READY" if not failed else "POSITION_MANAGER_V2_REVIEW_REQUIRED"

    snapshot = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "positions": positions,
        "exposure": exposure,
        "open_position_count": open_positions,
        "total_realized_pnl": round(sum(float(p.get("realized_pnl", 0) or 0) for p in positions), 2),
        "total_unrealized_pnl": round(sum(float(p.get("unrealized_pnl", 0) or 0) for p in positions), 2),
    }
    actual = root / "release/v236_01_to_v240_64/actual"
    write_json(actual / "position_snapshot.json", snapshot)
    recovery = build_recovery(root)

    result = {
        "stage": "V240.64",
        "state": state,
        "status": "PASS",
        "positions": positions,
        "exposure": exposure,
        "snapshot": snapshot,
        "recovery": recovery,
        "checks": checks,
        "failed": failed,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V241_01_TO_V245_64_EXIT_MANAGER_V2",
    }
    write_json(actual / "position_manager_v2_result.json", result)
    append_jsonl(actual / "position_manager_v2_ledger.jsonl", {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "state": state,
        "open_position_count": open_positions,
        "equity": exposure["equity"],
        "total_unrealized_pnl": snapshot["total_unrealized_pnl"],
        "actual_live_orders_submitted": 0,
    })
    return result
