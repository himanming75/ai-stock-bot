from __future__ import annotations
from typing import Any

def signals(
    family: str,
    closes: list[float],
    parameters: dict[str, Any],
) -> list[int]:
    normalized = family.upper()
    result = [0] * len(closes)

    if normalized == "MOMENTUM":
        period = max(1, int(parameters.get("period", 5)))
        for i in range(period, len(closes)):
            result[i] = 1 if closes[i] > closes[i-period] else 0
        return result

    if normalized == "EMA_CROSS":
        fast = max(2, int(parameters.get("fast", 5)))
        slow = max(fast + 1, int(parameters.get("slow", 15)))
        alpha_fast = 2.0 / (fast + 1.0)
        alpha_slow = 2.0 / (slow + 1.0)
        ema_fast = closes[0] if closes else 0.0
        ema_slow = closes[0] if closes else 0.0
        for i, value in enumerate(closes):
            ema_fast = alpha_fast * value + (1-alpha_fast) * ema_fast
            ema_slow = alpha_slow * value + (1-alpha_slow) * ema_slow
            result[i] = 1 if ema_fast > ema_slow else 0
        return result

    if normalized == "BUY_HOLD":
        return [1] * len(closes)

    raise ValueError(f"Unsupported strategy family: {family}")
