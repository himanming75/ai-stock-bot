from __future__ import annotations

"""
V26.1 Offline Multi-Asset Engine

Deterministic, offline-only portfolio simulation for multiple symbols.

Features:
- synchronized multi-symbol OHLCV replay
- independent positions per symbol
- equal-weight capital allocation
- per-symbol and portfolio exposure limits
- maximum open-position limit
- commission and slippage simulation
- trade logs, equity curve, symbol P&L, and portfolio weights
- canonical SHA-256 result hash
- JSON save/load and tamper detection

Safety boundary:
- no network access
- no broker/account APIs
- no real order submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

VERSION = "26.1"
ZERO = Decimal("0")
CENT = Decimal("0.01")
QTY_STEP = Decimal("0.000001")
FOUR = Decimal("0.0001")


class MultiAssetError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise MultiAssetError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise MultiAssetError("decimal value must be finite")
    return result


def _money(value: Any) -> Decimal:
    return _d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _qty(value: Any) -> Decimal:
    return _d(value).quantize(QTY_STEP, rounding=ROUND_DOWN)


def _four(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise MultiAssetError("invalid symbol")
    return result


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AssetBar:
    symbol: str
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class MultiAssetPolicy:
    starting_cash: Decimal = Decimal("100000.00")
    max_open_positions: int = 4
    max_symbol_weight: Decimal = Decimal("0.30")
    max_gross_exposure: Decimal = Decimal("0.90")
    commission_per_order: Decimal = Decimal("1.00")
    slippage_bps: Decimal = Decimal("5")
    fast_period: int = 3
    slow_period: int = 6
    min_bars_before_trade: int = 6

    def __post_init__(self) -> None:
        if _money(self.starting_cash) <= ZERO:
            raise MultiAssetError("starting_cash must be positive")
        if self.max_open_positions <= 0:
            raise MultiAssetError("max_open_positions must be positive")
        for name in ("max_symbol_weight", "max_gross_exposure"):
            value = _d(getattr(self, name))
            if value <= ZERO or value > Decimal("1"):
                raise MultiAssetError(f"{name} must be within (0, 1]")
        if _d(self.max_symbol_weight) > _d(self.max_gross_exposure):
            raise MultiAssetError("symbol weight cannot exceed gross exposure")
        if _d(self.commission_per_order) < ZERO or _d(self.slippage_bps) < ZERO:
            raise MultiAssetError("fees cannot be negative")
        if self.fast_period <= 0 or self.slow_period <= 0:
            raise MultiAssetError("periods must be positive")
        if self.fast_period >= self.slow_period:
            raise MultiAssetError("fast_period must be below slow_period")
        if self.min_bars_before_trade < self.slow_period:
            raise MultiAssetError("min_bars_before_trade must be at least slow_period")


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    last_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return _money(self.quantity * self.last_price)


@dataclass(frozen=True)
class Trade:
    symbol: str
    side: str
    timestamp: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    realized_pnl: Decimal
    reason: str


@dataclass(frozen=True)
class PortfolioPoint:
    timestamp: str
    cash: Decimal
    gross_exposure: Decimal
    equity: Decimal
    drawdown_pct: Decimal


@dataclass(frozen=True)
class SymbolSummary:
    symbol: str
    realized_pnl: Decimal
    trades: int
    ending_weight: Decimal


@dataclass(frozen=True)
class MultiAssetResult:
    version: str
    symbols: tuple[str, ...]
    starting_cash: Decimal
    ending_equity: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    total_trades: int
    trades: tuple[Trade, ...]
    equity_curve: tuple[PortfolioPoint, ...]
    symbol_summaries: tuple[SymbolSummary, ...]
    result_hash: str


def _bar_payload(bar: AssetBar) -> dict[str, str]:
    return {
        "symbol": bar.symbol,
        "timestamp": bar.timestamp,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
    }


def _trade_payload(trade: Trade) -> dict[str, str]:
    return {
        "symbol": trade.symbol,
        "side": trade.side,
        "timestamp": trade.timestamp,
        "quantity": str(trade.quantity),
        "price": str(trade.price),
        "commission": str(trade.commission),
        "realized_pnl": str(trade.realized_pnl),
        "reason": trade.reason,
    }


def _point_payload(point: PortfolioPoint) -> dict[str, str]:
    return {
        "timestamp": point.timestamp,
        "cash": str(point.cash),
        "gross_exposure": str(point.gross_exposure),
        "equity": str(point.equity),
        "drawdown_pct": str(point.drawdown_pct),
    }


def _summary_payload(summary: SymbolSummary) -> dict[str, str]:
    return {
        "symbol": summary.symbol,
        "realized_pnl": str(summary.realized_pnl),
        "trades": str(summary.trades),
        "ending_weight": str(summary.ending_weight),
    }


def _result_payload(result: MultiAssetResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "symbols": list(result.symbols),
        "starting_cash": str(result.starting_cash),
        "ending_equity": str(result.ending_equity),
        "total_return_pct": str(result.total_return_pct),
        "max_drawdown_pct": str(result.max_drawdown_pct),
        "total_trades": result.total_trades,
        "trades": [_trade_payload(t) for t in result.trades],
        "equity_curve": [_point_payload(p) for p in result.equity_curve],
        "symbol_summaries": [_summary_payload(s) for s in result.symbol_summaries],
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_bar(bar: AssetBar) -> AssetBar:
    symbol = _symbol(bar.symbol)
    if not bar.timestamp:
        raise MultiAssetError("timestamp required")
    o, h, l, c = map(_money, (bar.open, bar.high, bar.low, bar.close))
    volume = _qty(bar.volume)
    if min(o, h, l, c) <= ZERO or volume < ZERO:
        raise MultiAssetError("invalid OHLCV values")
    if h < max(o, l, c) or l > min(o, h, c):
        raise MultiAssetError("invalid OHLC range")
    return AssetBar(symbol, bar.timestamp, o, h, l, c, volume)


def _ema(values: list[Decimal], period: int) -> Decimal:
    alpha = Decimal("2") / Decimal(period + 1)
    current = values[0]
    for value in values[1:]:
        current = value * alpha + current * (Decimal("1") - alpha)
    return _four(current)


def _signal(history: list[AssetBar], policy: MultiAssetPolicy) -> str:
    closes = [bar.close for bar in history]
    fast = _ema(closes[-policy.slow_period:], policy.fast_period)
    slow = _ema(closes[-policy.slow_period:], policy.slow_period)
    if fast > slow:
        return "BUY"
    if fast < slow:
        return "SELL"
    return "HOLD"


def _fill(price: Decimal, side: str, bps: Decimal) -> Decimal:
    delta = bps / Decimal("10000")
    factor = Decimal("1") + delta if side == "BUY" else Decimal("1") - delta
    return _money(price * factor)


def run_multi_asset_backtest(
    bars: Iterable[AssetBar],
    policy: MultiAssetPolicy | None = None,
) -> MultiAssetResult:
    selected = policy or MultiAssetPolicy()
    normalized = tuple(sorted(
        (_normalize_bar(bar) for bar in bars),
        key=lambda bar: (bar.timestamp, bar.symbol),
    ))
    if not normalized:
        raise MultiAssetError("bars cannot be empty")

    keys = [(bar.symbol, bar.timestamp) for bar in normalized]
    if len(keys) != len(set(keys)):
        raise MultiAssetError("duplicate symbol/timestamp bars detected")

    symbols = tuple(sorted({bar.symbol for bar in normalized}))
    histories: dict[str, list[AssetBar]] = {symbol: [] for symbol in symbols}
    positions: dict[str, Position] = {}
    realized: dict[str, Decimal] = {symbol: ZERO for symbol in symbols}
    trade_counts: dict[str, int] = {symbol: 0 for symbol in symbols}
    trades: list[Trade] = []
    curve: list[PortfolioPoint] = []

    grouped: dict[str, list[AssetBar]] = {}
    for bar in normalized:
        grouped.setdefault(bar.timestamp, []).append(bar)

    cash = _money(selected.starting_cash)
    peak_equity = cash

    for timestamp in sorted(grouped):
        current_bars = sorted(grouped[timestamp], key=lambda bar: bar.symbol)

        for bar in current_bars:
            histories[bar.symbol].append(bar)
            if bar.symbol in positions:
                positions[bar.symbol] = replace(positions[bar.symbol], last_price=bar.close)

        for bar in current_bars:
            history = histories[bar.symbol]
            if len(history) < selected.min_bars_before_trade:
                continue

            signal = _signal(history, selected)
            position = positions.get(bar.symbol)

            if position is not None and signal == "SELL":
                exit_price = _fill(bar.close, "SELL", _d(selected.slippage_bps))
                commission = _money(selected.commission_per_order)
                proceeds = _money(position.quantity * exit_price - commission)
                pnl = _money(
                    (exit_price - position.entry_price) * position.quantity
                    - commission
                    - _money(selected.commission_per_order)
                )
                cash = _money(cash + proceeds)
                realized[bar.symbol] = _money(realized[bar.symbol] + pnl)
                trade_counts[bar.symbol] += 1
                trades.append(Trade(
                    bar.symbol, "SELL", timestamp, position.quantity,
                    exit_price, commission, pnl, "SIGNAL_EXIT",
                ))
                del positions[bar.symbol]
                continue

            if position is None and signal == "BUY":
                if len(positions) >= selected.max_open_positions:
                    continue

                gross_before = _money(sum((p.market_value for p in positions.values()), ZERO))
                equity_before = _money(cash + gross_before)
                symbol_budget = _money(equity_before * _d(selected.max_symbol_weight))
                gross_room = _money(
                    equity_before * _d(selected.max_gross_exposure) - gross_before
                )
                allocation = min(symbol_budget, gross_room, cash)
                commission = _money(selected.commission_per_order)
                entry_price = _fill(bar.close, "BUY", _d(selected.slippage_bps))
                qty = _qty(max(allocation - commission, ZERO) / entry_price)

                if qty <= ZERO:
                    continue

                cost = _money(qty * entry_price + commission)
                if cost > cash:
                    continue

                cash = _money(cash - cost)
                positions[bar.symbol] = Position(
                    bar.symbol, qty, entry_price, bar.close
                )
                trade_counts[bar.symbol] += 1
                trades.append(Trade(
                    bar.symbol, "BUY", timestamp, qty, entry_price,
                    commission, ZERO, "SIGNAL_ENTRY",
                ))

        gross = _money(sum((p.market_value for p in positions.values()), ZERO))
        equity = _money(cash + gross)
        peak_equity = max(peak_equity, equity)
        drawdown = _four((equity - peak_equity) / peak_equity * Decimal("100"))
        curve.append(PortfolioPoint(timestamp, cash, gross, equity, drawdown))

    if not curve:
        raise MultiAssetError("no synchronized portfolio points were created")

    last_timestamp = curve[-1].timestamp
    for symbol in sorted(tuple(positions)):
        position = positions[symbol]
        exit_price = _fill(position.last_price, "SELL", _d(selected.slippage_bps))
        commission = _money(selected.commission_per_order)
        proceeds = _money(position.quantity * exit_price - commission)
        pnl = _money(
            (exit_price - position.entry_price) * position.quantity
            - commission
            - _money(selected.commission_per_order)
        )
        cash = _money(cash + proceeds)
        realized[symbol] = _money(realized[symbol] + pnl)
        trade_counts[symbol] += 1
        trades.append(Trade(
            symbol, "SELL", last_timestamp, position.quantity,
            exit_price, commission, pnl, "END_OF_DATA",
        ))
        del positions[symbol]

    final_peak = max(peak_equity, cash)
    final_drawdown = _four((cash - final_peak) / final_peak * Decimal("100"))
    curve[-1] = PortfolioPoint(last_timestamp, cash, ZERO, cash, final_drawdown)

    summaries = tuple(
        SymbolSummary(
            symbol=symbol,
            realized_pnl=_money(realized[symbol]),
            trades=trade_counts[symbol],
            ending_weight=ZERO,
        )
        for symbol in symbols
    )

    total_return = _four(
        (cash - _money(selected.starting_cash))
        / _money(selected.starting_cash)
        * Decimal("100")
    )
    max_drawdown = min((point.drawdown_pct for point in curve), default=ZERO)

    result = MultiAssetResult(
        version=VERSION,
        symbols=symbols,
        starting_cash=_money(selected.starting_cash),
        ending_equity=cash,
        total_return_pct=total_return,
        max_drawdown_pct=max_drawdown,
        total_trades=len(trades),
        trades=tuple(trades),
        equity_curve=tuple(curve),
        symbol_summaries=summaries,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: MultiAssetResult) -> bool:
    if result.version != VERSION:
        raise MultiAssetError("unsupported result version")
    if result.total_trades != len(result.trades):
        raise MultiAssetError("trade count mismatch")
    if not result.equity_curve:
        raise MultiAssetError("equity curve cannot be empty")
    if result.ending_equity != result.equity_curve[-1].equity:
        raise MultiAssetError("ending equity mismatch")
    if tuple(sorted(result.symbols)) != result.symbols:
        raise MultiAssetError("symbols must be sorted")
    if tuple(summary.symbol for summary in result.symbol_summaries) != result.symbols:
        raise MultiAssetError("symbol summary index mismatch")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise MultiAssetError("result hash mismatch")
    return True


def save_result(result: MultiAssetResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> MultiAssetResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    trades = tuple(Trade(
        symbol=item["symbol"],
        side=item["side"],
        timestamp=item["timestamp"],
        quantity=_d(item["quantity"]),
        price=_d(item["price"]),
        commission=_d(item["commission"]),
        realized_pnl=_d(item["realized_pnl"]),
        reason=item["reason"],
    ) for item in payload["trades"])
    curve = tuple(PortfolioPoint(
        timestamp=item["timestamp"],
        cash=_d(item["cash"]),
        gross_exposure=_d(item["gross_exposure"]),
        equity=_d(item["equity"]),
        drawdown_pct=_d(item["drawdown_pct"]),
    ) for item in payload["equity_curve"])
    summaries = tuple(SymbolSummary(
        symbol=item["symbol"],
        realized_pnl=_d(item["realized_pnl"]),
        trades=int(item["trades"]),
        ending_weight=_d(item["ending_weight"]),
    ) for item in payload["symbol_summaries"])

    result = MultiAssetResult(
        version=payload["version"],
        symbols=tuple(payload["symbols"]),
        starting_cash=_d(payload["starting_cash"]),
        ending_equity=_d(payload["ending_equity"]),
        total_return_pct=_d(payload["total_return_pct"]),
        max_drawdown_pct=_d(payload["max_drawdown_pct"]),
        total_trades=int(payload["total_trades"]),
        trades=trades,
        equity_curve=curve,
        symbol_summaries=summaries,
        result_hash=payload["result_hash"],
    )
    verify_result(result)
    return result


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
