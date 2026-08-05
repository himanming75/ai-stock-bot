from __future__ import annotations
from decimal import Decimal
from typing import Any


class MarketRegimeDetector:
    def detect(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        index_return = Decimal(str(snapshot.get("index_return_20", "0")))
        volatility = Decimal(str(snapshot.get("volatility_20", "0")))
        breadth = Decimal(str(snapshot.get("breadth", "0.5")))
        trend_strength = Decimal(str(snapshot.get("trend_strength", "0")))

        if volatility >= Decimal("0.20"):
            regime = "HIGH_VOLATILITY"
            multiplier = Decimal("0.55")
        elif index_return > Decimal("0.03") and breadth >= Decimal("0.60"):
            regime = "BULL_TREND"
            multiplier = Decimal("1.00")
        elif index_return < Decimal("-0.03") and breadth <= Decimal("0.40"):
            regime = "BEAR_TREND"
            multiplier = Decimal("0.45")
        elif abs(index_return) < Decimal("0.02") and trend_strength < Decimal("0.30"):
            regime = "RANGE_BOUND"
            multiplier = Decimal("0.75")
        else:
            regime = "MIXED"
            multiplier = Decimal("0.65")

        return {
            "regime": regime,
            "allocation_multiplier": str(multiplier),
            "index_return_20": str(index_return),
            "volatility_20": str(volatility),
            "breadth": str(breadth),
            "trend_strength": str(trend_strength),
        }
