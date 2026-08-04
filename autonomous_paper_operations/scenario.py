from __future__ import annotations
from typing import Any

def scenario_for_session(
    base_prices: dict[str,float],
    session_number: int,
) -> dict[str, Any]:
    direction=1 if session_number%2 else -1
    scale=1.0+direction*(0.004+0.001*session_number)
    close={symbol:round(float(price)*scale,4) for symbol,price in base_prices.items()}
    middle={
        symbol:round((float(price)+close[symbol])/2.0,4)
        for symbol,price in base_prices.items()
    }
    return {
        "reference_prices":base_prices,
        "intraday_ticks":[
            {"tick":"10:00","prices":middle},
            {"tick":"14:00","prices":close},
        ],
        "closing_prices":close,
    }
