from __future__ import annotations
from typing import Any

def build_report(
    state: str,
    session: dict[str, Any],
    preflight: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "state": state,
        "session_id": session.get("session_id"),
        "session_date": session.get("session_date"),
        "preflight_passed": preflight.get("passed"),
        "paper_simulation_authorized": approval.get(
            "paper_simulation_authorized"
        ),
        "live_execution_authorized": False,
        "planned_strategy_count": plan.get("plan_count", 0),
        "authorized_plan_count": sum(
            1 for row in plan.get("plans", [])
            if row.get("state") == "AUTHORIZED_FOR_PAPER_SIMULATION"
        ),
        "actual_broker_orders_submitted": 0,
        "paper_only": True,
    }
