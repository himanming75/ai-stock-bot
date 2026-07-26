from data.market import get_history
from ml.model_selector import (
    compare_models,
    print_model_comparison,
)


symbol = "AAPL"

data = get_history(
    symbol=symbol,
    period="5y",
    interval="1d",
)

result = compare_models(
    symbol=symbol,
    data=data,
    horizon_days=5,
    minimum_return=0.0,
)

print_model_comparison(
    result
)