from data.market import get_history
from forecast.predictor import (
    create_trade_plan,
    print_trade_plan,
)
from strategy.score import (
    calculate_score,
    determine_signal,
)


symbol = "AAPL"

data = get_history(
    symbol=symbol,
    period="5y",
    interval="1d",
)

latest = data.iloc[-1]

score_result = calculate_score(
    latest
)

score = int(
    score_result["score"]
)

signal = determine_signal(
    latest,
    score,
)

plan = create_trade_plan(
    symbol=symbol,
    data=data,
    technical_signal=signal,
)

print_trade_plan(
    plan
)