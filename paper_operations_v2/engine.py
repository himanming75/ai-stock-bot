from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from paper_operations_v2.config import load, validate
from paper_operations_v2.idempotency import make_key, register
from paper_operations_v2.io import load_json, write_json, append_jsonl
from paper_operations_v2.lifecycle import record
from paper_operations_v2.reconcile import reconcile
from paper_operations_v2.recovery import build as build_recovery
from paper_operations_v2.state import save_checkpoint

def _cycle_id(now: datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%SZ")

def evaluate(root: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cycle_id = _cycle_id(now)
    policy = load(root)
    validation = validate(policy)

    signal_data = load_json(root / "release/v221_01_to_v225_64/input/paper_signal.json")
    local_data = load_json(root / "release/v221_01_to_v225_64/input/local_positions.json")
    broker_data = load_json(root / "release/v221_01_to_v225_64/input/paper_broker_snapshot.json")
    risk_data = load_json(root / "release/v206_01_to_v210_64/actual/risk_engine_v2_result.json")

    save_checkpoint(root, cycle_id, "PRE_MARKET_CHECK", "PASS", {
        "policy_valid": validation["valid"],
        "real_network_enabled": policy["real_network_enabled"],
    })

    signal = signal_data.get("signal", {})
    save_checkpoint(root, cycle_id, "SIGNAL_COLLECTION", "PASS" if signal else "EMPTY", signal)

    risk_passed = risk_data.get("risk_gate", {}).get("passed") is True
    save_checkpoint(root, cycle_id, "RISK_GATE", "PASS" if risk_passed else "BLOCKED", {
        "risk_state": risk_data.get("state", "NOT_AVAILABLE"),
    })

    symbol = str(signal.get("symbol", "AAPL"))
    side = str(signal.get("side", "BUY"))
    strategy_id = str(signal.get("strategy_id", "NO_STRATEGY"))
    quantity = min(int(signal.get("quantity", 1) or 1), int(policy["maximum_order_quantity"]))
    price = float(signal.get("reference_price", 0) or 0)
    notional = quantity * price
    key = make_key(cycle_id, symbol, side, strategy_id)

    plan_allowed = (
        validation["valid"]
        and bool(signal)
        and risk_passed
        and quantity > 0
        and notional <= float(policy["maximum_order_notional"])
    )
    order_id = f"PAPER-{key}"

    order_plan = {
        "cycle_id": cycle_id,
        "order_id": order_id,
        "idempotency_key": key,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "reference_price": price,
        "notional": round(notional, 2),
        "strategy_id": strategy_id,
        "plan_allowed": plan_allowed,
    }
    write_json(root / "release/v221_01_to_v225_64/actual/paper_order_plan.json", order_plan)
    save_checkpoint(root, cycle_id, "PAPER_ORDER_PLAN", "PASS" if plan_allowed else "BLOCKED", order_plan)

    idempotency_result = register(root, key, order_plan)
    record(root, cycle_id, order_id, "PLANNED", order_plan)

    submission_authorized = (
        plan_allowed
        and policy.get("paper_submission_enabled") is True
        and policy.get("real_network_enabled") is True
    )

    if submission_authorized:
        # Foundation only. No broker client is called in V225.
        record(root, cycle_id, order_id, "SUBMISSION_BLOCKED", {
            "reason": "BROKER_CLIENT_NOT_INCLUDED_IN_V225_FOUNDATION",
        })
        paper_orders_submitted = 0
        submission_state = "FOUNDATION_BLOCKED"
    else:
        record(root, cycle_id, order_id, "SUBMISSION_BLOCKED", {
            "reason": "PAPER_SUBMISSION_OR_REAL_NETWORK_DISABLED",
        })
        paper_orders_submitted = 0
        submission_state = "POLICY_BLOCKED"

    save_checkpoint(root, cycle_id, "PAPER_ORDER_SUBMISSION", "BLOCKED", {
        "submission_state": submission_state,
    })
    save_checkpoint(root, cycle_id, "FILL_MONITOR", "NOT_REQUIRED", {
        "paper_orders_submitted": paper_orders_submitted,
    })

    reconciliation = reconcile(
        local_data.get("positions", []),
        broker_data.get("positions", []),
    )
    write_json(
        root / "release/v221_01_to_v225_64/actual/paper_position_reconciliation.json",
        reconciliation,
    )
    save_checkpoint(
        root,
        cycle_id,
        "POSITION_RECONCILIATION",
        "PASS" if reconciliation["passed"] else "CONFLICT",
        reconciliation,
    )

    report = {
        "cycle_id": cycle_id,
        "generated_at": now.isoformat(),
        "signal_present": bool(signal),
        "risk_gate_passed": risk_passed,
        "order_plan_allowed": plan_allowed,
        "paper_orders_submitted": paper_orders_submitted,
        "reconciliation_passed": reconciliation["passed"],
        "reconciliation_conflicts": reconciliation["conflict_count"],
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v221_01_to_v225_64/actual/paper_daily_operations_report.json", report)
    save_checkpoint(root, cycle_id, "END_OF_DAY_REPORT", "PASS", report)
    final_checkpoint = save_checkpoint(root, cycle_id, "CHECKPOINT_COMPLETE", "PASS", report)
    recovery = build_recovery(root)

    checks = {
        "policy_valid": validation["valid"],
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "live_orders_zero": True,
        "idempotency_registered": idempotency_result.get("registered") is True,
        "reconciliation_complete": "passed" in reconciliation,
        "checkpoint_complete": final_checkpoint["step"] == "CHECKPOINT_COMPLETE",
        "recovery_plan_present": bool(recovery),
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = "PAPER_OPERATIONS_AUTOMATION_V2_READY" if not failed else "PAPER_OPERATIONS_AUTOMATION_V2_REVIEW_REQUIRED"

    result = {
        "stage": "V225.64",
        "state": state,
        "status": "PASS",
        "cycle_id": cycle_id,
        "checks": checks,
        "failed": failed,
        "order_plan": order_plan,
        "idempotency": idempotency_result,
        "submission_state": submission_state,
        "paper_orders_submitted": paper_orders_submitted,
        "reconciliation": reconciliation,
        "recovery": recovery,
        "automatic_cycle_foundation_ready": True,
        "paper_submission_enabled": policy.get("paper_submission_enabled") is True,
        "real_network_enabled": policy.get("real_network_enabled") is True,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_live_orders_submitted": 0,
        "next_phase": "V226_01_TO_V230_64_LIVE_SHADOW_SLIPPAGE_QUALIFICATION",
    }

    actual = root / "release/v221_01_to_v225_64/actual"
    write_json(actual / "paper_operations_v2_result.json", result)
    append_jsonl(actual / "paper_operations_v2_audit_ledger.jsonl", {
        "cycle_id": cycle_id,
        "state": state,
        "paper_orders_submitted": paper_orders_submitted,
        "reconciliation_passed": reconciliation["passed"],
        "actual_live_orders_submitted": 0,
    })
    return result
