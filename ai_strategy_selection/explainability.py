from __future__ import annotations


def reasons(strategy: str, payload: dict, score: dict) -> list[str]:
    output = [
        f"Market regime is {str(payload['market_regime']).upper()}.",
        f"Strategy score is {score['score']:.2f}.",
        f"Strategy confidence is {score['confidence']:.2f}.",
    ]
    if strategy == "TREND_FOLLOWING":
        output.append(f"Trend strength is {float(payload['trend_strength']):.1f}.")
    elif strategy == "MOMENTUM":
        output.append(f"Momentum strength is {float(payload['momentum_strength']):.1f}.")
    elif strategy == "BREAKOUT":
        output.append(f"Breakout strength is {float(payload['breakout_strength']):.1f}.")
    elif strategy == "MEAN_REVERSION":
        output.append(f"Mean-reversion strength is {float(payload['mean_reversion_strength']):.1f}.")
    elif strategy == "CASH_DEFENSIVE":
        output.append(f"Volatility score is {float(payload['volatility_score']):.1f}.")
    if not score["eligible"]:
        output.append("Strategy is not eligible under the current risk constraints.")
    output.append("Selection is analytical only and cannot submit an order.")
    return output
