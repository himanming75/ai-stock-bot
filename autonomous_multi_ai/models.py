from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class AIVote:
    voter_id: str
    action: str
    confidence: Decimal
    weight: Decimal
    reason: str
    veto: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["confidence"] = str(value["confidence"])
        value["weight"] = str(value["weight"])
        return value


@dataclass(frozen=True)
class VotingDecision:
    final_action: str
    weighted_scores: dict[str, Decimal]
    winning_score: Decimal
    consensus_ratio: Decimal
    veto_applied: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["weighted_scores"] = {
            key: str(score)
            for key, score in self.weighted_scores.items()
        }
        value["winning_score"] = str(value["winning_score"])
        value["consensus_ratio"] = str(value["consensus_ratio"])
        return value


@dataclass(frozen=True)
class StrategyPerformance:
    strategy_id: str
    trade_count: int
    win_rate: Decimal
    expected_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    stability: Decimal

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "win_rate",
            "expected_return",
            "sharpe_ratio",
            "max_drawdown",
            "stability",
        ):
            value[key] = str(value[key])
        return value
