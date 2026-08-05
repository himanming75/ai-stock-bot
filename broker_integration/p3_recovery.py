from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def build_recovery_plan(result: dict[str, Any]) -> list[dict[str, Any]]:
    actions = []
    if result.get("unknown_order_states"):
        actions.append({
            "action": "HALT_NEW_ORDERS",
            "reason": "UNKNOWN_ORDER_STATE",
        })
    if result.get("position_drifts"):
        actions.append({
            "action": "REFRESH_BROKER_POSITIONS",
            "reason": "POSITION_RECONCILIATION_DRIFT",
        })
    if result.get("account_drifts"):
        actions.append({
            "action": "REFRESH_ACCOUNT_AND_LOCAL_PORTFOLIO",
            "reason": "ACCOUNT_RECONCILIATION_DRIFT",
        })
    if not actions:
        actions.append({
            "action": "CONTINUE_MONITORING",
            "reason": "RECONCILIATION_HEALTHY",
        })
    return actions


def write_checkpoint(
    path: Path,
    result: dict[str, Any],
) -> None:
    checkpoint = {
        "stage": "P3",
        "observed_at": result.get("observed_at"),
        "reconciliation_passed": result.get("reconciliation_passed"),
        "new_fill_count": result.get("new_fill_count"),
        "duplicate_fill_count": result.get("duplicate_fill_count"),
        "recovery_plan": build_recovery_plan(result),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
