from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from .models import FusionInput
from .scoring import score_momentum


class RegimeClassifier:
    def classify(self, items: Sequence[FusionInput]) -> tuple[str, str, Decimal]:
        if not items:
            return "UNKNOWN", "RISK_OFF", Decimal("0")

        n = Decimal(len(items))
        avg_momentum = sum((score_momentum(x) for x in items), Decimal("0")) / n
        avg_breadth = sum((x.breadth_score for x in items), Decimal("0")) / n
        avg_volatility = sum((x.realized_volatility for x in items), Decimal("0")) / n
        avg_macro_risk = sum((x.macro_risk for x in items), Decimal("0")) / n

        if avg_volatility >= Decimal("0.55") or avg_macro_risk >= Decimal("0.75"):
            return "HIGH_VOLATILITY", "RISK_OFF", Decimal("0.25")
        if avg_momentum >= Decimal("0.64") and avg_breadth >= Decimal("0.10"):
            return "TRENDING_UP", "RISK_ON", avg_momentum
        if avg_momentum <= Decimal("0.38") and avg_breadth <= Decimal("-0.10"):
            return "TRENDING_DOWN", "RISK_OFF", Decimal("1") - avg_momentum
        if avg_volatility <= Decimal("0.20") and Decimal("0.43") <= avg_momentum <= Decimal("0.57"):
            return "LOW_VOLATILITY_RANGE", "NEUTRAL", Decimal("0.55")
        return "MIXED", "NEUTRAL", Decimal("0.50")
