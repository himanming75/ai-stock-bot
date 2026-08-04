from __future__ import annotations
from typing import Any

def volatility_scale(
    target_volatility_pct: float,
    observed_volatility_pct: float,
    minimum_multiplier: float,
    maximum_multiplier: float,
) -> dict[str, Any]:
    observed=max(1e-9,observed_volatility_pct)
    raw=target_volatility_pct/observed
    multiplier=max(minimum_multiplier,min(maximum_multiplier,raw))
    return {
        "target_volatility_pct":round(target_volatility_pct,6),
        "observed_volatility_pct":round(observed_volatility_pct,6),
        "raw_multiplier":round(raw,6),
        "applied_multiplier":round(multiplier,6),
    }
