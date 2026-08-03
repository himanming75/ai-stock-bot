from __future__ import annotations
from typing import Any

def resample_bars(
    bars: list[dict[str, Any]],
    factor: int,
) -> list[dict[str, Any]]:
    if factor <= 1:
        return list(bars)
    output = []
    for start in range(0, len(bars), factor):
        chunk = bars[start:start + factor]
        if len(chunk) < factor:
            continue
        output.append({
            "timestamp": chunk[-1]["timestamp"],
            "open": float(chunk[0]["open"]),
            "high": max(float(row["high"]) for row in chunk),
            "low": min(float(row["low"]) for row in chunk),
            "close": float(chunk[-1]["close"]),
            "volume": sum(float(row.get("volume", 0.0)) for row in chunk),
        })
    return output
