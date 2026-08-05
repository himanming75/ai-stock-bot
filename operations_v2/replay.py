from __future__ import annotations
from decimal import Decimal
from typing import Any


class HistoricalReplaySimulator:
    def replay(
        self,
        *,
        symbol: str,
        bars: list[dict[str, Any]],
        fast_window: int = 5,
        slow_window: int = 20,
    ) -> dict[str, Any]:
        if fast_window <= 0 or slow_window <= fast_window:
            raise ValueError("INVALID_WINDOWS")
        if len(bars) < slow_window:
            raise ValueError("INSUFFICIENT_BARS")

        closes = [Decimal(str(bar["close"])) for bar in bars]
        events = []
        position = 0
        entry_price = Decimal("0")
        realized_pnl = Decimal("0")

        for index in range(slow_window - 1, len(closes)):
            fast = sum(closes[index-fast_window+1:index+1]) / Decimal(fast_window)
            slow = sum(closes[index-slow_window+1:index+1]) / Decimal(slow_window)
            price = closes[index]

            action = "HOLD"
            if fast > slow and position == 0:
                action = "BUY_PREVIEW"
                position = 1
                entry_price = price
            elif fast < slow and position == 1:
                action = "SELL_PREVIEW"
                realized_pnl += price - entry_price
                position = 0

            events.append({
                "index": index,
                "timestamp": bars[index]["timestamp"],
                "price": str(price),
                "fast_average": str(fast.quantize(Decimal("0.0001"))),
                "slow_average": str(slow.quantize(Decimal("0.0001"))),
                "action": action,
                "order_created": False,
                "broker_write_used": False,
            })

        unrealized = (
            closes[-1] - entry_price if position == 1 else Decimal("0")
        )
        return {
            "symbol": symbol,
            "event_count": len(events),
            "events": events,
            "ending_position_preview": position,
            "realized_pnl_preview": str(realized_pnl.quantize(Decimal("0.01"))),
            "unrealized_pnl_preview": str(unrealized.quantize(Decimal("0.01"))),
            "actual_orders_created": False,
            "actual_portfolio_modified": False,
            "broker_network_used": False,
            "broker_write_used": False,
        }
