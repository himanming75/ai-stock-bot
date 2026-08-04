from __future__ import annotations
from typing import Any

WORKFLOW_ORDER = [
    "MARKET_REGIME",
    "META_STRATEGY",
    "PAPER_ACCOUNT",
    "PORTFOLIO_MANAGER",
    "AI_RISK_MANAGER",
    "RISK_BUDGET",
    "REBALANCE_CONTROL",
    "ADAPTIVE_REBALANCE",
]

def build_workflow(modules: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {row["module_id"]: row for row in modules}
    steps = []
    blocked = False
    for index, module_id in enumerate(WORKFLOW_ORDER, start=1):
        module = lookup.get(module_id, {})
        ready = bool(module.get("ready"))
        state = "READY" if ready and not blocked else "BLOCKED"
        if not ready:
            blocked = True
            state = "SOURCE_NOT_READY"
        steps.append({
            "step": index,
            "module_id": module_id,
            "state": state,
            "source_state": module.get("state"),
            "source_status": module.get("status"),
        })
    return {
        "workflow_order": WORKFLOW_ORDER,
        "steps": steps,
        "ready_step_count": sum(1 for row in steps if row["state"] == "READY"),
        "blocked_step_count": sum(1 for row in steps if row["state"] != "READY"),
        "passed": all(row["state"] == "READY" for row in steps),
    }
