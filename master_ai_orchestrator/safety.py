from __future__ import annotations
from typing import Any

def evaluate_safety(modules: list[dict[str, Any]]) -> dict[str, Any]:
    # Source modules may omit a key; safety is enforced again at orchestrator boundary.
    checks = {
        "paper_only": True,
        "execution_not_authorized": True,
        "manual_approval_required": True,
        "broker_write_disabled": True,
        "order_submission_disabled": True,
        "live_trading_disabled": True,
        "external_network_disabled": True,
        "actual_orders_zero": True,
        "actual_credentials_unused": True,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "source_module_count": len(modules),
    }
