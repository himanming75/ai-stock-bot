from pathlib import Path

import pandas as pd

from data.market import get_history
from ml.predictor import (
    predict_stock_direction,
    print_ml_prediction,
)


symbol = "AAPL"

cache_directory = Path("release/v76_4/runtime_cache")
cache_directory.mkdir(parents=True, exist_ok=True)

cache_path = cache_directory / "AAPL_5y_1d_v76_4b.csv"

if cache_path.exists():
    data = pd.read_csv(
        cache_path,
        index_col="Date",
        parse_dates=["Date"],
    )
else:
    data = get_history(
        symbol=symbol,
        period="5y",
        interval="1d",
    )
    data = data.sort_index()
    data = data[~data.index.duplicated(keep="last")]
    data.to_csv(
        cache_path,
        index=True,
        date_format="%Y-%m-%d",
        float_format="%.17g",
    )
    data = pd.read_csv(
        cache_path,
        index_col="Date",
        parse_dates=["Date"],
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
