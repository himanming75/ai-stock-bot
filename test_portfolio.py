from data.market import get_history
from forecast.predictor import create_trade_plan
from portfolio.manager import (
    create_position_plan,
    print_position_plan,
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

trade_plan = create_trade_plan(
    symbol=symbol,
    data=data,
    technical_signal=signal,
)

position_plan = create_position_plan(
    trade_plan=trade_plan,
)

print_position_plan(
    position_plan
)