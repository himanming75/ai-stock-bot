from __future__ import annotations
from typing import Any

def strategy_description(strategy_id: str, parameters: dict[str, Any]) -> str:
    if strategy_id.startswith("MOMENTUM"):
        return (
            f'This momentum strategy uses a {parameters.get("period", "?")}-bar '
            "lookback and enters when momentum changes from non-positive to "
            "positive, then exits when momentum reverses."
        )
    if strategy_id.startswith("EMA"):
        return (
            f'This EMA crossover strategy compares fast period '
            f'{parameters.get("fast", "?")} with slow period '
            f'{parameters.get("slow", "?")}.'
        )
    if strategy_id.startswith("RSI"):
        return (
            f'This RSI strategy uses period {parameters.get("period", "?")} '
            f'with thresholds {parameters.get("oversold", "?")} and '
            f'{parameters.get("overbought", "?")}.'
        )
    if strategy_id.startswith("BOLLINGER"):
        return (
            f'This Bollinger strategy uses period '
            f'{parameters.get("period", "?")} and standard-deviation multiplier '
            f'{parameters.get("std", "?")}.'
        )
    return "This configuration uses the registered strategy rules."

def build_summary(
    features: dict[str, Any],
    reasons: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    confidence: dict[str, Any],
) -> str:
    strategy = features.get("strategy_id") or "Unknown strategy"
    parameters = features.get("parameters", {})
    status = (
        "passed the walk-forward stability gate"
        if features.get("stability_passed")
        else "did not pass the walk-forward stability gate"
    )
    risk_text = (
        f'{len(risks)} risk factor(s) remain.'
        if risks else "No material rule-based risk factors were identified."
    )
    return (
        f'{strategy} with parameters {parameters} {status}. '
        f'It produced {features.get("total_return_pct", 0):.2f}% total return, '
        f'{features.get("maximum_drawdown_pct", 0):.2f}% maximum drawdown, '
        f'and {features.get("positive_window_pct", 0):.2f}% positive '
        f'walk-forward windows. Confidence is {confidence.get("level")} '
        f'({confidence.get("score"):.2f}/100). {risk_text}'
    )
