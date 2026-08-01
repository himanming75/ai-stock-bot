from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class RuntimeRiskState:
    kill_switch_engaged: bool = False
    emergency_stop_engaged: bool = False
    new_buys_allowed: bool = True
    daily_realized_pnl: Decimal = Decimal("0")
    current_equity: Decimal = Decimal("0")
    peak_equity: Decimal = Decimal("0")
    total_exposure: Decimal = Decimal("0")
    open_position_count: int = 0
    consecutive_losses: int = 0

    @property
    def drawdown(self) -> Decimal:
        return max(self.peak_equity - self.current_equity, Decimal("0"))

    def engage_kill_switch(self) -> None:
        self.kill_switch_engaged = True
        self.new_buys_allowed = False

    def engage_emergency_stop(self) -> None:
        self.emergency_stop_engaged = True
        self.new_buys_allowed = False

    def reset_session(self) -> None:
        self.kill_switch_engaged = False
        self.emergency_stop_engaged = False
        self.new_buys_allowed = True
        self.daily_realized_pnl = Decimal("0")
        self.consecutive_losses = 0
