from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from strategy_engine import MarketSnapshot, SignalAction, StrategySignal


@dataclass(frozen=True)
class PositionSizingConfig:
    max_quantity: Decimal = Decimal("1")
    max_order_notional: Decimal = Decimal("100")
    cash_fraction: Decimal = Decimal("0.10")
    sell_fraction: Decimal = Decimal("1.00")
    fractional_step: Decimal = Decimal("0.001")
    slippage_buffer_bps: Decimal = Decimal("25")

    def validate(self) -> None:
        if self.max_quantity <= 0 or self.max_order_notional <= 0:
            raise ValueError("max limits must be positive")
        if not Decimal("0") < self.cash_fraction <= Decimal("1"):
            raise ValueError("cash_fraction must be in (0, 1]")
        if not Decimal("0") < self.sell_fraction <= Decimal("1"):
            raise ValueError("sell_fraction must be in (0, 1]")
        if self.fractional_step <= 0:
            raise ValueError("fractional_step must be positive")
        if self.slippage_buffer_bps < 0:
            raise ValueError("slippage_buffer_bps cannot be negative")


@dataclass(frozen=True)
class SizingResult:
    accepted: bool
    quantity: Decimal
    effective_price: Decimal
    estimated_notional: Decimal
    reason: str


class PositionSizer:
    def __init__(self, config: PositionSizingConfig) -> None:
        config.validate()
        self.config = config

    def _floor_to_step(self, value: Decimal) -> Decimal:
        steps = (value / self.config.fractional_step).to_integral_value(rounding=ROUND_DOWN)
        return steps * self.config.fractional_step

    def _effective_price(self, signal: StrategySignal) -> Decimal:
        adjustment = self.config.slippage_buffer_bps / Decimal("10000")
        if signal.action == SignalAction.BUY:
            return signal.reference_price * (Decimal("1") + adjustment)
        if signal.action == SignalAction.SELL:
            return signal.reference_price * (Decimal("1") - adjustment)
        return signal.reference_price

    def size(self, signal: StrategySignal, snapshot: MarketSnapshot) -> SizingResult:
        signal.validate()
        snapshot.validate()

        if signal.action == SignalAction.HOLD:
            return SizingResult(False, Decimal("0"), signal.reference_price, Decimal("0"), "hold_signal")

        effective_price = self._effective_price(signal)
        if effective_price <= 0:
            return SizingResult(False, Decimal("0"), effective_price, Decimal("0"), "invalid_effective_price")

        if signal.action == SignalAction.BUY:
            capital_budget = min(
                snapshot.cash_available * self.config.cash_fraction,
                self.config.max_order_notional,
            )
            raw_quantity = capital_budget / effective_price
        else:
            raw_quantity = snapshot.position_quantity * self.config.sell_fraction

        raw_quantity = min(raw_quantity, self.config.max_quantity)
        quantity = self._floor_to_step(raw_quantity)

        if quantity <= 0:
            return SizingResult(False, Decimal("0"), effective_price, Decimal("0"), "quantity_below_step")

        estimated_notional = quantity * effective_price
        if estimated_notional > self.config.max_order_notional:
            quantity = self._floor_to_step(self.config.max_order_notional / effective_price)
            estimated_notional = quantity * effective_price

        if quantity <= 0:
            return SizingResult(False, Decimal("0"), effective_price, Decimal("0"), "notional_too_small")

        if signal.action == SignalAction.SELL and quantity > snapshot.position_quantity:
            return SizingResult(False, Decimal("0"), effective_price, Decimal("0"), "insufficient_position")

        if signal.action == SignalAction.BUY and estimated_notional > snapshot.cash_available:
            return SizingResult(False, Decimal("0"), effective_price, Decimal("0"), "insufficient_cash")

        return SizingResult(True, quantity, effective_price, estimated_notional, "accepted")
