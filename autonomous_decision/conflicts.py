from __future__ import annotations
from typing import Any

def detect_conflicts(signals: dict[str, Any]) -> dict[str, Any]:
    conflicts = []
    if signals.get("regime_conflict"):
        conflicts.append("MULTI_TIMEFRAME_REGIME_CONFLICT")
    if signals.get("meta_risk_approved") and not signals.get("risk_gate_passed"):
        conflicts.append("META_APPROVED_RISK_REJECTED")
    if (
        signals.get("actionable_adjustment_count", 0) > 0
        and signals.get("adaptive_state") == "ADAPTIVE_REBALANCE_OPTIMIZATION_NO_ACTION"
    ):
        conflicts.append("ADJUSTMENT_COUNT_STATE_CONFLICT")
    if (
        signals.get("target_gross_exposure_pct", 0.0) <= 0.0
        and signals.get("actionable_adjustment_count", 0) > 0
    ):
        conflicts.append("ZERO_EXPOSURE_WITH_ACTIONS")
    return {
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "passed": not conflicts,
    }
