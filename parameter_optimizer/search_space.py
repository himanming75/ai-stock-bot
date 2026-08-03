from __future__ import annotations
from typing import Any

SEARCH_SPACES: dict[str, list[dict[str, Any]]] = {
    "EMA_CROSS": [
        {"fast": fast, "slow": slow}
        for fast in (5, 8, 10, 12, 15, 20)
        for slow in (20, 25, 30, 40, 50, 60)
        if fast < slow
    ],
    "RSI": [
        {"period": period, "oversold": low, "overbought": high}
        for period in (7, 10, 14, 18, 21)
        for low, high in ((25, 75), (30, 70), (35, 65), (40, 60))
    ],
    "MOMENTUM": [
        {"period": period}
        for period in (5, 8, 10, 12, 15, 20, 25, 30)
    ],
    "BOLLINGER": [
        {"period": period, "std": std}
        for period in (10, 15, 20, 25, 30)
        for std in (1.5, 2.0, 2.5, 3.0)
    ],
    "MACD": [{}],
}

def get_space(base_strategy: str) -> list[dict[str, Any]]:
    return list(SEARCH_SPACES.get(base_strategy, []))
