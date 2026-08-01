from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class RuntimeLifecycleState(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RuntimeCycleResult:
    cycle_id: int
    symbol: str
    signal_count: int
    intent_created: bool
    risk_status: str | None
    execution_status: str | None
    fill_status: str | None
    portfolio_equity: Decimal
    portfolio_cash: Decimal
    completed: bool
    reason: str
