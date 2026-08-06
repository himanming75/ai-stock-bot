from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class PortfolioCandidate:
    symbol: str
    sector: str
    action: str
    confidence: Decimal
    volatility: Decimal
    correlation_group: str
    expected_return: Decimal
    current_weight: Decimal

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "confidence",
            "volatility",
            "expected_return",
            "current_weight",
        ):
            value[key] = str(value[key])
        return value


@dataclass(frozen=True)
class AllocationDecision:
    symbol: str
    target_weight: Decimal
    current_weight: Decimal
    delta_weight: Decimal
    action: str
    reason: str
    constrained_by: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "target_weight",
            "current_weight",
            "delta_weight",
        ):
            value[key] = str(value[key])
        value["constrained_by"] = list(self.constrained_by)
        return value
