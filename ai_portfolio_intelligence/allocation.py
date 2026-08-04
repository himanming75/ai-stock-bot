from __future__ import annotations
from collections import Counter


def cash_weight(selected: list[dict]) -> float:
    if not selected:
        return 1.0
    avg_confidence = sum(float(item["confidence"]) for item in selected) / len(selected)
    avg_risk = sum(float(item["risk_score"]) for item in selected) / len(selected)
    value = 0.35 - (avg_confidence - 55.0) / 200.0 + avg_risk / 500.0
    return round(max(0.05, min(0.60, value)), 4)


def assign_weights(selected: list[dict], cash: float, maximum_single_weight: float) -> list[dict]:
    if not selected:
        return []
    investable = max(0.0, 1.0 - cash)
    quality = [max(1.0, float(item["selection_score"])) for item in selected]
    total_quality = sum(quality)
    raw = [investable * value / total_quality for value in quality]

    # Cap and redistribute deterministically.
    weights = [min(maximum_single_weight, value) for value in raw]
    remaining = investable - sum(weights)
    for _ in range(10):
        if remaining <= 1e-9:
            break
        eligible = [i for i, value in enumerate(weights) if value < maximum_single_weight - 1e-9]
        if not eligible:
            break
        share = remaining / len(eligible)
        before = sum(weights)
        for i in eligible:
            weights[i] = min(maximum_single_weight, weights[i] + share)
        remaining = investable - sum(weights)
        if abs(sum(weights) - before) < 1e-12:
            break

    output: list[dict] = []
    for item, weight in zip(selected, weights):
        copy = dict(item)
        copy["weight"] = round(weight, 6)
        output.append(copy)
    return output


def diversification_score(selected: list[dict]) -> float:
    if not selected:
        return 0.0
    counts = Counter(str(item.get("sector", "UNKNOWN")).upper() for item in selected)
    largest = max(counts.values())
    concentration = largest / len(selected)
    return round((1.0 - concentration) * 100.0, 2)
