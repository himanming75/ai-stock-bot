from __future__ import annotations
from typing import Any

def evaluate_integrity(
    duplicate_fill_ids: list[str],
    cash_reconciliation: dict[str, Any],
    position_reconciliation: dict[str, Any],
    equity_reconciliation: dict[str, Any],
    realized_pnl: float,
    unrealized_pnl: float,
) -> dict[str, Any]:
    checks = {
        "no_duplicate_fill_ids": not duplicate_fill_ids,
        "cash_reconciled": cash_reconciliation.get("passed") is True,
        "positions_reconciled": position_reconciliation.get("passed") is True,
        "equity_reconciled": equity_reconciliation.get("passed") is True,
        "realized_pnl_numeric": isinstance(realized_pnl, (int, float)),
        "unrealized_pnl_numeric": isinstance(unrealized_pnl, (int, float)),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
    }
