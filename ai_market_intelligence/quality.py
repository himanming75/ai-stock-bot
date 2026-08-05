from __future__ import annotations
import math


REQUIRED_FEATURES = (
    "close", "volume", "sma_5", "sma_10", "sma_20", "ema_9",
    "ema_12", "ema_26", "rsi_14", "macd", "macd_signal",
    "macd_histogram", "atr_14", "bollinger_middle", "vwap",
    "obv", "adx_14", "roc_5", "roc_10", "return_1",
    "return_5", "return_10", "volume_ratio_20",
)


def validate_record(record: dict, minimum_bars: int = 35) -> dict:
    blockers = []
    warnings = []
    if int(record.get("bar_count", 0)) < minimum_bars:
        blockers.append("INSUFFICIENT_BARS")
    for key in REQUIRED_FEATURES:
        value = record.get(key)
        if value is None:
            blockers.append(f"MISSING_FEATURE:{key}")
        elif isinstance(value, (int, float)) and not math.isfinite(float(value)):
            blockers.append(f"NON_FINITE_FEATURE:{key}")
    if not record.get("timestamp"):
        blockers.append("TIMESTAMP_MISSING")
    if float(record.get("volume", 0.0)) <= 0:
        warnings.append("NON_POSITIVE_LATEST_VOLUME")
    return {
        "symbol": record.get("symbol"),
        "passed": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "feature_count": len([k for k, v in record.items() if v is not None]),
    }
