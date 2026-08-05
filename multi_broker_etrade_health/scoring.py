from __future__ import annotations
from .models import HealthSignal


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, value))


def weighted_score(signals: list[HealthSignal]) -> int:
    if not signals:
        return 0
    weighted_total = sum(signal.score * signal.weight for signal in signals)
    weight_total = sum(signal.weight for signal in signals)
    return clamp(round(weighted_total / weight_total))


def health_band(score: int) -> str:
    if score >= 90:
        return "HEALTHY"
    if score >= 75:
        return "DEGRADED"
    if score >= 50:
        return "UNHEALTHY"
    return "CRITICAL"
