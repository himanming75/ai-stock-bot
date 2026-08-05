from __future__ import annotations

def timeframe_consensus(
    symbol: str,
    timeframe_input: dict,
    required: list[str],
) -> dict:
    symbol_rows = timeframe_input.get("symbols", {}).get(symbol, {})
    observed = {
        frame: symbol_rows.get(frame)
        for frame in required
        if symbol_rows.get(frame) in {"BUY", "SELL", "HOLD"}
    }
    missing = [frame for frame in required if frame not in observed]
    buy = sum(1 for value in observed.values() if value == "BUY")
    sell = sum(1 for value in observed.values() if value == "SELL")
    hold = sum(1 for value in observed.values() if value == "HOLD")
    consensus = (
        "BUY" if buy > sell and buy > hold
        else "SELL" if sell > buy and sell > hold
        else "HOLD"
    )
    return {
        "symbol": symbol,
        "required_timeframes": required,
        "observed": observed,
        "missing_timeframes": missing,
        "complete": len(missing) == 0,
        "consensus": consensus,
        "counts": {"buy": buy, "sell": sell, "hold": hold},
    }
