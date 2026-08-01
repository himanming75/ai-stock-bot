from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutonomousRuntimeConfig:
    symbol: str = "AAPL"
    max_quantity: int = 1
    max_order_notional: float = 100.0
    allow_fractional: bool = False
    require_market_open: bool = True
    read_network_enabled: bool = False
    single_order_write_enabled: bool = False
    live_trading_enabled: bool = False

    def validate(self) -> None:
        if self.symbol not in {"AAPL", "SPY", "QQQ"}:
            raise ValueError("symbol is not in the approved autonomous Paper list")
        if self.max_quantity != 1:
            raise ValueError("max_quantity must remain exactly 1")
        if self.max_order_notional <= 0 or self.max_order_notional > 100:
            raise ValueError("max_order_notional must be between 0 and 100")
        if self.allow_fractional:
            raise ValueError("fractional autonomous orders are disabled")
        if self.live_trading_enabled:
            raise ValueError("live trading is not supported")
        if self.single_order_write_enabled and not self.read_network_enabled:
            raise ValueError("write opt-in requires read network opt-in")
