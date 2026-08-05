from __future__ import annotations
from decimal import Decimal
from typing import Any


class StrategyPlugin:
    strategy_id = "base"
    version = "0.0.0"
    category = "UNKNOWN"

    def metadata(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "category": self.category,
            "plugin_state": "READY_OFFLINE",
        }

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MomentumPlugin(StrategyPlugin):
    strategy_id = "momentum_v3"
    version = "3.0.0"
    category = "TREND"

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        momentum = Decimal(str(features.get("momentum", "0")))
        score = max(Decimal("0"), min(Decimal("1"), Decimal("0.5") + momentum * 5))
        return self._result(score, momentum > Decimal("0.02"))

    def _result(self, score: Decimal, active: bool) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "score": str(score.quantize(Decimal("0.0001"))),
            "signal": "BUY_PREVIEW" if active else "HOLD",
            "order_created": False,
        }


class MeanReversionPlugin(StrategyPlugin):
    strategy_id = "mean_reversion_v3"
    version = "3.0.0"
    category = "MEAN_REVERSION"

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        z = Decimal(str(features.get("z_score", "0")))
        score = max(Decimal("0"), min(Decimal("1"), abs(z) / 3))
        signal = "BUY_PREVIEW" if z <= Decimal("-1.5") else "HOLD"
        return {
            "strategy_id": self.strategy_id,
            "score": str(score.quantize(Decimal("0.0001"))),
            "signal": signal,
            "order_created": False,
        }


class BreakoutPlugin(StrategyPlugin):
    strategy_id = "breakout_v3"
    version = "3.0.0"
    category = "BREAKOUT"

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        breakout = bool(features.get("breakout"))
        volume = Decimal(str(features.get("relative_volume", "1")))
        score = min(Decimal("1"), Decimal("0.4") + volume / 3) if breakout else Decimal("0.2")
        return {
            "strategy_id": self.strategy_id,
            "score": str(score.quantize(Decimal("0.0001"))),
            "signal": "BUY_PREVIEW" if breakout and volume > 1 else "HOLD",
            "order_created": False,
        }


class ScalpingPlugin(StrategyPlugin):
    strategy_id = "scalping_v1"
    version = "1.0.0"
    category = "INTRADAY"

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        spread = Decimal(str(features.get("spread_bps", "999")))
        score = max(Decimal("0"), Decimal("1") - spread / Decimal("20"))
        return {
            "strategy_id": self.strategy_id,
            "score": str(score.quantize(Decimal("0.0001"))),
            "signal": "BUY_PREVIEW" if spread <= 5 else "HOLD",
            "order_created": False,
        }


class SwingPlugin(StrategyPlugin):
    strategy_id = "swing_v1"
    version = "1.0.0"
    category = "SWING"

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        trend = Decimal(str(features.get("trend_strength", "0")))
        score = max(Decimal("0"), min(Decimal("1"), trend))
        return {
            "strategy_id": self.strategy_id,
            "score": str(score.quantize(Decimal("0.0001"))),
            "signal": "BUY_PREVIEW" if trend >= Decimal("0.7") else "HOLD",
            "order_created": False,
        }


class StrategyRegistry:
    def __init__(self) -> None:
        self._plugins = {
            "momentum_v3": MomentumPlugin(),
            "mean_reversion_v3": MeanReversionPlugin(),
            "breakout_v3": BreakoutPlugin(),
            "scalping_v1": ScalpingPlugin(),
            "swing_v1": SwingPlugin(),
        }

    def list_metadata(self) -> list[dict[str, Any]]:
        return [
            self._plugins[key].metadata()
            for key in sorted(self._plugins)
        ]

    def evaluate_all(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            self._plugins[key].evaluate(features)
            for key in sorted(self._plugins)
        ]

    def get(self, strategy_id: str) -> StrategyPlugin:
        try:
            return self._plugins[strategy_id]
        except KeyError as exc:
            raise KeyError(f"UNKNOWN_STRATEGY:{strategy_id}") from exc
