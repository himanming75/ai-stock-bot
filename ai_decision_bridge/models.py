from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

def D(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return value if isinstance(value, Decimal) else Decimal(str(value))

@dataclass(frozen=True)
class BridgeConfig:
    portfolio_value: Decimal = Decimal("100000")
    maximum_base_notional: Decimal = Decimal("5000")
    current_portfolio_exposure: Decimal = Decimal("0.20")
    current_sector_exposure: Decimal = Decimal("0.10")
    correlated_exposure_after: Decimal = Decimal("0.25")
    drawdown_ratio: Decimal = Decimal("0.05")
    consecutive_losses: int = 0
    daily_loss_limit_reached: bool = False
    strategy_risk_budget: Decimal = Decimal("0.80")
    default_volatility: Decimal = Decimal("0.22")

    @classmethod
    def from_mapping(cls, data: dict | None) -> "BridgeConfig":
        data = data or {}
        return cls(
            portfolio_value=D(data.get("portfolio_value"), "100000"),
            maximum_base_notional=D(data.get("maximum_base_notional"), "5000"),
            current_portfolio_exposure=D(data.get("current_portfolio_exposure"), "0.20"),
            current_sector_exposure=D(data.get("current_sector_exposure"), "0.10"),
            correlated_exposure_after=D(data.get("correlated_exposure_after"), "0.25"),
            drawdown_ratio=D(data.get("drawdown_ratio"), "0.05"),
            consecutive_losses=int(data.get("consecutive_losses", 0)),
            daily_loss_limit_reached=bool(data.get("daily_loss_limit_reached", False)),
            strategy_risk_budget=D(data.get("strategy_risk_budget"), "0.80"),
            default_volatility=D(data.get("default_volatility"), "0.22"),
        )

@dataclass(frozen=True)
class SymbolBridgeDecision:
    symbol: str
    approved: bool
    strategy_route: str
    ensemble_action: str
    ensemble_confidence: Decimal
    approved_notional: Decimal
    risk_multiplier: Decimal
    target_weight: Decimal
    target_notional: Decimal
    rebalance_required: bool
    blockers: tuple[str, ...]
    explanation: tuple[str, ...]

    def as_json(self) -> dict:
        data = asdict(self)
        for k, v in list(data.items()):
            if isinstance(v, Decimal): data[k] = str(v)
            elif isinstance(v, tuple): data[k] = list(v)
        return data

@dataclass(frozen=True)
class BridgeResult:
    status: str
    decisions: tuple[SymbolBridgeDecision, ...]
    approved_symbols: tuple[str, ...]
    total_approved_notional: Decimal
    blockers: tuple[str, ...]

    def as_json(self) -> dict:
        return {
            "status": self.status,
            "decisions": [x.as_json() for x in self.decisions],
            "approved_symbols": list(self.approved_symbols),
            "total_approved_notional": str(self.total_approved_notional),
            "blockers": list(self.blockers),
        }
