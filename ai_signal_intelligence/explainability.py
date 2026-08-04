from __future__ import annotations


def explain(action: str, components: dict[str, float], patterns: list[str], regime: str) -> list[str]:
    reasons = [f"Market regime is {regime}."]
    reasons.append(f"Trend component is {components['trend']:.3f}.")
    reasons.append(f"Momentum component is {components['momentum']:.3f}; RSI is {components['rsi']:.1f}.")
    reasons.append(f"Relative volume is {components['volume_ratio']:.2f}.")
    reasons.append(f"MACD component is {components['macd']:.3f}.")
    if patterns:
        reasons.append("Detected patterns: " + ", ".join(patterns) + ".")
    reasons.append(f"Final analytical action is {action}; no order can be submitted.")
    return reasons
