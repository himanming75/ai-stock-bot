from __future__ import annotations

import math
import statistics


def returns(values: list[float]) -> list[float]:
    output = []
    for previous, current in zip(values, values[1:]):
        if previous:
            output.append((current - previous) / previous)
    return output


def pearson(a: list[float], b: list[float]) -> float:
    length = min(len(a), len(b))
    if length < 2:
        return 0.0
    x = a[:length]
    y = b[:length]
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    numerator = sum((i - mean_x) * (j - mean_y) for i, j in zip(x, y))
    denom_x = math.sqrt(sum((i - mean_x) ** 2 for i in x))
    denom_y = math.sqrt(sum((j - mean_y) ** 2 for j in y))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def correlation_matrix(series: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    transformed = {symbol: returns(values) for symbol, values in series.items()}
    matrix = {}
    for left, left_values in transformed.items():
        matrix[left] = {}
        for right, right_values in transformed.items():
            matrix[left][right] = round(
                1.0 if left == right else pearson(left_values, right_values),
                4,
            )
    return matrix
