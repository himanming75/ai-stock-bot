from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

def D(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return value if isinstance(value, Decimal) else Decimal(str(value))

@dataclass(frozen=True)
class ExecutionBridgeConfig:
    default_reference_prices: dict[str, Decimal]
    spread_bps: Decimal = Decimal("2")
    volatility: Decimal = Decimal("0.20")
    urgency: Decimal = Decimal("0.50")
    maximum_order_notional: Decimal = Decimal("5000")
    allow_fractional: bool = True

    @classmethod
    def from_mapping(cls, data: dict) -> "ExecutionBridgeConfig":
        prices = {
            str(k).upper(): D(v)
            for k, v in data.get("default_reference_prices", {}).items()
        }
        return cls(
            default_reference_prices=prices,
            spread_bps=D(data.get("spread_bps"), "2"),
            volatility=D(data.get("volatility"), "0.20"),
            urgency=D(data.get("urgency"), "0.50"),
            maximum_order_notional=D(data.get("maximum_order_notional"), "5000"),
            allow_fractional=bool(data.get("allow_fractional", True)),
        )

@dataclass(frozen=True)
class ExecutionBridgeDecision:
    symbol: str
    approved_notional: Decimal
    reference_price: Decimal
    quantity: Decimal
    side: str
    order_type: str
    slice_count: int
    limit_price: Decimal | None
    expected_slippage_bps: Decimal
    time_limit_seconds: int
    blocked: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict:
        result = asdict(self)
        for key, value in list(result.items()):
            if isinstance(value, Decimal):
                result[key] = str(value)
            elif isinstance(value, tuple):
                result[key] = list(value)
        return result
