from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from .models import MarketSnapshot, SignalAction, StrategySignal


@dataclass(frozen=True)
class FilterDecision:
    accepted: bool
    reason: str


@dataclass
class ConfidenceFilter:
    minimum_confidence: Decimal = Decimal("0.60")

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.minimum_confidence <= Decimal("1"):
            raise ValueError("minimum_confidence must be between 0 and 1")

    def check(self, signal: StrategySignal) -> FilterDecision:
        if signal.action == SignalAction.HOLD:
            return FilterDecision(False, "hold_signal")
        if signal.confidence < self.minimum_confidence:
            return FilterDecision(False, "confidence_below_threshold")
        return FilterDecision(True, "accepted")


@dataclass
class CooldownFilter:
    cooldown_seconds: int = 60
    _last_accepted: dict[tuple[str, str], datetime] = None

    def __post_init__(self) -> None:
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")
        if self._last_accepted is None:
            self._last_accepted = {}

    def check(self, signal: StrategySignal) -> FilterDecision:
        key = (signal.strategy_name, signal.symbol)
        previous = self._last_accepted.get(key)
        if previous is not None:
            elapsed = (signal.generated_at - previous).total_seconds()
            if elapsed < self.cooldown_seconds:
                return FilterDecision(False, "cooldown_active")
        self._last_accepted[key] = signal.generated_at
        return FilterDecision(True, "accepted")


@dataclass
class RiskPreFilter:
    max_quantity: Decimal = Decimal("1")
    max_notional: Decimal = Decimal("100")
    allowed_symbols: set[str] = None

    def __post_init__(self) -> None:
        if self.max_quantity <= 0 or self.max_notional <= 0:
            raise ValueError("risk limits must be positive")
        if self.allowed_symbols is None:
            self.allowed_symbols = {"AAPL", "MSFT", "SPY"}

    def check(self, signal: StrategySignal, snapshot: MarketSnapshot) -> FilterDecision:
        if signal.symbol not in self.allowed_symbols:
            return FilterDecision(False, "symbol_not_allowed")
        if signal.suggested_quantity > self.max_quantity:
            return FilterDecision(False, "quantity_limit")
        notional = signal.suggested_quantity * signal.reference_price
        if notional > self.max_notional:
            return FilterDecision(False, "notional_limit")
        if signal.action == SignalAction.SELL and snapshot.position_quantity < signal.suggested_quantity:
            return FilterDecision(False, "insufficient_position")
        if signal.action == SignalAction.BUY and snapshot.cash_available < notional:
            return FilterDecision(False, "insufficient_cash")
        return FilterDecision(True, "accepted")
