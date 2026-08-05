from __future__ import annotations

from decimal import Decimal

from .models import DecisionPolicy


def allocate(selected: list[dict], policy: DecisionPolicy, risk_mode: str) -> dict[str, Decimal]:
    if not selected:
        return {}

    risk_multiplier = {
        "RISK_ON": Decimal("1.00"),
        "NEUTRAL": Decimal("0.75"),
        "RISK_OFF": Decimal("0.00"),
    }.get(risk_mode, Decimal("0.50"))

    budget = min(policy.maximum_total_weight, policy.maximum_total_weight * risk_multiplier)
    scores = [Decimal(str(x["composite_score"])) * Decimal(str(x["confidence"])) for x in selected]
    total = sum(scores, Decimal("0"))
    if total <= 0 or budget <= 0:
        return {str(x["symbol"]): Decimal("0") for x in selected}

    raw = {
        str(item["symbol"]): min(policy.maximum_symbol_weight, budget * score / total)
        for item, score in zip(selected, scores)
    }
    allocated = sum(raw.values(), Decimal("0"))
    if allocated > budget and allocated > 0:
        scale = budget / allocated
        raw = {symbol: weight * scale for symbol, weight in raw.items()}
    return {symbol: weight.quantize(Decimal("0.0001")) for symbol, weight in raw.items()}
