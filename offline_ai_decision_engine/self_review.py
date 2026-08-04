from __future__ import annotations
from .models import MarketInput


def review(action: str, confidence: float, regime: str, value: MarketInput) -> list[str]:
    notes: list[str] = []
    if confidence < 60:
        notes.append("Confidence is below the execution-grade threshold.")
    if regime == "HIGH_VOLATILITY":
        notes.append("High volatility requires reduced size or no trade in a future execution layer.")
    if action == "BUY" and value.rsi >= 70:
        notes.append("BUY signal conflicts with an overbought RSI.")
    if action == "SELL" and value.rsi <= 30:
        notes.append("SELL signal conflicts with an oversold RSI.")
    if not notes:
        notes.append("No major internal conflict detected.")
    notes.append("This offline decision cannot submit an order.")
    return notes
