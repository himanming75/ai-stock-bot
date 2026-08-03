from __future__ import annotations
from typing import Any

def final_position_multiplier(
    regime_multiplier: float,
    risk_approved: bool,
    confidence_score: float,
    conflict_detected: bool,
) -> float:
    multiplier = float(regime_multiplier)
    if not risk_approved:
        multiplier = min(multiplier, 0.25)
    if confidence_score < 50.0:
        multiplier *= 0.5
    elif confidence_score < 70.0:
        multiplier *= 0.8
    if conflict_detected:
        multiplier *= 0.8
    return round(max(0.0, min(1.0, multiplier)), 4)

def paper_decision(
    allocations: list[dict[str, Any]],
    multiplier: float,
    risk_approved: bool,
    checks_passed: bool,
) -> str:
    if not allocations or multiplier <= 0:
        return "NO_ACTION"
    if not risk_approved or not checks_passed:
        return "REVIEW_REQUIRED"
    if multiplier < 0.25:
        return "PAPER_TRADE_MINIMAL_EXPOSURE"
    if multiplier < 0.60:
        return "PAPER_TRADE_REDUCED_EXPOSURE"
    return "PAPER_TRADE_NORMAL_EXPOSURE"
