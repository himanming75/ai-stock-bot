from __future__ import annotations
from math import sqrt


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("series must have the same length and at least 2 values")
    lm = _mean(left)
    rm = _mean(right)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    lden = sqrt(sum((a - lm) ** 2 for a in left))
    rden = sqrt(sum((b - rm) ** 2 for b in right))
    if lden == 0 or rden == 0:
        return 0.0
    return max(-1.0, min(1.0, numerator / (lden * rden)))


def correlation_matrix(series: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    symbols = sorted(series)
    matrix: dict[str, dict[str, float]] = {}
    for left in symbols:
        matrix[left] = {}
        for right in symbols:
            matrix[left][right] = round(
                1.0 if left == right else pearson(series[left], series[right]),
                6,
            )
    return matrix


def classify_correlation(value: float) -> str:
    if value >= 0.35:
        return "POSITIVE"
    if value <= -0.35:
        return "NEGATIVE"
    return "NEUTRAL"
