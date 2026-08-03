from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Candidate:
    symbol: str
    sector: str
    decision: str
    confidence: float
    composite_score: float
    volatility_pct: float
    max_position_pct: float
    liquidity_score: float = 100.0
    enabled: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Candidate":
        return cls(
            symbol=str(value.get("symbol", "UNKNOWN")).upper().strip(),
            sector=str(value.get("sector", "UNKNOWN")).upper().strip(),
            decision=str(value.get("decision", "HOLD")).upper().strip(),
            confidence=float(value.get("confidence", 0.0)),
            composite_score=float(value.get("composite_score", 0.0)),
            volatility_pct=float(value.get("volatility_pct", 0.0)),
            max_position_pct=float(value.get("max_position_pct", 10.0)),
            liquidity_score=float(value.get("liquidity_score", 100.0)),
            enabled=bool(value.get("enabled", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
