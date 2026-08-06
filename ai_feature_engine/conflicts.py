from __future__ import annotations


def detect_conflicts(candidate: dict) -> dict:
    features = candidate.get("features", {})
    conflicts = []

    ema9 = features.get("ema9")
    ema21 = features.get("ema21")
    histogram = features.get("macd_histogram")
    rsi14 = features.get("rsi14")

    if (
        ema9 is not None
        and ema21 is not None
        and histogram is not None
    ):
        if ema9 > ema21 and histogram < 0:
            conflicts.append({
                "code": "EMA_UP_MACD_DOWN",
                "en": "EMA and MACD disagree.",
                "ko": "EMA와 MACD 방향이 서로 다릅니다.",
            })
        if ema9 < ema21 and histogram > 0:
            conflicts.append({
                "code": "EMA_DOWN_MACD_UP",
                "en": "EMA and MACD disagree.",
                "ko": "EMA와 MACD 방향이 서로 다릅니다.",
            })

    if rsi14 is not None:
        if candidate.get("action") == "BUY" and rsi14 >= 70:
            conflicts.append({
                "code": "BUY_WHILE_OVERBOUGHT",
                "en": "Buy candidate conflicts with overbought RSI.",
                "ko": "매수 후보와 RSI 과매수 상태가 충돌합니다.",
            })
        if candidate.get("action") == "SELL" and rsi14 <= 30:
            conflicts.append({
                "code": "SELL_WHILE_OVERSOLD",
                "en": "Sell candidate conflicts with oversold RSI.",
                "ko": "매도 후보와 RSI 과매도 상태가 충돌합니다.",
            })

    return {
        "has_conflict": bool(conflicts),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }
