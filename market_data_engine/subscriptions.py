from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SubscriptionRegistry:
    quotes: set[str] = field(default_factory=set)
    trades: set[str] = field(default_factory=set)
    bars: set[str] = field(default_factory=set)

    @staticmethod
    def _normalize(symbols) -> set[str]:
        normalized = {str(symbol).upper().strip() for symbol in symbols}
        if "" in normalized:
            raise ValueError("blank symbol is not allowed")
        return normalized

    def subscribe(self, *, quotes=(), trades=(), bars=()) -> dict[str, list[str]]:
        self.quotes |= self._normalize(quotes)
        self.trades |= self._normalize(trades)
        self.bars |= self._normalize(bars)
        return self.snapshot()

    def unsubscribe(self, *, quotes=(), trades=(), bars=()) -> dict[str, list[str]]:
        self.quotes -= self._normalize(quotes)
        self.trades -= self._normalize(trades)
        self.bars -= self._normalize(bars)
        return self.snapshot()

    def accepts(self, kind: str, symbol: str) -> bool:
        bucket = {"quote": self.quotes, "trade": self.trades, "bar": self.bars}.get(kind)
        if bucket is None:
            raise ValueError(f"unknown market-data kind: {kind}")
        return symbol.upper() in bucket

    def alpaca_subscribe_message(self) -> dict[str, object]:
        return {
            "action": "subscribe",
            "quotes": sorted(self.quotes),
            "trades": sorted(self.trades),
            "bars": sorted(self.bars),
        }

    def snapshot(self) -> dict[str, list[str]]:
        return {
            "quotes": sorted(self.quotes),
            "trades": sorted(self.trades),
            "bars": sorted(self.bars),
        }
