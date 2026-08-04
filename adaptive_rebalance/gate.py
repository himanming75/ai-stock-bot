from __future__ import annotations
from typing import Any

def evaluate_gate(
    optimized_rows: list[dict[str, Any]],
    stability: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    actionable = [row for row in optimized_rows if row.get("state") == "OPTIMIZED"]
    checks = {
        "stability_passed": stability.get("passed") is True,
        "adjustment_count_limit": len(actionable) <= int(
            policy.get("maximum_optimized_adjustments", 10)
        ),
        "submission_disabled": all(
            row.get("submission_allowed") is False for row in optimized_rows
        ),
        "positive_net_benefit": all(
            float(row.get("net_benefit", 0.0)) > 0.0 for row in actionable
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
        "actionable_count": len(actionable),
    }
