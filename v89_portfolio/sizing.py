from __future__ import annotations
import math

def equal_weight(symbols: list[str]) -> dict[str, float]:
    if not symbols:
        return {}
    weight = 1.0 / len(symbols)
    return {symbol: weight for symbol in symbols}

def score_weight(rows: list[dict]) -> dict[str, float]:
    positive = {
        str(row.get("strategy", f"S{index}")): max(0.0, float(row.get("portfolio_score", 0.0)))
        for index, row in enumerate(rows)
    }
    total = sum(positive.values())
    if total <= 0:
        return equal_weight(list(positive))
    return {key: value / total for key, value in positive.items()}

def inverse_drawdown_weight(rows: list[dict]) -> dict[str, float]:
    raw = {}
    for index, row in enumerate(rows):
        name = str(row.get("strategy", f"S{index}"))
        drawdown = max(0.1, float(row.get("maximum_drawdown_pct", 0.1)))
        raw[name] = 1.0 / drawdown
    total = sum(raw.values())
    return {key: value / total for key, value in raw.items()} if total else {}

def kelly_fraction(win_rate_pct: float, profit_factor: float) -> float:
    p = max(0.0, min(1.0, win_rate_pct / 100.0))
    q = 1.0 - p
    b = max(0.0001, profit_factor)
    fraction = p - q / b
    return max(0.0, min(1.0, fraction))

def capped_weights(weights: dict[str, float], max_weight: float) -> dict[str, float]:
    if not weights:
        return {}
    result = dict(weights)
    for _ in range(20):
        excess = 0.0
        free = []
        for key, value in result.items():
            if value > max_weight:
                excess += value - max_weight
                result[key] = max_weight
            else:
                free.append(key)
        if excess <= 1e-12 or not free:
            break
        addition = excess / len(free)
        for key in free:
            result[key] += addition
    total = sum(result.values())
    return {key: value / total for key, value in result.items()} if total else result
