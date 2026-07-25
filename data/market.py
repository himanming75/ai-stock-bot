import yfinance as yf


def get_history(symbol, period="6mo"):
    stock = yf.Ticker(symbol)
    data = stock.history(period=period)

    # 이동평균선
    data["MA5"] = data["Close"].rolling(5).mean()
    data["MA20"] = data["Close"].rolling(20).mean()

    # RSI
    change = data["Close"].diff()

    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    average_gain = gain.rolling(14).mean()
    average_loss = loss.rolling(14).mean()

    rs = average_gain / average_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = data["Close"].ewm(span=12, adjust=False).mean()
    ema26 = data["Close"].ewm(span=26, adjust=False).mean()

    data["MACD"] = ema12 - ema26
    data["MACD_SIGNAL"] = data["MACD"].ewm(
        span=9,
        adjust=False,
    ).mean()

    data["MACD_HIST"] = (
        data["MACD"] - data["MACD_SIGNAL"]
    )

    # 볼린저 밴드
    data["BB_MIDDLE"] = data["Close"].rolling(20).mean()

    standard_deviation = data["Close"].rolling(20).std()

    data["BB_UPPER"] = (
        data["BB_MIDDLE"] + standard_deviation * 2
    )

    data["BB_LOWER"] = (
        data["BB_MIDDLE"] - standard_deviation * 2
    )

    # 계산되지 않은 행 제거
    data = data.dropna()

    return data