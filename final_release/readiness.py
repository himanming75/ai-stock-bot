from __future__ import annotations
from typing import Any

def evaluate_readiness(
    integration: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "integration_ready": (
            integration.get("state") == "FINAL_SYSTEM_INTEGRATION_READY"
        ),
        "integration_status_pass": integration.get("status") == "PASS",
        "release_eligible": integration.get("final_release_eligible") is True,
        "readiness_score": float(
            integration.get("readiness", {}).get("readiness_score", 0.0)
        ) >= float(policy.get("minimum_readiness_score", 95.0)),
        "all_modules_ready": (
            integration.get("readiness", {}).get("ready_module_count")
            == integration.get("readiness", {}).get("module_count")
        ),
        "pipeline_passed": integration.get("pipeline", {}).get("passed") is True,
        "safety_passed": integration.get("safety", {}).get("passed") is True,
        "actual_orders_zero": integration.get("actual_orders_submitted", 0) == 0,
        "execution_not_authorized": (
            integration.get("execution_authorized") is False
        ),
        "paper_only": integration.get("paper_only") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
        "readiness_score": integration.get(
            "readiness", {}
        ).get("readiness_score"),
        "ready_module_count": integration.get(
            "readiness", {}
        ).get("ready_module_count"),
        "module_count": integration.get(
            "readiness", {}
        ).get("module_count"),
        "pipeline_ready_steps": integration.get(
            "pipeline", {}
        ).get("ready_steps"),
        "pipeline_total_steps": integration.get(
            "pipeline", {}
        ).get("total_steps"),
    }
