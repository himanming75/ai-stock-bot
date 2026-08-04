from __future__ import annotations
from typing import Any
from daily_paper_runner.io import digest

def build_daily_plan(
    session: dict[str, Any],
    decision: dict[str, Any],
    portfolio: dict[str, Any],
    approval: dict[str, Any],
) -> dict[str, Any]:
    allocations = portfolio.get("allocation", {}).get("allocations", [])
    plan_rows = []
    for index, row in enumerate(allocations, start=1):
        strategy_id = row.get("strategy_id")
        weight = float(row.get("target_weight_pct", 0.0))
        plan_rows.append({
            "plan_number": index,
            "strategy_id": strategy_id,
            "target_weight_pct": weight,
            "paper_action": "SIMULATE_ALLOCATION",
            "state": (
                "AUTHORIZED_FOR_PAPER_SIMULATION"
                if approval.get("paper_simulation_authorized")
                else "BLOCKED"
            ),
            "plan_key": digest({
                "session_id": session.get("session_id"),
                "strategy_id": strategy_id,
                "weight": weight,
            }),
        })
    return {
        "session_id": session.get("session_id"),
        "session_date": session.get("session_date"),
        "source_decision": decision.get(
            "autonomous_decision", {}
        ).get("decision"),
        "plan_count": len(plan_rows),
        "plans": plan_rows,
        "paper_simulation_authorized": approval.get(
            "paper_simulation_authorized"
        ) is True,
    }
