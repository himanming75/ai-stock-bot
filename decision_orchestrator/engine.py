from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_orchestrator.io import load_json, write_json, append_jsonl, digest_payload
from decision_orchestrator.planning import build_order_plan
from decision_orchestrator.dedup import apply_duplicate_protection
from decision_orchestrator.gates import evaluate_gates
from decision_orchestrator.checklist import build_checklist

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v94_33_to_v94_64/input/decision_orchestration_policy.json"
    )
    meta = load_json(
        root / "release/v94_01_to_v94_32/actual/meta_strategy_result.json"
    )
    prices = load_json(
        root / "release/v94_33_to_v94_64/input/reference_prices.json"
    )
    ledger_path = root / "release/v94_33_to_v94_64/actual/paper_execution_plan_ledger.jsonl"

    allocations = meta.get("strategy_allocations", [])
    if not allocations:
        return {
            "stage": "V94.64",
            "stage_range": "V94.33-V94.64",
            "state": "DECISION_ORCHESTRATION_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    portfolio_value = float(policy.get("planning_portfolio_value", 100000.0))
    multiplier = float(meta.get("final_position_multiplier", 0.0))
    plans = build_order_plan(
        allocations,
        portfolio_value,
        multiplier,
        {str(k): float(v) for k, v in prices.items()},
        policy,
    )

    prior_keys = set()
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                value = __import__("json").loads(line)
                key = value.get("plan_key")
                if key:
                    prior_keys.add(str(key))
            except Exception:
                pass

    plans = apply_duplicate_protection(plans, prior_keys)
    gates = evaluate_gates(meta, plans, policy)
    checklist = build_checklist(gates, plans)
    manual_approval_required = True
    executable = False

    state = (
        "PAPER_EXECUTION_PLAN_READY_FOR_MANUAL_APPROVAL"
        if gates["passed"]
        else "PAPER_EXECUTION_PLAN_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V94.64",
        "stage_range": "V94.33-V94.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_meta_state": meta.get("state"),
        "source_paper_decision": meta.get("paper_decision"),
        "planning_portfolio_value": portfolio_value,
        "source_position_multiplier": multiplier,
        "paper_order_plans": plans,
        "gates": gates,
        "pre_execution_checklist": checklist,
        "manual_approval_required": manual_approval_required,
        "execution_authorized": executable,
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
        "next_phase": "V95_01_PAPER_EXECUTION_SIMULATOR",
    }
    body["decision_orchestration_certificate_sha256"] = digest_payload(body)

    write_json(
        root / "release/v94_33_to_v94_64/actual/paper_execution_plan.json",
        body,
    )
    for row in plans:
        append_jsonl(ledger_path, {
            "observed_at": body["observed_at"],
            "plan_key": row.get("plan_key"),
            "strategy_id": row.get("strategy_id"),
            "symbol": row.get("symbol"),
            "quantity": row.get("quantity"),
            "state": row.get("state"),
        })
    return body
