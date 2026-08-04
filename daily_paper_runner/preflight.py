from __future__ import annotations
from typing import Any

def evaluate_preflight(
    final_release: dict[str, Any],
    scheduler: dict[str, Any],
    continuous_runtime: dict[str, Any],
    selected_session: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    session = selected_session.get("session") or {}
    checks = {
        "final_release_complete": (
            final_release.get("state")
            == "PRODUCTION_READINESS_FINAL_RELEASE_COMPLETE"
        ),
        "paper_trading_ready": final_release.get("paper_trading_ready") is True,
        "live_trading_disabled": final_release.get("live_trading_ready") is False,
        "scheduler_ready": scheduler.get("state") == "MULTI_DAY_SCHEDULER_READY",
        "runtime_ready": (
            continuous_runtime.get("state")
            == "CONTINUOUS_SERVICE_RUNTIME_READY"
        ),
        "session_available": selected_session.get("session_available") is True,
        "session_paper_only": session.get("paper_only", True) is True,
        "actual_orders_zero": session.get("actual_orders_submitted", 0) == 0,
        "paper_auto_approval_enabled": (
            policy.get("paper_auto_approval_enabled") is True
        ),
        "live_auto_approval_disabled": (
            policy.get("live_auto_approval_enabled") is False
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {"passed": not failed, "checks": checks, "failed": failed}
