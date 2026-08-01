from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from strategy_engine import MarketSnapshot, SignalAction, StrategySignal

from .models import OrderIntent, OrderSide, OrderType, TimeInForce
from .sizing import PositionSizer


class OrderIntentFactory:
    def __init__(
        self,
        *,
        position_sizer: PositionSizer,
        ttl_seconds: int = 30,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.position_sizer = position_sizer
        self.ttl_seconds = ttl_seconds
        self.order_type = order_type
        self.time_in_force = time_in_force

    def create(self, signal: StrategySignal, snapshot: MarketSnapshot) -> OrderIntent | None:
        sizing = self.position_sizer.size(signal, snapshot)
        if not sizing.accepted:
            return None

        side = OrderSide.BUY if signal.action == SignalAction.BUY else OrderSide.SELL
        intent = OrderIntent(
            symbol=signal.symbol,
            side=side,
            quantity=sizing.quantity,
            reference_price=signal.reference_price,
            estimated_notional=sizing.estimated_notional,
            created_at=signal.generated_at,
            expires_at=signal.generated_at + timedelta(seconds=self.ttl_seconds),
            source_signal_id=signal.signal_id,
            strategy_name=signal.strategy_name,
            order_type=self.order_type,
            time_in_force=self.time_in_force,
            metadata={
                "effective_price": str(sizing.effective_price),
                "sizing_reason": sizing.reason,
                "signal_confidence": str(signal.confidence),
            },
        )
        intent.validate()
        return intent
