from __future__ import annotations

"""
V25.6 Offline Backtest Engine

A deterministic, offline-only single-symbol backtest engine that:
- replays OHLCV bars sequentially
- calculates EMA, RSI, ATR, and breakout context
- generates BUY/HOLD/SELL decisions
- applies risk-based position sizing
- simulates fills with commission and slippage
- updates cash and holdings
- records trades and an equity curve
- calculates return, drawdown, win rate, profit factor, and Sharpe ratio
- protects the final result with a canonical SHA-256 hash

Safety boundary:
- no network access
- no broker/account APIs
- no real order creation or submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from hashlib import sha256
from math import sqrt
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable
import json

VERSION = "25.6"
ZERO = Decimal("0")
CENT = Decimal("0.01")
QTY_STEP = Decimal("0.000001")
FOUR = Decimal("0.0001")


class BacktestError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise BacktestError(f"invalid decimal: {value!r}") from exc
    if not result.is_finite():
        raise BacktestError("decimal must be finite")
    return result


def _money(value: Any) -> Decimal:
    return _d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _qty(value: Any) -> Decimal:
    return _d(value).quantize(QTY_STEP, rounding=ROUND_DOWN)


def _four(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise BacktestError("invalid symbol")
    return result


@dataclass(frozen=True)
class Bar:
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class BacktestPolicy:
    starting_cash: Decimal = Decimal("100000.00")
    fast_ema_period: int = 5
    slow_ema_period: int = 12
    rsi_period: int = 6
    atr_period: int = 6
    breakout_lookback: int = 8
    risk_per_trade_pct: Decimal = Decimal("0.01")
    max_position_pct: Decimal = Decimal("0.25")
    atr_stop_multiple: Decimal = Decimal("2.0")
    take_profit_r_multiple: Decimal = Decimal("2.0")
    commission_per_order: Decimal = Decimal("1.00")
    slippage_bps: Decimal = Decimal("5")
    min_bars_before_trade: int = 12

    def __post_init__(self) -> None:
        if _money(self.starting_cash) <= ZERO:
            raise BacktestError("starting cash must be positive")
        for name in (
            "fast_ema_period", "slow_ema_period", "rsi_period",
            "atr_period", "breakout_lookback", "min_bars_before_trade",
        ):
            if int(getattr(self, name)) <= 0:
                raise BacktestError(f"{name} must be positive")
        if self.fast_ema_period >= self.slow_ema_period:
            raise BacktestError("fast EMA period must be below slow EMA period")
        for name in (
            "risk_per_trade_pct", "max_position_pct",
            "atr_stop_multiple", "take_profit_r_multiple",
        ):
            if _d(getattr(self, name)) <= ZERO:
                raise BacktestError(f"{name} must be positive")
        if _d(self.risk_per_trade_pct) > Decimal("1") or _d(self.max_position_pct) > Decimal("1"):
            raise BacktestError("percentage policy values cannot exceed 1")
        if _d(self.commission_per_order) < ZERO or _d(self.slippage_bps) < ZERO:
            raise BacktestError("fees cannot be negative")


@dataclass(frozen=True)
class Trade:
    entry_index: int
    exit_index: int
    entry_time: str
    exit_time: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    return_pct: Decimal
    exit_reason: str


@dataclass(frozen=True)
class EquityPoint:
    index: int
    timestamp: str
    cash: Decimal
    position_value: Decimal
    equity: Decimal
    drawdown_pct: Decimal


@dataclass(frozen=True)
class BacktestResult:
    version: str
    symbol: str
    starting_cash: Decimal
    ending_equity: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    trades: tuple[Trade, ...]
    equity_curve: tuple[EquityPoint, ...]
    result_hash: str


def _bar_payload(bar: Bar) -> dict[str, str]:
    return {
        "timestamp": bar.timestamp,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
    }


def _trade_payload(trade: Trade) -> dict[str, Any]:
    return {
        "entry_index": trade.entry_index,
        "exit_index": trade.exit_index,
        "entry_time": trade.entry_time,
        "exit_time": trade.exit_time,
        "quantity": str(trade.quantity),
        "entry_price": str(trade.entry_price),
        "exit_price": str(trade.exit_price),
        "gross_pnl": str(trade.gross_pnl),
        "net_pnl": str(trade.net_pnl),
        "return_pct": str(trade.return_pct),
        "exit_reason": trade.exit_reason,
    }


def _equity_payload(point: EquityPoint) -> dict[str, Any]:
    return {
        "index": point.index,
        "timestamp": point.timestamp,
        "cash": str(point.cash),
        "position_value": str(point.position_value),
        "equity": str(point.equity),
        "drawdown_pct": str(point.drawdown_pct),
    }


def _result_payload(result: BacktestResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "symbol": result.symbol,
        "starting_cash": str(result.starting_cash),
        "ending_equity": str(result.ending_equity),
        "total_return_pct": str(result.total_return_pct),
        "max_drawdown_pct": str(result.max_drawdown_pct),
        "win_rate": str(result.win_rate),
        "profit_factor": str(result.profit_factor),
        "sharpe_ratio": str(result.sharpe_ratio),
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "trades": [_trade_payload(t) for t in result.trades],
        "equity_curve": [_equity_payload(p) for p in result.equity_curve],
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_bar(bar: Bar) -> Bar:
    o, h, l, c, v = map(_d, (bar.open, bar.high, bar.low, bar.close, bar.volume))
    if min(o, h, l, c) <= ZERO or v < ZERO:
        raise BacktestError("OHLC prices must be positive and volume cannot be negative")
    if h < max(o, l, c) or l > min(o, h, c):
        raise BacktestError("invalid OHLC range")
    if not bar.timestamp:
        raise BacktestError("timestamp required")
    return Bar(bar.timestamp, _money(o), _money(h), _money(l), _money(c), _qty(v))


def _ema(values: list[Decimal], period: int) -> Decimal:
    if not values:
        raise BacktestError("EMA requires data")
    alpha = Decimal("2") / Decimal(period + 1)
    current = values[0]
    for value in values[1:]:
        current = value * alpha + current * (Decimal("1") - alpha)
    return _four(current)


def _rsi(values: list[Decimal], period: int) -> Decimal:
    if len(values) < 2:
        return Decimal("50.0000")
    relevant = values[-(period + 1):]
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for left, right in zip(relevant, relevant[1:]):
        change = right - left
        gains.append(max(change, ZERO))
        losses.append(max(-change, ZERO))
    avg_gain = sum(gains, ZERO) / Decimal(len(gains))
    avg_loss = sum(losses, ZERO) / Decimal(len(losses))
    if avg_loss == ZERO:
        return Decimal("100.0000") if avg_gain > ZERO else Decimal("50.0000")
    rs = avg_gain / avg_loss
    return _four(Decimal("100") - Decimal("100") / (Decimal("1") + rs))


def _atr(bars: list[Bar], period: int) -> Decimal:
    if not bars:
        raise BacktestError("ATR requires data")
    trs: list[Decimal] = []
    for index, bar in enumerate(bars):
        if index == 0:
            tr = bar.high - bar.low
        else:
            previous_close = bars[index - 1].close
            tr = max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            )
        trs.append(tr)
    relevant = trs[-period:]
    return _four(sum(relevant, ZERO) / Decimal(len(relevant)))


def _fill_price(price: Decimal, side: str, slippage_bps: Decimal) -> Decimal:
    delta = slippage_bps / Decimal("10000")
    factor = Decimal("1") + delta if side == "BUY" else Decimal("1") - delta
    return _money(price * factor)


def _position_size(
    equity: Decimal,
    cash: Decimal,
    entry: Decimal,
    stop: Decimal,
    policy: BacktestPolicy,
) -> Decimal:
    risk_per_share = entry - stop
    if risk_per_share <= ZERO:
        return ZERO
    risk_budget = equity * _d(policy.risk_per_trade_pct)
    risk_qty = risk_budget / risk_per_share
    position_cap = equity * _d(policy.max_position_pct)
    cap_qty = position_cap / entry
    cash_qty = max(cash - _money(policy.commission_per_order), ZERO) / entry
    return _qty(min(risk_qty, cap_qty, cash_qty))


def _signal(
    bars: list[Bar],
    policy: BacktestPolicy,
) -> str:
    closes = [b.close for b in bars]
    fast = _ema(closes[-policy.slow_ema_period:], policy.fast_ema_period)
    slow = _ema(closes[-policy.slow_ema_period:], policy.slow_ema_period)
    rsi = _rsi(closes, policy.rsi_period)
    lookback = bars[-policy.breakout_lookback:]
    prior = lookback[:-1] if len(lookback) > 1 else lookback
    prior_high = max(b.high for b in prior)
    prior_low = min(b.low for b in prior)
    close = bars[-1].close

    bullish = fast > slow and rsi >= Decimal("50") and close >= prior_high
    bearish = fast < slow and rsi <= Decimal("50")
    breakdown = close <= prior_low

    if bullish:
        return "BUY"
    if bearish or breakdown:
        return "SELL"
    return "HOLD"


def run_backtest(
    symbol: str,
    bars: Iterable[Bar],
    policy: BacktestPolicy | None = None,
) -> BacktestResult:
    selected = policy or BacktestPolicy()
    sym = _symbol(symbol)
    normalized = [_normalize_bar(bar) for bar in bars]
    if len(normalized) < selected.min_bars_before_trade + 2:
        raise BacktestError("insufficient bars for backtest")
    timestamps = [bar.timestamp for bar in normalized]
    if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
        raise BacktestError("timestamps must be unique and increasing")

    cash = _money(selected.starting_cash)
    quantity = ZERO
    entry_price = ZERO
    entry_index = -1
    entry_time = ""
    stop_price = ZERO
    take_profit = ZERO
    peak_equity = cash
    trades: list[Trade] = []
    curve: list[EquityPoint] = []
    daily_returns: list[float] = []
    prior_equity = cash

    for index, bar in enumerate(normalized):
        history = normalized[: index + 1]
        position_value = _money(quantity * bar.close)
        equity = _money(cash + position_value)

        exit_reason = ""
        exit_raw = ZERO
        if quantity > ZERO:
            if bar.low <= stop_price:
                exit_reason = "STOP_LOSS"
                exit_raw = stop_price
            elif bar.high >= take_profit:
                exit_reason = "TAKE_PROFIT"
                exit_raw = take_profit
            elif index >= selected.min_bars_before_trade and _signal(history, selected) == "SELL":
                exit_reason = "STRATEGY_EXIT"
                exit_raw = bar.close

        if quantity > ZERO and exit_reason:
            exit_price = _fill_price(exit_raw, "SELL", _d(selected.slippage_bps))
            commission = _money(selected.commission_per_order)
            proceeds = _money(quantity * exit_price - commission)
            cash = _money(cash + proceeds)
            gross = _money((exit_price - entry_price) * quantity)
            net = _money(gross - commission - _money(selected.commission_per_order))
            ret = _four(net / max(entry_price * quantity, Decimal("0.01")) * Decimal("100"))
            trades.append(Trade(
                entry_index, index, entry_time, bar.timestamp, quantity,
                entry_price, exit_price, gross, net, ret, exit_reason
            ))
            quantity = ZERO
            entry_price = ZERO
            stop_price = ZERO
            take_profit = ZERO
            position_value = ZERO
            equity = cash

        if (
            quantity == ZERO
            and index >= selected.min_bars_before_trade
            and _signal(history, selected) == "BUY"
        ):
            atr = _atr(history, selected.atr_period)
            raw_entry = bar.close
            fill = _fill_price(raw_entry, "BUY", _d(selected.slippage_bps))
            stop = _money(fill - atr * _d(selected.atr_stop_multiple))
            qty = _position_size(equity, cash, fill, stop, selected)
            if qty > ZERO:
                commission = _money(selected.commission_per_order)
                cost = _money(qty * fill + commission)
                if cost <= cash:
                    cash = _money(cash - cost)
                    quantity = qty
                    entry_price = fill
                    entry_index = index
                    entry_time = bar.timestamp
                    stop_price = stop
                    take_profit = _money(
                        fill + (fill - stop) * _d(selected.take_profit_r_multiple)
                    )
                    position_value = _money(quantity * bar.close)
                    equity = _money(cash + position_value)

        peak_equity = max(peak_equity, equity)
        drawdown = (
            _four((equity - peak_equity) / peak_equity * Decimal("100"))
            if peak_equity > ZERO else ZERO
        )
        curve.append(EquityPoint(index, bar.timestamp, cash, position_value, equity, drawdown))
        if index > 0 and prior_equity > ZERO:
            daily_returns.append(float((equity - prior_equity) / prior_equity))
        prior_equity = equity

    if quantity > ZERO:
        last = normalized[-1]
        exit_price = _fill_price(last.close, "SELL", _d(selected.slippage_bps))
        commission = _money(selected.commission_per_order)
        proceeds = _money(quantity * exit_price - commission)
        cash = _money(cash + proceeds)
        gross = _money((exit_price - entry_price) * quantity)
        net = _money(gross - commission - _money(selected.commission_per_order))
        ret = _four(net / max(entry_price * quantity, Decimal("0.01")) * Decimal("100"))
        trades.append(Trade(
            entry_index, len(normalized) - 1, entry_time, last.timestamp, quantity,
            entry_price, exit_price, gross, net, ret, "END_OF_DATA"
        ))
        quantity = ZERO
        last_point = curve[-1]
        peak_equity = max(peak_equity, cash)
        drawdown = _four((cash - peak_equity) / peak_equity * Decimal("100"))
        curve[-1] = EquityPoint(
            last_point.index, last_point.timestamp, cash, ZERO, cash, drawdown
        )

    ending_equity = curve[-1].equity
    total_return = _four(
        (ending_equity - _money(selected.starting_cash))
        / _money(selected.starting_cash)
        * Decimal("100")
    )
    max_drawdown = min((p.drawdown_pct for p in curve), default=ZERO)
    wins = [t for t in trades if t.net_pnl > ZERO]
    losses = [t for t in trades if t.net_pnl < ZERO]
    win_rate = _four(Decimal(len(wins)) / Decimal(len(trades)) * Decimal("100")) if trades else ZERO
    gross_profit = sum((t.net_pnl for t in wins), ZERO)
    gross_loss = abs(sum((t.net_pnl for t in losses), ZERO))
    if gross_loss > ZERO:
        profit_factor = _four(gross_profit / gross_loss)
    elif gross_profit > ZERO:
        profit_factor = Decimal("999.0000")
    else:
        profit_factor = ZERO

    if len(daily_returns) > 1 and pstdev(daily_returns) > 0:
        sharpe = mean(daily_returns) / pstdev(daily_returns) * sqrt(252)
        sharpe_ratio = _four(str(sharpe))
    else:
        sharpe_ratio = ZERO

    result = BacktestResult(
        version=VERSION,
        symbol=sym,
        starting_cash=_money(selected.starting_cash),
        ending_equity=ending_equity,
        total_return_pct=total_return,
        max_drawdown_pct=max_drawdown,
        win_rate=win_rate,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe_ratio,
        total_trades=len(trades),
        winning_trades=len(wins),
        losing_trades=len(losses),
        trades=tuple(trades),
        equity_curve=tuple(curve),
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: BacktestResult) -> bool:
    if result.version != VERSION:
        raise BacktestError("unsupported result version")
    if result.total_trades != len(result.trades):
        raise BacktestError("trade count mismatch")
    if result.winning_trades + result.losing_trades > result.total_trades:
        raise BacktestError("invalid win/loss counts")
    if not result.equity_curve:
        raise BacktestError("equity curve cannot be empty")
    if result.ending_equity != result.equity_curve[-1].equity:
        raise BacktestError("ending equity mismatch")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise BacktestError("result hash mismatch")
    return True


def save_result(result: BacktestResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> BacktestResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    trades = tuple(Trade(
        int(t["entry_index"]), int(t["exit_index"]), t["entry_time"], t["exit_time"],
        _d(t["quantity"]), _d(t["entry_price"]), _d(t["exit_price"]),
        _d(t["gross_pnl"]), _d(t["net_pnl"]), _d(t["return_pct"]), t["exit_reason"]
    ) for t in payload["trades"])
    curve = tuple(EquityPoint(
        int(p["index"]), p["timestamp"], _d(p["cash"]), _d(p["position_value"]),
        _d(p["equity"]), _d(p["drawdown_pct"])
    ) for p in payload["equity_curve"])
    result = BacktestResult(
        payload["version"], payload["symbol"], _d(payload["starting_cash"]),
        _d(payload["ending_equity"]), _d(payload["total_return_pct"]),
        _d(payload["max_drawdown_pct"]), _d(payload["win_rate"]),
        _d(payload["profit_factor"]), _d(payload["sharpe_ratio"]),
        int(payload["total_trades"]), int(payload["winning_trades"]),
        int(payload["losing_trades"]), trades, curve, payload["result_hash"]
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
