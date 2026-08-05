from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import Any
import json


class HistoricalDataAdapter:
    def load_json_bars(self, path: Path) -> list[dict[str, Any]]:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        bars = value.get("bars", value) if isinstance(value, dict) else value
        if not isinstance(bars, list):
            raise ValueError("INVALID_HISTORICAL_BAR_FORMAT")
        return bars

    def fixture_bars(
        self,
        *,
        start_price: Decimal,
        count: int = 30,
        daily_step: Decimal = Decimal("0.6"),
    ) -> list[dict[str, Any]]:
        bars = []
        price = start_price
        for index in range(count):
            close = price + daily_step
            bars.append({
                "timestamp": f"2026-01-{index + 1:02d}",
                "open": str(price),
                "high": str(close + Decimal("1")),
                "low": str(price - Decimal("1")),
                "close": str(close),
                "volume": str(1000000 + index * 25000),
            })
            price = close
        return bars
