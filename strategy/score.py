import pandas as pd


def calculate_score(row: pd.Series) -> dict:
    """
    한 날짜의 기술지표를 바탕으로 0~100점 점수를 계산합니다.

    점수 구성:
    - 추세: 30점
    - RSI: 20점
    - MACD: 30점
    - Bollinger Band: 20점
    """

    score = 0
    reasons = []

    close = float(row["Close"])
    ma5 = float(row["MA5"])
    ma20 = float(row["MA20"])
    rsi = float(row["RSI"])
    macd = float(row["MACD"])
    macd_signal = float(row["MACD_SIGNAL"])
    macd_hist = float(row["MACD_HIST"])
    bb_upper = float(row["BB_UPPER"])
    bb_middle = float(row["BB_MIDDLE"])
    bb_lower = float(row["BB_LOWER"])

    # -------------------------------------------------
    # 1. Trend score: 최대 30점
    # -------------------------------------------------

    if ma5 > ma20:
        score += 15
        reasons.append("MA5 is above MA20")
    else:
        reasons.append("MA5 is below or equal to MA20")

    if close > ma20:
        score += 15
        reasons.append("Price is above MA20")
    else:
        reasons.append("Price is below or equal to MA20")

    # -------------------------------------------------
    # 2. RSI score: 최대 20점
    # -------------------------------------------------

    if 45 <= rsi <= 60:
        score += 20
        reasons.append("RSI is in the strongest healthy range")

    elif 40 <= rsi < 45 or 60 < rsi <= 65:
        score += 15
        reasons.append("RSI is in a healthy range")

    elif 30 <= rsi < 40:
        score += 10
        reasons.append("RSI is recovering from a weak range")

    elif 65 < rsi < 70:
        score += 8
        reasons.append("RSI is strong but approaching overbought")

    elif rsi < 30:
        score += 5
        reasons.append("RSI is oversold")

    else:
        reasons.append("RSI is overbought")

    # -------------------------------------------------
    # 3. MACD score: 최대 30점
    # -------------------------------------------------

    if macd > macd_signal:
        score += 15
        reasons.append("MACD is above its signal line")
    else:
        reasons.append("MACD is below or equal to its signal line")

    if macd_hist > 0:
        score += 15
        reasons.append("MACD histogram is positive")
    else:
        reasons.append("MACD histogram is negative or flat")

    # -------------------------------------------------
    # 4. Bollinger Band score: 최대 20점
    # -------------------------------------------------

    if close < bb_lower:
        score += 10
        reasons.append("Price is below the lower Bollinger Band")

    elif bb_lower <= close < bb_middle:
        score += 20
        reasons.append("Price is in the lower Bollinger range")

    elif bb_middle <= close <= bb_upper:
        score += 12
        reasons.append("Price is in the upper Bollinger range")

    else:
        score += 3
        reasons.append("Price is above the upper Bollinger Band")

    # 안전하게 0~100점 범위 제한
    score = max(0, min(100, score))

    return {
        "score": score,
        "reasons": reasons,
    }


def determine_signal(row: pd.Series, score: int) -> str:
    """
    기술점수와 주요 지표를 함께 사용해 BUY/HOLD/SELL을 결정합니다.

    BUY:
    - 점수 75점 이상
    - MA5 > MA20
    - MACD > Signal
    - RSI 70 미만
    - 종가가 Bollinger Upper보다 높지 않음

    SELL:
    - 점수 40점 이하
    - 또는 MA5 < MA20이면서 MACD도 약세
    - 또는 RSI가 매우 과매수
    """

    ma5 = float(row["MA5"])
    ma20 = float(row["MA20"])
    rsi = float(row["RSI"])
    macd = float(row["MACD"])
    macd_signal = float(row["MACD_SIGNAL"])
    close = float(row["Close"])
    bb_upper = float(row["BB_UPPER"])

    bullish_trend = ma5 > ma20
    bullish_macd = macd > macd_signal
    below_upper_band = close <= bb_upper

    if (
        score >= 75
        and bullish_trend
        and bullish_macd
        and rsi < 70
        and below_upper_band
    ):
        return "BUY"

    if (
        score <= 40
        or (ma5 < ma20 and macd < macd_signal)
        or rsi >= 75
    ):
        return "SELL"

    return "HOLD"