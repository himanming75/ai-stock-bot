from __future__ import annotations
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from .models import Signal


class StrategyPlugin(ABC):
    strategy_id: str
    supported_horizons: tuple[str, ...]

    @abstractmethod
    def generate_signals(
        self,
        *,
        market_snapshot: dict[str, Any],
        runtime_snapshot: dict[str, Any],
    ) -> list[Signal]:
        raise NotImplementedError


class DeterministicFixtureStrategy(StrategyPlugin):
    strategy_id = "fixture_momentum_v1"
    supported_horizons = (
        "ultra_short",
        "day",
        "swing",
        "position",
    )

    def generate_signals(
        self,
        *,
        market_snapshot: dict[str, Any],
        runtime_snapshot: dict[str, Any],
    ) -> list[Signal]:
        symbols = runtime_snapshot.get("allowed_symbols", [])
        prices = market_snapshot.get("prices", {})
        signals: list[Signal] = []
        for index, symbol in enumerate(symbols):
            price = Decimal(str(prices.get(symbol, "0")))
            if price <= 0:
                continue
            side = "buy" if index == 0 else "hold"
            strength = Decimal("0.80") if side == "buy" else Decimal("0.20")
            signals.append(Signal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                side=side,
                strength=strength,
                reference_price=price,
                reason="OFFLINE_DETERMINISTIC_FIXTURE",
            ))
        return signals


class StrategyRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, StrategyPlugin] = {}

    def register(self, plugin: StrategyPlugin) -> None:
        if not plugin.strategy_id:
            raise ValueError("STRATEGY_ID_REQUIRED")
        if plugin.strategy_id in self._plugins:
            raise ValueError(f"DUPLICATE_STRATEGY:{plugin.strategy_id}")
        self._plugins[plugin.strategy_id] = plugin

    def get(self, strategy_id: str) -> StrategyPlugin:
        if strategy_id not in self._plugins:
            raise KeyError(f"STRATEGY_NOT_FOUND:{strategy_id}")
        return self._plugins[strategy_id]

    def catalog(self) -> dict[str, Any]:
        items = []
        for strategy_id, plugin in sorted(self._plugins.items()):
            items.append({
                "strategy_id": strategy_id,
                "supported_horizons": list(plugin.supported_horizons),
                "actual_strategy_execution_enabled": False,
            })
        return {
            "strategy_count": len(items),
            "strategies": items,
            "dynamic_loading_enabled": False,
            "untrusted_plugin_execution_enabled": False,
        }
