from __future__ import annotations
from typing import Any

def selection_reasons(features: dict[str, Any]) -> list[dict[str, Any]]:
    reasons = []
    if features.get("stability_passed"):
        reasons.append({
            "importance": "high",
            "factor": "walk_forward_stability",
            "message": (
                f'{features.get("positive_window_pct", 0):.2f}% of walk-forward '
                "windows were profitable and the stability gate passed."
            ),
        })
    if float(features.get("sharpe_ratio", 0.0)) > 0:
        reasons.append({
            "importance": "high",
            "factor": "risk_adjusted_return",
            "message": (
                f'Sharpe ratio was {features.get("sharpe_ratio", 0):.2f}, '
                "indicating positive risk-adjusted performance."
            ),
        })
    if float(features.get("total_return_pct", 0.0)) > 0:
        reasons.append({
            "importance": "medium",
            "factor": "positive_total_return",
            "message": (
                f'Total return was {features.get("total_return_pct", 0):.2f}%.'
            ),
        })
    if float(features.get("maximum_drawdown_pct", 0.0)) <= 20:
        reasons.append({
            "importance": "medium",
            "factor": "controlled_drawdown",
            "message": (
                f'Maximum drawdown was limited to '
                f'{features.get("maximum_drawdown_pct", 0):.2f}%.'
            ),
        })
    if int(features.get("total_trades", 0)) >= 2:
        reasons.append({
            "importance": "low",
            "factor": "minimum_trade_evidence",
            "message": (
                f'The configuration produced {features.get("total_trades", 0)} '
                "completed trades."
            ),
        })
    return reasons

def risk_factors(features: dict[str, Any]) -> list[dict[str, Any]]:
    risks = []
    if int(features.get("total_trades", 0)) < 10:
        risks.append({
            "severity": "medium",
            "factor": "small_trade_sample",
            "message": (
                f'Only {features.get("total_trades", 0)} completed trades were '
                "available, so statistical confidence remains limited."
            ),
        })
    if float(features.get("worst_window_return_pct", 0.0)) < 0:
        risks.append({
            "severity": "medium",
            "factor": "negative_walk_forward_window",
            "message": (
                f'The worst walk-forward window returned '
                f'{features.get("worst_window_return_pct", 0):.2f}%.'
            ),
        })
    if float(features.get("positive_window_pct", 0.0)) < 75:
        risks.append({
            "severity": "medium",
            "factor": "inconsistent_windows",
            "message": (
                f'Positive windows were '
                f'{features.get("positive_window_pct", 0):.2f}%, below a strong '
                "consistency level of 75%."
            ),
        })
    if float(features.get("profit_factor", 0.0)) < 1.5:
        risks.append({
            "severity": "medium",
            "factor": "moderate_profit_factor",
            "message": (
                f'Profit factor was {features.get("profit_factor", 0):.2f}.'
            ),
        })
    if float(features.get("worst_window_drawdown_pct", 0.0)) > 20:
        risks.append({
            "severity": "high",
            "factor": "window_drawdown",
            "message": (
                f'Worst walk-forward drawdown reached '
                f'{features.get("worst_window_drawdown_pct", 0):.2f}%.'
            ),
        })
    if not features.get("stability_passed"):
        risks.append({
            "severity": "high",
            "factor": "stability_gate_failed",
            "message": (
                "The stability gate failed: "
                + ", ".join(features.get("stability_failed_checks", []))
            ),
        })
    return risks
