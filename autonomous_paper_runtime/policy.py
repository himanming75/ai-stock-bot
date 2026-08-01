from __future__ import annotations

from .config import AutonomousRuntimeConfig
from .models import AutonomousDecision


class AutonomousDecisionPolicy:
    def __init__(self, config: AutonomousRuntimeConfig) -> None:
        config.validate()
        self.config = config

    def decide(
        self,
        *,
        market_open: bool,
        signal_action: str,
        estimated_price: float,
    ) -> AutonomousDecision:
        if self.config.require_market_open and not market_open:
            return AutonomousDecision.WAIT_MARKET_CLOSED
        if signal_action.upper() != "BUY":
            return AutonomousDecision.WAIT_NO_SIGNAL
        if not self.config.read_network_enabled:
            return AutonomousDecision.BLOCKED_READ_DISABLED
        if not self.config.single_order_write_enabled:
            return AutonomousDecision.PREVIEW_ORDER
        if estimated_price <= 0:
            raise ValueError("estimated_price must be positive")
        if estimated_price * self.config.max_quantity > self.config.max_order_notional:
            return AutonomousDecision.BLOCKED_WRITE_DISABLED
        return AutonomousDecision.SUBMIT_SINGLE_PAPER_ORDER
