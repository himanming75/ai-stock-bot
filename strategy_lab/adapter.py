from __future__ import annotations

def base_strategy_name(strategy_id: str) -> str:
    if strategy_id.startswith("EMA_"):
        return "EMA_CROSS"
    if strategy_id.startswith("RSI_"):
        return "RSI"
    if strategy_id.startswith("MACD_"):
        return "MACD"
    if strategy_id.startswith("MOMENTUM_"):
        return "MOMENTUM"
    if strategy_id.startswith("BOLLINGER_"):
        return "BOLLINGER"
    raise ValueError(f"unsupported strategy id: {strategy_id}")
