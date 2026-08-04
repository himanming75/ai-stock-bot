from __future__ import annotations
from .models import MarketInput


def reasons(value: MarketInput, features: dict[str, float], regime: str) -> list[str]:
    output = [f"Market regime: {regime}."]
    output.append(
        "Fast moving average is above the slow moving average."
        if features["trend"] > 0
        else "Fast moving average is below the slow moving average."
        if features["trend"] < 0
        else "Moving-average trend is neutral."
    )
    output.append(f"RSI is {value.rsi:.1f}.")
    output.append(f"Volume ratio is {value.volume_ratio:.2f}.")
    if value.news_score:
        output.append(f"Offline news score is {value.news_score:.2f}.")
    return output
