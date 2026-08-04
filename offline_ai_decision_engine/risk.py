from __future__ import annotations
from .models import MarketInput


def level(value: MarketInput, regime: str) -> str:
    if regime == "HIGH_VOLATILITY" or value.atr_pct >= 0.035:
        return "HIGH"
    if value.atr_pct >= 0.02 or value.volume_ratio >= 2.0:
        return "MEDIUM"
    return "LOW"
