from __future__ import annotations
from .correlation import classify_correlation


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_portfolio_context(
    analyses: list[dict],
    matrix: dict[str, dict[str, float]],
) -> dict:
    if not analyses:
        raise ValueError("analyses are required")

    symbols = [item["symbol"] for item in analyses]
    pair_values = []
    pairs = []
    for index, left in enumerate(symbols):
        for right in symbols[index + 1:]:
            value = matrix[left][right]
            pair_values.append(abs(value))
            pairs.append({
                "left": left,
                "right": right,
                "correlation": value,
                "classification": classify_correlation(value),
            })

    average_abs_correlation = (
        sum(pair_values) / len(pair_values) if pair_values else 0.0
    )
    concentration_risk = clamp(average_abs_correlation, 0.0, 1.0)

    directional_scores = [
        float(item.get("consensus_score", 0.0)) for item in analyses
    ]
    gross_direction = sum(abs(value) for value in directional_scores)
    net_direction = abs(sum(directional_scores))
    directional_concentration = (
        net_direction / gross_direction if gross_direction else 0.0
    )

    portfolio_risk_score = clamp(
        concentration_risk * 0.55 + directional_concentration * 0.45,
        0.0,
        1.0,
    )
    if portfolio_risk_score >= 0.67:
        risk_level = "HIGH"
    elif portfolio_risk_score >= 0.34:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    diversification_state = (
        "CONCENTRATED" if average_abs_correlation >= 0.55 else "DIVERSIFIED"
    )

    return {
        "symbols": symbols,
        "pair_count": len(pairs),
        "pairs": pairs,
        "average_absolute_correlation": round(average_abs_correlation, 6),
        "directional_concentration": round(directional_concentration, 6),
        "portfolio_risk_score": round(portfolio_risk_score, 6),
        "portfolio_risk_level": risk_level,
        "diversification_state": diversification_state,
        "analysis_only": True,
        "capital_allocation_enabled": False,
    }
