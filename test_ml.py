from data.market import get_history
from ml.predictor import (
    predict_stock_direction,
    print_ml_prediction,
)


symbol = "AAPL"

data = get_history(
    symbol=symbol,
    period="5y",
    interval="1d",
)

prediction = predict_stock_direction(
    symbol=symbol,
    data=data,
    horizon_days=5,
    minimum_return=0.0,
)

print_ml_prediction(
    prediction
)