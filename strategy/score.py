def calculate_score(row):

    score = 0

    # MA5 > MA20
    if row["MA5"] > row["MA20"]:
        score += 30

    # RSI
    if 40 < row["RSI"] < 70:
        score += 30

    # 가격이 MA5 위
    if row["Close"] > row["MA5"]:
        score += 20

    # 가격이 MA20 위
    if row["Close"] > row["MA20"]:
        score += 20

    return score