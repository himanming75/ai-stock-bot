from __future__ import annotations
from typing import Any

def evaluate_iteration_gates(
    sources: dict[str, Any],
    selected_session: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    decision = sources["decision"]
    risk = sources["risk"]
    adaptive = sources["adaptive_rebalance"]
    session = selected_session.get("session") or {}

    checks = {
        "session_available": selected_session.get("session_available") is True,
        "manual_approval_guard": decision.get(
            "manual_approval_required", True
        ) is True,
        "approval_not_granted": decision.get(
            "approval_gate", {}
        ).get("approval_granted", False) is False,
        "execution_not_authorized": decision.get(
            "execution_authorized", False
        ) is False,
        "risk_gate_passed": risk.get(
            "pre_execution_gate", {}
        ).get("passed") is True,
        "adaptive_gate_passed": adaptive.get(
            "optimization_gate", {}
        ).get("passed") is True,
        "session_orders_zero": session.get("actual_orders_submitted", 0) == 0,
        "paper_only": session.get("paper_only", True) is True,
        "maximum_iteration_count_valid": int(
            policy.get("maximum_iterations_per_run", 1)
        ) >= 1,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"passed":not failed,"checks":checks,"failed":failed}
