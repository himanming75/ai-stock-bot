from __future__ import annotations
from decimal import Decimal
from typing import Any


class DataQualityAuditor:
    def audit_bars(
        self,
        *,
        symbol: str,
        bars: list[dict[str, Any]],
    ) -> dict[str, Any]:
        duplicate_timestamps = 0
        non_monotonic = 0
        invalid_ohlc = 0
        invalid_volume = 0
        missing_fields = 0

        seen = set()
        previous_timestamp = None
        required = {"timestamp", "open", "high", "low", "close", "volume"}

        for bar in bars:
            if not required.issubset(bar):
                missing_fields += 1
                continue

            timestamp = str(bar["timestamp"])
            if timestamp in seen:
                duplicate_timestamps += 1
            seen.add(timestamp)

            if previous_timestamp is not None and timestamp <= previous_timestamp:
                non_monotonic += 1
            previous_timestamp = timestamp

            try:
                open_price = Decimal(str(bar["open"]))
                high = Decimal(str(bar["high"]))
                low = Decimal(str(bar["low"]))
                close = Decimal(str(bar["close"]))
                volume = Decimal(str(bar["volume"]))
            except Exception:
                invalid_ohlc += 1
                continue

            if high < max(open_price, close) or low > min(open_price, close) or low > high:
                invalid_ohlc += 1
            if volume < 0:
                invalid_volume += 1

        checks = {
            "bars_present": bool(bars),
            "no_duplicate_timestamps": duplicate_timestamps == 0,
            "timestamps_monotonic": non_monotonic == 0,
            "ohlc_valid": invalid_ohlc == 0,
            "volume_valid": invalid_volume == 0,
            "required_fields_present": missing_fields == 0,
        }
        return {
            "symbol": symbol,
            "bar_count": len(bars),
            "checks": checks,
            "failed": [key for key, value in checks.items() if not value],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "duplicate_timestamps": duplicate_timestamps,
            "non_monotonic_rows": non_monotonic,
            "invalid_ohlc_rows": invalid_ohlc,
            "invalid_volume_rows": invalid_volume,
            "missing_field_rows": missing_fields,
        }
