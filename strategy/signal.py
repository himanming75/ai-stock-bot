def generate_signal(row):

    if row["RSI"] < 35:
        return "BUY"

    if row["RSI"] > 65:
        return "SELL"

    return "HOLD"


def add_signals(data):
    data = data.copy()
    data["Signal"] = data.apply(generate_signal, axis=1)
    return data