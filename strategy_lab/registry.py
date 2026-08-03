from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    name: str
    category: str
    description: str
    parameters: dict[str, Any]
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

DEFAULT_STRATEGIES = [
    StrategyDefinition("EMA_FAST_5_20","EMA Cross 5/20","trend","Fast EMA crossover",{"fast":5,"slow":20}),
    StrategyDefinition("EMA_FAST_10_30","EMA Cross 10/30","trend","Balanced EMA crossover",{"fast":10,"slow":30}),
    StrategyDefinition("EMA_SLOW_20_50","EMA Cross 20/50","trend","Slow EMA crossover",{"fast":20,"slow":50}),
    StrategyDefinition("RSI_30_70","RSI 30/70","mean_reversion","Classic RSI reversal",{"period":14,"oversold":30,"overbought":70}),
    StrategyDefinition("RSI_35_65","RSI 35/65","mean_reversion","Moderate RSI reversal",{"period":14,"oversold":35,"overbought":65}),
    StrategyDefinition("MACD_CLASSIC","MACD Classic","trend","12/26 crossover proxy",{}),
    StrategyDefinition("MOMENTUM_10","Momentum 10","momentum","Ten-bar momentum reversal",{"period":10}),
    StrategyDefinition("MOMENTUM_15","Momentum 15","momentum","Fifteen-bar momentum reversal",{"period":15}),
    StrategyDefinition("MOMENTUM_20","Momentum 20","momentum","Twenty-bar momentum reversal",{"period":20}),
    StrategyDefinition("BOLLINGER_20_2","Bollinger 20/2","mean_reversion","Classic Bollinger reversal",{"period":20,"std":2}),
    StrategyDefinition("BOLLINGER_15_2","Bollinger 15/2","mean_reversion","Short Bollinger reversal",{"period":15,"std":2}),
]

class StrategyRegistry:
    def __init__(self):
        self._items: dict[str, StrategyDefinition] = {}

    def register(self, definition: StrategyDefinition) -> None:
        if definition.strategy_id in self._items:
            raise ValueError(f"duplicate strategy id: {definition.strategy_id}")
        self._items[definition.strategy_id] = definition

    def register_defaults(self) -> None:
        for item in DEFAULT_STRATEGIES:
            self.register(item)

    def enabled(self) -> list[StrategyDefinition]:
        return [item for item in self._items.values() if item.enabled]

    def all(self) -> list[StrategyDefinition]:
        return list(self._items.values())
