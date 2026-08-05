from __future__ import annotations

from decimal import Decimal

from .models import D, ZERO


def closes(bars: list[dict]) -> list[Decimal]:
    return [D(item.get("close")) for item in bars if D(item.get("close")) > 0]


def highs(bars: list[dict]) -> list[Decimal]:
    return [D(item.get("high")) for item in bars if D(item.get("high")) > 0]


def lows(bars: list[dict]) -> list[Decimal]:
    return [D(item.get("low")) for item in bars if D(item.get("low")) > 0]


def mean(values: list[Decimal]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values)) if values else ZERO


def simple_return(first: Decimal, last: Decimal) -> Decimal:
    if first == ZERO:
        return ZERO
    return (last - first) / first


def rolling_high(values: list[Decimal], window: int) -> Decimal:
    sample = values[-window:] if window > 0 else values
    return max(sample) if sample else ZERO


def rolling_low(values: list[Decimal], window: int) -> Decimal:
    sample = values[-window:] if window > 0 else values
    return min(sample) if sample else ZERO
