from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class QueuedOrder:
    queue_id: str
    candidate_id: str
    account_id: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    notional: Decimal
    state: str
    dispatch_allowed: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "candidate_id": self.candidate_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "notional": str(self.notional),
            "state": self.state,
            "dispatch_allowed": self.dispatch_allowed,
        }
