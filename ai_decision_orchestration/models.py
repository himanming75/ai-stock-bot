from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


def D(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class DecisionPolicy:
    maximum_symbols: int = 3
    minimum_score: Decimal = Decimal("0.55")
    minimum_confidence: Decimal = Decimal("0.70")
    maximum_symbol_weight: Decimal = Decimal("0.40")
    maximum_total_weight: Decimal = Decimal("0.90")
    neutral_selection_allowed: bool = True
    blocked_biases: tuple[str, ...] = ("BLOCKED", "AVOID")

    @classmethod
    def from_mapping(cls, data: dict | None) -> "DecisionPolicy":
        data = data or {}
        return cls(
            maximum_symbols=int(data.get("maximum_symbols", 3)),
            minimum_score=D(data.get("minimum_score"), "0.55"),
            minimum_confidence=D(data.get("minimum_confidence"), "0.70"),
            maximum_symbol_weight=D(data.get("maximum_symbol_weight"), "0.40"),
            maximum_total_weight=D(data.get("maximum_total_weight"), "0.90"),
            neutral_selection_allowed=bool(data.get("neutral_selection_allowed", True)),
            blocked_biases=tuple(data.get("blocked_biases", ("BLOCKED", "AVOID"))),
        )


@dataclass(frozen=True)
class SymbolDecision:
    symbol: str
    selected: bool
    rank: int | None
    composite_score: Decimal
    confidence: Decimal
    trade_bias: str
    target_weight: Decimal
    strategy_route: str
    risk_mode: str
    reason_codes: tuple[str, ...]
    blockers: tuple[str, ...]

    def as_json(self) -> dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, tuple):
                data[key] = list(value)
        return data


@dataclass(frozen=True)
class OrchestrationResult:
    status: str
    market_regime: str
    risk_mode: str
    selected_symbols: tuple[str, ...]
    decisions: tuple[SymbolDecision, ...]
    portfolio_weight: Decimal
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_json(self) -> dict:
        return {
            "status": self.status,
            "market_regime": self.market_regime,
            "risk_mode": self.risk_mode,
            "selected_symbols": list(self.selected_symbols),
            "decisions": [x.as_json() for x in self.decisions],
            "portfolio_weight": str(self.portfolio_weight),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }
