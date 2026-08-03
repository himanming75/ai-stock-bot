from __future__ import annotations
from typing import Any

Z_95=1.6448536269514722

def portfolio_var(
    account_equity: float,
    weighted_volatility_pct: float,
    horizon_days: int=1,
    confidence_z: float=Z_95,
) -> dict[str, Any]:
    daily_vol=weighted_volatility_pct/100.0
    scale=max(1.0,float(horizon_days))**0.5
    var_pct=confidence_z*daily_vol*scale*100.0
    var_amount=account_equity*var_pct/100.0
    return {
        "confidence_level_pct":95.0,
        "horizon_days":horizon_days,
        "weighted_volatility_pct":round(weighted_volatility_pct,6),
        "var_pct":round(var_pct,6),
        "var_amount":round(var_amount,6),
    }
