import yfinance as yf

def get_history(symbol, period="6mo"):
    stock = yf.Ticker(symbol)
    data = stock.history(period=period)

    data["MA5"] = data["Close"].rolling(5).mean()
    data["MA20"] = data["Close"].rolling(20).mean()

    change = data["Close"].diff()

    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    average_gain = gain.rolling(14).mean()
    average_loss = loss.rolling(14).mean()

    rs = average_gain / average_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    data = data.dropna()

    return data