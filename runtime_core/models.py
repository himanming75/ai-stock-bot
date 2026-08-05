from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    symbol: str
    side: str
    strength: Decimal
    reference_price: Decimal
    reason: str

    def validate(self) -> dict[str, Any]:
        checks = {
            "strategy_id_present": bool(self.strategy_id),
            "symbol_present": bool(self.symbol),
            "side_valid": self.side in {"buy", "sell", "hold"},
            "strength_in_range": Decimal("0") <= self.strength <= Decimal("1"),
            "reference_price_positive": self.reference_price > 0,
            "reason_present": bool(self.reason),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }


@dataclass(frozen=True)
class AllocationDecision:
    symbol: str
    side: str
    approved_notional: Decimal
    requested_notional: Decimal
    allocation_fraction: Decimal
    blocked: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "approved_notional": str(self.approved_notional),
            "requested_notional": str(self.requested_notional),
            "allocation_fraction": str(self.allocation_fraction),
            "blocked": self.blocked,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class OrderCandidate:
    candidate_id: str
    strategy_id: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    notional: Decimal
    reference_price: Decimal
    broker_mode: str
    submit_allowed: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "notional": str(self.notional),
            "reference_price": str(self.reference_price),
            "broker_mode": self.broker_mode,
            "submit_allowed": self.submit_allowed,
        }
