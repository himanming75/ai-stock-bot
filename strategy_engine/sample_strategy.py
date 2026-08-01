from __future__ import annotations

from decimal import Decimal

from .models import MarketSnapshot, SignalAction, StrategySignal


class MovingAverageCrossStrategy:
    """Deterministic example strategy used to validate the signal pipeline."""

    name = "moving_average_cross"

    def __init__(self, *, short_window: int = 3, long_window: int = 5) -> None:
        if short_window < 1 or long_window <= short_window:
            raise ValueError("require 1 <= short_window < long_window")
        self.short_window = short_window
        self.long_window = long_window

    @staticmethod
    def _mean(values: tuple[Decimal, ...]) -> Decimal:
        return sum(values, Decimal("0")) / Decimal(len(values))

    def evaluate(self, snapshot: MarketSnapshot) -> StrategySignal:
        snapshot.validate()
        closes = snapshot.recent_closes
        if len(closes) < self.long_window:
            return StrategySignal(
                strategy_name=self.name,
                symbol=snapshot.symbol,
                action=SignalAction.HOLD,
                confidence=Decimal("0"),
                generated_at=snapshot.timestamp,
                reason="insufficient_history",
                reference_price=snapshot.last_price,
            )

        short_avg = self._mean(closes[-self.short_window:])
        long_avg = self._mean(closes[-self.long_window:])
        spread = (short_avg - long_avg) / long_avg

        if spread > 0:
            action = SignalAction.BUY
        elif spread < 0:
            action = SignalAction.SELL
        else:
            action = SignalAction.HOLD

        confidence = min(abs(spread) * Decimal("20"), Decimal("1"))
        quantity = Decimal("1") if action != SignalAction.HOLD else Decimal("0")
        return StrategySignal(
            strategy_name=self.name,
            symbol=snapshot.symbol,
            action=action,
            confidence=confidence,
            generated_at=snapshot.timestamp,
            reason=f"short_avg={short_avg};long_avg={long_avg};spread={spread}",
            reference_price=snapshot.last_price,
            suggested_quantity=quantity,
            metadata={
                "short_average": str(short_avg),
                "long_average": str(long_avg),
                "spread": str(spread),
            },
        )
