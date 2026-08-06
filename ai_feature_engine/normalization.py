from __future__ import annotations
from .models import Bar


def normalize_bars(payload) -> list[Bar]:
    if not isinstance(payload, list):
        raise ValueError("BARS_LIST_REQUIRED")
    bars = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"BAR_{index}_OBJECT_REQUIRED")
        try:
            bar = Bar(
                timestamp=str(item.get("timestamp") or index),
                open=float(item["open"]),
                high=float(item["high"]),
                low=float(item["low"]),
                close=float(item["close"]),
                volume=float(item.get("volume", 0)),
            )
        except Exception as exc:
            raise ValueError(f"BAR_{index}_INVALID") from exc
        if bar.high < max(bar.open, bar.close, bar.low):
            raise ValueError(f"BAR_{index}_HIGH_INVALID")
        if bar.low > min(bar.open, bar.close, bar.high):
            raise ValueError(f"BAR_{index}_LOW_INVALID")
        bars.append(bar)
    if len(bars) < 30:
        raise ValueError("MINIMUM_30_BARS_REQUIRED")
    return bars
