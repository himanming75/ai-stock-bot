from __future__ import annotations

from decimal import Decimal

from .models import D, ZERO, text


DIRECTION = {"BUY": Decimal("1"), "SELL": Decimal("-1"), "HOLD": ZERO}


def vote(results: list[dict], weights: dict[str, str], minimum_score: Decimal) -> dict:
    weighted = ZERO
    total_weight = ZERO
    contributors = []
    for item in results:
        if item.get("status") != "PASS":
            continue
        weight = D(weights.get(item["strategy"], "1"))
        score = D(item.get("score"))
        direction = DIRECTION.get(item.get("signal"), ZERO)
        weighted += direction * score * weight
        total_weight += abs(weight)
        contributors.append(
            {
                "strategy": item["strategy"],
                "signal": item["signal"],
                "score": item["score"],
                "weight": text(weight),
            }
        )
    normalized = weighted / total_weight if total_weight else ZERO
    signal = (
        "BUY" if normalized >= minimum_score
        else "SELL" if normalized <= -minimum_score
        else "HOLD"
    )
    return {
        "signal": signal,
        "combined_score": text(normalized),
        "contributors": contributors,
        "contributor_count": len(contributors),
    }
