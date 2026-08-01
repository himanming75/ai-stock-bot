from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class RiskDecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    HALTED = "HALTED"


@dataclass(frozen=True)
class RiskLimits:
    max_daily_loss: Decimal = Decimal("50")
    max_drawdown: Decimal = Decimal("100")
    max_symbol_exposure: Decimal = Decimal("250")
    max_total_exposure: Decimal = Decimal("500")
    max_open_positions: int = 3
    max_consecutive_losses: int = 3
    allow_new_buys: bool = True

    def validate(self) -> None:
        if self.max_daily_loss <= 0:
            raise ValueError("max_daily_loss must be positive")
        if self.max_drawdown <= 0:
            raise ValueError("max_drawdown must be positive")
        if self.max_symbol_exposure <= 0:
            raise ValueError("max_symbol_exposure must be positive")
        if self.max_total_exposure <= 0:
            raise ValueError("max_total_exposure must be positive")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if self.max_consecutive_losses < 1:
            raise ValueError("max_consecutive_losses must be at least 1")


@dataclass(frozen=True)
class RiskDecision:
    status: RiskDecisionStatus
    reason: str
    checked_at: datetime
    intent_id: str | None = None
    symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskSnapshot:
    captured_at: datetime
    kill_switch_engaged: bool
    emergency_stop_engaged: bool
    new_buys_allowed: bool
    daily_realized_pnl: Decimal
    current_equity: Decimal
    peak_equity: Decimal
    drawdown: Decimal
    total_exposure: Decimal
    open_position_count: int
    consecutive_losses: int
    last_decision: RiskDecision | None
