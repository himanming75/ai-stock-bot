from __future__ import annotations

def val(record: dict, key: str, default=0.0) -> float:
    value = record.get(key)
    return default if value is None else float(value)

def clamp(value: float, low=-100.0, high=100.0) -> float:
    return max(low, min(high, value))

def signal(score: float, threshold=20.0) -> str:
    if score >= threshold:
        return "BULLISH"
    if score <= -threshold:
        return "BEARISH"
    return "NEUTRAL"
