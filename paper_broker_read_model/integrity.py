from __future__ import annotations
from typing import Any

def evaluate_integrity(
    account_reconciliation: dict[str, Any],
    position_reconciliation: dict[str, Any],
    freshness: dict[str, Any],
    adapter_result: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "account_reconciled": account_reconciliation.get("passed") is True,
        "positions_reconciled": position_reconciliation.get("passed") is True,
        "snapshot_fresh": freshness.get("passed") is True,
        "safe_boundary_passed": (
            adapter_result.get("safe_api_boundary", {}).get("passed") is True
        ),
        "read_only_adapter": adapter_result.get("read_only_adapter") is True,
        "credentials_unused": (
            adapter_result.get("actual_credentials_used") is False
        ),
        "network_unused": (
            adapter_result.get("actual_external_network_used") is False
        ),
        "orders_zero": adapter_result.get("actual_orders_submitted") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
    }
