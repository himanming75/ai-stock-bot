#!/usr/bin/env python3
"""
V42.0 Strategy Engine Foundation

Deterministic, offline-only strategy engine for:
- SMA calculations
- momentum and trend classification
- BUY / SELL / HOLD decisions
- confidence scoring
- SHA-256 decision receipts
- JSON export
- explicit live-mode safety gate

No network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence


VERSION = "42.0"


class Decision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Trend(str, Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"


class Momentum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def to_decimal(value: Any, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    return number


def positive_decimal(value: Any, name: str) -> Decimal:
    number = to_decimal(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def normalize(number: Decimal) -> str:
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


def parse_prices(values: Iterable[Any]) -> list[Decimal]:
    prices = [positive_decimal(v, "price") for v in values]
    if not prices:
        raise ValueError("at least one price is required")
    return prices


def sma(prices: Sequence[Decimal], period: int) -> Decimal | None:
    if period <= 0:
        raise ValueError("period must be greater than zero")
    if len(prices) < period:
        return None
    window = prices[-period:]
    return sum(window, Decimal("0")) / Decimal(period)


def classify_momentum(prices: Sequence[Decimal], lookback: int = 3) -> Momentum:
    if lookback <= 0:
        raise ValueError("lookback must be greater than zero")
    if len(prices) <= lookback:
        return Momentum.NEUTRAL
    delta = prices[-1] - prices[-1 - lookback]
    if delta > 0:
        return Momentum.POSITIVE
    if delta < 0:
        return Momentum.NEGATIVE
    return Momentum.NEUTRAL


def classify_trend(
    short_sma: Decimal | None,
    long_sma: Decimal | None,
    tolerance_pct: Decimal = Decimal("0.001"),
) -> Trend:
    if short_sma is None or long_sma is None:
        return Trend.SIDEWAYS
    if long_sma == 0:
        return Trend.SIDEWAYS
    diff_pct = (short_sma - long_sma) / long_sma
    if diff_pct > tolerance_pct:
        return Trend.UPTREND
    if diff_pct < -tolerance_pct:
        return Trend.DOWNTREND
    return Trend.SIDEWAYS


@dataclass(frozen=True)
class StrategyConfig:
    short_period: int = 5
    medium_period: int = 10
    long_period: int = 20
    momentum_lookback: int = 3
    minimum_confidence: int = 60
    tolerance_pct: str = "0.001"

    def validate(self) -> None:
        if min(self.short_period, self.medium_period, self.long_period) <= 0:
            raise ValueError("SMA periods must be greater than zero")
        if not (self.short_period < self.medium_period < self.long_period):
            raise ValueError("SMA periods must satisfy short < medium < long")
        if self.momentum_lookback <= 0:
            raise ValueError("momentum_lookback must be greater than zero")
        if not 0 <= self.minimum_confidence <= 100:
            raise ValueError("minimum_confidence must be between 0 and 100")
        if to_decimal(self.tolerance_pct, "tolerance_pct") < 0:
            raise ValueError("tolerance_pct must be zero or greater")


@dataclass(frozen=True)
class StrategyResult:
    schema_version: str
    version: str
    symbol: str
    mode: str
    decision: str
    confidence: int
    trend: str
    momentum: str
    latest_price: str
    sma_short: str | None
    sma_medium: str | None
    sma_long: str | None
    price_count: int
    reasons: list[str]
    network_used: bool
    decision_sha256: str


class StrategyEngine:
    def __init__(
        self,
        config: StrategyConfig | None = None,
        *,
        mode: str = "replay",
        enable_live: bool = False,
    ) -> None:
        self.config = config or StrategyConfig()
        self.config.validate()
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live market transport is intentionally not implemented in V42.0"
            )

    def evaluate(self, symbol: str, prices: Iterable[Any]) -> StrategyResult:
        self._live_gate()
        clean_symbol = symbol.strip().upper()
        if not clean_symbol:
            raise ValueError("symbol is required")

        parsed = parse_prices(prices)
        short = sma(parsed, self.config.short_period)
        medium = sma(parsed, self.config.medium_period)
        long = sma(parsed, self.config.long_period)
        momentum = classify_momentum(parsed, self.config.momentum_lookback)
        trend = classify_trend(
            short,
            long,
            to_decimal(self.config.tolerance_pct, "tolerance_pct"),
        )

        score = 50
        reasons: list[str] = []

        if trend is Trend.UPTREND:
            score += 25
            reasons.append("Short SMA is above long SMA.")
        elif trend is Trend.DOWNTREND:
            score -= 25
            reasons.append("Short SMA is below long SMA.")
        else:
            reasons.append("SMA trend is sideways or insufficient.")

        if momentum is Momentum.POSITIVE:
            score += 20
            reasons.append("Momentum is positive.")
        elif momentum is Momentum.NEGATIVE:
            score -= 20
            reasons.append("Momentum is negative.")
        else:
            reasons.append("Momentum is neutral.")

        if short is not None and medium is not None:
            if short > medium:
                score += 5
                reasons.append("Short SMA is above medium SMA.")
            elif short < medium:
                score -= 5
                reasons.append("Short SMA is below medium SMA.")

        confidence = max(0, min(100, abs(score - 50) * 2))

        if score >= 50 + self.config.minimum_confidence // 2:
            decision = Decision.BUY
        elif score <= 50 - self.config.minimum_confidence // 2:
            decision = Decision.SELL
        else:
            decision = Decision.HOLD

        if len(parsed) < self.config.long_period:
            decision = Decision.HOLD
            confidence = min(confidence, 50)
            reasons.append("Not enough prices for the long SMA; decision forced to HOLD.")

        core = {
            "schema_version": "v42.0.strategy_result.1",
            "version": VERSION,
            "symbol": clean_symbol,
            "mode": self.mode,
            "decision": decision.value,
            "confidence": confidence,
            "trend": trend.value,
            "momentum": momentum.value,
            "latest_price": normalize(parsed[-1]),
            "sma_short": normalize(short) if short is not None else None,
            "sma_medium": normalize(medium) if medium is not None else None,
            "sma_long": normalize(long) if long is not None else None,
            "price_count": len(parsed),
            "reasons": reasons,
            "network_used": False,
        }
        return StrategyResult(**core, decision_sha256=canonical_hash(core))

    @staticmethod
    def export(path: Path, result: StrategyResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v42.0.strategy_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_price_text(value: str) -> list[str]:
    parts = [part.strip() for part in value.split(",")]
    return [part for part in parts if part]


def load_prices(path: Path) -> list[Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("prices")
    if not isinstance(payload, list):
        raise ValueError("input JSON must be a list or contain a prices list")
    return payload


def demo_prices(kind: str) -> list[str]:
    if kind == "buy":
        return [str(100 + i) for i in range(25)]
    if kind == "sell":
        return [str(125 - i) for i in range(25)]
    return ["100"] * 25


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V42.0 Strategy Engine Foundation")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="replay")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--prices")
    parser.add_argument("--input")
    parser.add_argument("--demo", choices=["buy", "sell", "hold"], default="buy")
    parser.add_argument("--short-period", type=int, default=5)
    parser.add_argument("--medium-period", type=int, default=10)
    parser.add_argument("--long-period", type=int, default=20)
    parser.add_argument("--momentum-lookback", type=int, default=3)
    parser.add_argument("--minimum-confidence", type=int, default=60)
    parser.add_argument(
        "--output",
        default="release/v42/audit/strategy_engine_result_v42_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = StrategyConfig(
        short_period=args.short_period,
        medium_period=args.medium_period,
        long_period=args.long_period,
        momentum_lookback=args.momentum_lookback,
        minimum_confidence=args.minimum_confidence,
    )
    engine = StrategyEngine(config, mode=args.mode, enable_live=args.enable_live)

    try:
        if args.input:
            prices = load_prices(Path(args.input))
        elif args.prices:
            prices = parse_price_text(args.prices)
        else:
            prices = demo_prices(args.demo)

        result = engine.evaluate(args.symbol, prices)
        engine.export(Path(args.output), result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0
    except (ValueError, PermissionError, NotImplementedError) as exc:
        error = {
            "schema_version": "v42.0.strategy_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(error, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
