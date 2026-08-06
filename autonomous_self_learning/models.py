from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class TradeOutcome:
    strategy_id: str
    symbol: str
    action: str
    pnl_ratio: Decimal
    holding_minutes: int
    regime: str
    confidence: Decimal
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["pnl_ratio"] = str(value["pnl_ratio"])
        value["confidence"] = str(value["confidence"])
        return value


@dataclass(frozen=True)
class StrategyLearningSummary:
    strategy_id: str
    trade_count: int
    win_rate: Decimal
    average_return: Decimal
    average_win: Decimal
    average_loss: Decimal
    profit_factor: Decimal
    sharpe_proxy: Decimal
    max_drawdown: Decimal
    stability: Decimal
    status: str
    weakness_reasons: tuple[str, ...]
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "win_rate",
            "average_return",
            "average_win",
            "average_loss",
            "profit_factor",
            "sharpe_proxy",
            "max_drawdown",
            "stability",
        ):
            value[key] = str(value[key])
        value["weakness_reasons"] = list(self.weakness_reasons)
        value["recommendations"] = list(self.recommendations)
        return value
