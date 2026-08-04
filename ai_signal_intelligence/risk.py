from __future__ import annotations


def calculate(components: dict[str, float], action: str) -> tuple[int, str]:
    score = components["volatility"] * 55.0
    if components["volume_ratio"] >= 2.5:
        score += 15.0
    if action == "BUY" and components["rsi"] >= 70:
        score += 20.0
    if action == "SELL" and components["rsi"] <= 30:
        score += 20.0
    value = int(round(max(0.0, min(100.0, score))))
    level = "HIGH" if value >= 65 else "MEDIUM" if value >= 35 else "LOW"
    return value, level
