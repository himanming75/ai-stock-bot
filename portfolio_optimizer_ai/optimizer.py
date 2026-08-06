from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_candidate_weights(
    analyses: list[dict],
    *,
    max_symbol_weight: float = 0.35,
) -> dict:
    if not analyses:
        raise ValueError("analyses are required")

    raw = {}
    for item in analyses:
        symbol = item["symbol"]
        expected_return = abs(float(item.get("expected_return", 0.0)))
        expected_risk = max(float(item.get("expected_risk", 0.01)), 0.0001)
        confidence = float(
            item.get("confidence_calibration", {}).get(
                "calibrated_confidence", 0.5
            )
        )
        score = expected_return / expected_risk * confidence
        raw[symbol] = max(score, 0.01)

    total = sum(raw.values())
    uncapped = {symbol: value / total for symbol, value in raw.items()}
    capped = {
        symbol: min(weight, max_symbol_weight)
        for symbol, weight in uncapped.items()
    }
    capped_total = sum(capped.values())
    normalized = {
        symbol: round(weight / capped_total, 6)
        for symbol, weight in capped.items()
    }

    return {
        "candidate_weights": normalized,
        "max_symbol_weight": max_symbol_weight,
        "weight_sum": round(sum(normalized.values()), 6),
        "allocation_mode": "SIMULATION_ONLY",
        "capital_allocation_enabled": False,
        "order_generation_enabled": False,
    }
