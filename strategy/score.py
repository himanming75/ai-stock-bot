def calculate_score(row):
    score = 0
    reasons = []

    # 추세: 최대 30점
    if row["MA5"] > row["MA20"]:
        score += 20
        reasons.append("MA5 is above MA20")

    if row["Close"] > row["MA20"]:
        score += 10
        reasons.append("Price is above MA20")

    # RSI: 최대 20점
    if 45 <= row["RSI"] <= 65:
        score += 20
        reasons.append("RSI is in a healthy range")

    elif 35 <= row["RSI"] < 45:
        score += 10
        reasons.append("RSI is recovering from weakness")

    # MACD: 최대 30점
    if row["MACD"] > row["MACD_SIGNAL"]:
        score += 20
        reasons.append("MACD is above its signal line")

    if row["MACD_HIST"] > 0:
        score += 10
        reasons.append("MACD histogram is positive")

    # 볼린저 밴드: 최대 20점
    if row["BB_MIDDLE"] <= row["Close"] <= row["BB_UPPER"]:
        score += 20
        reasons.append("Price is in the upper Bollinger range")

    elif row["BB_LOWER"] <= row["Close"] < row["BB_MIDDLE"]:
        score += 10
        reasons.append("Price is in the lower Bollinger range")

    return {
        "score": score,
        "reasons": reasons,
    }