from __future__ import annotations

"""
V29.0 Professional Backtesting Engine

Features:
- multi-symbol portfolio backtesting
- BUY / SELL / HOLD signal execution
- position sizing by target portfolio fraction
- slippage and commission
- realized and unrealized PnL
- cash and equity tracking
- equity curve
- trade log
- win rate
- profit factor
- expectancy
- CAGR
- Sharpe ratio
- maximum drawdown
- exposure ratio
- deterministic output
- SHA-256 integrity verification
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no real orders
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import sqrt
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "29.0"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class BacktestError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise BacktestError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise BacktestError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise BacktestError(f"{field_name} must be a SHA-256 hex digest")
    return digest


@dataclass(frozen=True)
class BacktestPolicy:
    initial_cash: Decimal = Decimal("100000")
    slippage_bps: Decimal = Decimal("5")
    commission_per_share: Decimal = Decimal("0.005")
    minimum_commission: Decimal = Decimal("1.00")
    annualization_factor: int = 252
    allow_fractional_shares: bool = False

    def __post_init__(self) -> None:
        if _d(self.initial_cash) <= ZERO:
            raise BacktestError("initial_cash must be positive")
        if _d(self.slippage_bps) < ZERO:
            raise BacktestError("slippage_bps cannot be negative")
        if _d(self.commission_per_share) < ZERO:
            raise BacktestError("commission_per_share cannot be negative")
        if _d(self.minimum_commission) < ZERO:
            raise BacktestError("minimum_commission cannot be negative")
        if self.annualization_factor <= 0:
            raise BacktestError("annualization_factor must be positive")


@dataclass(frozen=True)
class BacktestBar:
    timestamp: str
    symbol: str
    close: Decimal
    signal: int
    target_fraction: Decimal
    strategy_hash: str


@dataclass(frozen=True)
class Trade:
    trade_id: str
    timestamp: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    notional: Decimal
    commission: Decimal
    realized_pnl: Decimal
    trade_hash: str


@dataclass(frozen=True)
class EquityPoint:
    timestamp: str
    cash: Decimal
    market_value: Decimal
    equity: Decimal
    exposure: Decimal
    point_hash: str


@dataclass(frozen=True)
class BacktestMetrics:
    total_return_pct: Decimal
    cagr_pct: Decimal
    sharpe_ratio: Decimal
    max_drawdown_pct: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    exposure_ratio: Decimal
    total_trades: int


@dataclass(frozen=True)
class BacktestResult:
    version: str
    backtest_id: str
    policy: BacktestPolicy
    trades: tuple[Trade, ...]
    equity_curve: tuple[EquityPoint, ...]
    metrics: BacktestMetrics
    input_hash: str
    result_hash: str


def _trade_payload(trade: Trade, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "trade_id": trade.trade_id,
        "timestamp": trade.timestamp,
        "symbol": trade.symbol,
        "side": trade.side,
        "quantity": str(trade.quantity),
        "price": str(trade.price),
        "notional": str(trade.notional),
        "commission": str(trade.commission),
        "realized_pnl": str(trade.realized_pnl),
    }
    if include_hash:
        payload["trade_hash"] = trade.trade_hash
    return payload


def _point_payload(point: EquityPoint, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "timestamp": point.timestamp,
        "cash": str(point.cash),
        "market_value": str(point.market_value),
        "equity": str(point.equity),
        "exposure": str(point.exposure),
    }
    if include_hash:
        payload["point_hash"] = point.point_hash
    return payload


def _metrics_payload(metrics: BacktestMetrics) -> dict[str, Any]:
    return {
        "total_return_pct": str(metrics.total_return_pct),
        "cagr_pct": str(metrics.cagr_pct),
        "sharpe_ratio": str(metrics.sharpe_ratio),
        "max_drawdown_pct": str(metrics.max_drawdown_pct),
        "win_rate": str(metrics.win_rate),
        "profit_factor": str(metrics.profit_factor),
        "expectancy": str(metrics.expectancy),
        "exposure_ratio": str(metrics.exposure_ratio),
        "total_trades": metrics.total_trades,
    }


def _policy_payload(policy: BacktestPolicy) -> dict[str, Any]:
    return {
        "initial_cash": str(policy.initial_cash),
        "slippage_bps": str(policy.slippage_bps),
        "commission_per_share": str(policy.commission_per_share),
        "minimum_commission": str(policy.minimum_commission),
        "annualization_factor": policy.annualization_factor,
        "allow_fractional_shares": policy.allow_fractional_shares,
    }


def _result_payload(result: BacktestResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "backtest_id": result.backtest_id,
        "policy": _policy_payload(result.policy),
        "trades": [_trade_payload(item, include_hash=True) for item in result.trades],
        "equity_curve": [_point_payload(item, include_hash=True) for item in result.equity_curve],
        "metrics": _metrics_payload(result.metrics),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _commission(quantity: Decimal, policy: BacktestPolicy) -> Decimal:
    return _q(max(
        _d(policy.minimum_commission),
        abs(quantity) * _d(policy.commission_per_share),
    ))


def _slipped_price(close: Decimal, side: str, policy: BacktestPolicy) -> Decimal:
    rate = _d(policy.slippage_bps) / Decimal("10000")
    if side == "BUY":
        return _q(close * (ONE + rate))
    return _q(close * (ONE - rate))


def _make_trade(
    timestamp: str,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    realized_pnl: Decimal,
) -> Trade:
    notional = _q(abs(quantity) * price)
    seed = _hash({
        "timestamp": timestamp,
        "symbol": symbol,
        "side": side,
        "quantity": str(quantity),
        "price": str(price),
        "realized_pnl": str(realized_pnl),
    })
    trade = Trade(
        trade_id=f"TRADE-{seed[:16].upper()}",
        timestamp=timestamp,
        symbol=symbol,
        side=side,
        quantity=_q(quantity),
        price=_q(price),
        notional=notional,
        commission=ZERO,
        realized_pnl=_q(realized_pnl),
        trade_hash="",
    )
    return trade


def run_backtest(
    bars: Iterable[BacktestBar],
    policy: BacktestPolicy | None = None,
) -> BacktestResult:
    selected = policy or BacktestPolicy()
    data = tuple(bars)
    if not data:
        raise BacktestError("at least one bar is required")

    normalized = []
    seen = set()
    for item in data:
        timestamp = item.timestamp.strip()
        symbol = item.symbol.strip().upper()
        if not timestamp or not symbol:
            raise BacktestError("timestamp and symbol are required")
        key = (timestamp, symbol)
        if key in seen:
            raise BacktestError("duplicate timestamp/symbol bar detected")
        seen.add(key)
        close = _q(item.close)
        target = _q(item.target_fraction)
        if close <= ZERO:
            raise BacktestError("close price must be positive")
        if target < ZERO or target > ONE:
            raise BacktestError("target_fraction must be between 0 and 1")
        if item.signal not in {-1, 0, 1}:
            raise BacktestError("signal must be -1, 0, or 1")
        _validate_sha256(item.strategy_hash, "strategy_hash")
        normalized.append(BacktestBar(timestamp, symbol, close, int(item.signal), target, item.strategy_hash))

    ordered = tuple(sorted(normalized, key=lambda row: (row.timestamp, row.symbol)))

    cash = _q(selected.initial_cash)
    positions: dict[str, Decimal] = {}
    cost_basis: dict[str, Decimal] = {}
    last_prices: dict[str, Decimal] = {}
    trades: list[Trade] = []
    equity_curve: list[EquityPoint] = []

    timestamps = sorted({row.timestamp for row in ordered})

    for timestamp in timestamps:
        rows = [row for row in ordered if row.timestamp == timestamp]

        for row in rows:
            last_prices[row.symbol] = row.close

        current_market_value = sum(
            positions.get(symbol, ZERO) * last_prices.get(symbol, ZERO)
            for symbol in positions
        )
        current_equity = cash + current_market_value

        for row in rows:
            current_qty = positions.get(row.symbol, ZERO)
            target_value = current_equity * row.target_fraction

            if row.signal == 1:
                desired_qty = target_value / row.close
                if not selected.allow_fractional_shares:
                    desired_qty = Decimal(int(desired_qty))
            elif row.signal == -1:
                desired_qty = -target_value / row.close
                if not selected.allow_fractional_shares:
                    desired_qty = Decimal(int(desired_qty))
            else:
                desired_qty = current_qty

            delta = desired_qty - current_qty
            if delta == ZERO:
                continue

            side = "BUY" if delta > ZERO else "SELL"
            execution_price = _slipped_price(row.close, side, selected)
            commission = _commission(delta, selected)
            realized_pnl = ZERO

            if side == "BUY":
                required = abs(delta) * execution_price + commission
                if required > cash:
                    affordable = (cash - commission) / execution_price
                    if affordable <= ZERO:
                        continue
                    if not selected.allow_fractional_shares:
                        affordable = Decimal(int(affordable))
                    delta = min(delta, affordable)
                    if delta <= ZERO:
                        continue
                    required = delta * execution_price + commission
                cash -= required

                if current_qty >= ZERO:
                    new_qty = current_qty + delta
                    previous_cost = current_qty * cost_basis.get(row.symbol, ZERO)
                    new_cost = previous_cost + delta * execution_price
                    cost_basis[row.symbol] = ZERO if new_qty == ZERO else _q(new_cost / new_qty)
                else:
                    closing = min(delta, abs(current_qty))
                    realized_pnl = _q((cost_basis.get(row.symbol, execution_price) - execution_price) * closing - commission)
                    new_qty = current_qty + delta
                    if new_qty > ZERO:
                        cost_basis[row.symbol] = execution_price
                positions[row.symbol] = _q(current_qty + delta)

            else:
                proceeds = abs(delta) * execution_price - commission
                cash += proceeds

                if current_qty > ZERO:
                    closing = min(abs(delta), current_qty)
                    realized_pnl = _q((execution_price - cost_basis.get(row.symbol, execution_price)) * closing - commission)
                    new_qty = current_qty + delta
                    if new_qty < ZERO:
                        cost_basis[row.symbol] = execution_price
                else:
                    new_qty = current_qty + delta
                    previous_abs = abs(current_qty)
                    new_abs = abs(new_qty)
                    previous_cost = previous_abs * cost_basis.get(row.symbol, ZERO)
                    new_cost = previous_cost + abs(delta) * execution_price
                    cost_basis[row.symbol] = ZERO if new_abs == ZERO else _q(new_cost / new_abs)
                positions[row.symbol] = _q(current_qty + delta)

            trade = _make_trade(
                timestamp,
                row.symbol,
                side,
                delta,
                execution_price,
                realized_pnl,
            )
            trade = replace(
                trade,
                commission=commission,
                trade_hash="",
            )
            trade = replace(trade, trade_hash=_hash(_trade_payload(trade)))
            trades.append(trade)

        market_value = _q(sum(
            qty * last_prices.get(symbol, ZERO)
            for symbol, qty in positions.items()
        ))
        equity = _q(cash + market_value)
        exposure = ZERO if equity == ZERO else _q(
            sum(
                abs(qty * last_prices.get(symbol, ZERO))
                for symbol, qty in positions.items()
            ) / equity
        )
        point = EquityPoint(
            timestamp=timestamp,
            cash=_q(cash),
            market_value=market_value,
            equity=equity,
            exposure=exposure,
            point_hash="",
        )
        point = replace(point, point_hash=_hash(_point_payload(point)))
        equity_curve.append(point)

    metrics = _calculate_metrics(
        tuple(trades),
        tuple(equity_curve),
        selected,
    )

    input_hash = _hash({
        "bars": [
            {
                "timestamp": row.timestamp,
                "symbol": row.symbol,
                "close": str(row.close),
                "signal": row.signal,
                "target_fraction": str(row.target_fraction),
                "strategy_hash": row.strategy_hash,
            }
            for row in ordered
        ],
        "policy": _policy_payload(selected),
    })

    result = BacktestResult(
        version=VERSION,
        backtest_id=f"BT-{input_hash[:16].upper()}",
        policy=selected,
        trades=tuple(trades),
        equity_curve=tuple(equity_curve),
        metrics=metrics,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def _calculate_metrics(
    trades: tuple[Trade, ...],
    curve: tuple[EquityPoint, ...],
    policy: BacktestPolicy,
) -> BacktestMetrics:
    start = _d(policy.initial_cash)
    end = curve[-1].equity
    total_return = ZERO if start == ZERO else (end / start - ONE) * Decimal("100")

    periods = max(1, len(curve) - 1)
    years = Decimal(periods) / Decimal(policy.annualization_factor)
    if end > ZERO and start > ZERO and years > ZERO:
        cagr = (_d(float(end / start) ** (1 / float(years))) - ONE) * Decimal("100")
    else:
        cagr = ZERO

    returns = []
    for previous, current in zip(curve, curve[1:]):
        if previous.equity != ZERO:
            returns.append((current.equity / previous.equity) - ONE)

    if len(returns) >= 2:
        avg = sum(returns, ZERO) / Decimal(len(returns))
        variance = sum((value - avg) ** 2 for value in returns) / Decimal(len(returns))
        stddev = _d(sqrt(float(variance)))
        sharpe = ZERO if stddev == ZERO else avg / stddev * _d(sqrt(policy.annualization_factor))
    else:
        sharpe = ZERO

    peak = curve[0].equity
    max_dd = ZERO
    exposure_avg = ZERO
    for point in curve:
        if point.equity > peak:
            peak = point.equity
        if peak > ZERO:
            drawdown = (point.equity / peak - ONE) * Decimal("100")
            max_dd = min(max_dd, drawdown)
        exposure_avg += point.exposure
    exposure_ratio = exposure_avg / Decimal(len(curve))

    realized = [trade.realized_pnl for trade in trades if trade.realized_pnl != ZERO]
    wins = [value for value in realized if value > ZERO]
    losses = [value for value in realized if value < ZERO]
    win_rate = ZERO if not realized else Decimal(len(wins)) / Decimal(len(realized))
    gross_profit = sum(wins, ZERO)
    gross_loss = abs(sum(losses, ZERO))
    profit_factor = (
        Decimal("999999")
        if gross_loss == ZERO and gross_profit > ZERO
        else ZERO if gross_loss == ZERO
        else gross_profit / gross_loss
    )
    expectancy = ZERO if not realized else sum(realized, ZERO) / Decimal(len(realized))

    return BacktestMetrics(
        total_return_pct=_q(total_return),
        cagr_pct=_q(cagr),
        sharpe_ratio=_q(sharpe),
        max_drawdown_pct=_q(max_dd),
        win_rate=_q(win_rate),
        profit_factor=_q(profit_factor),
        expectancy=_q(expectancy),
        exposure_ratio=_q(exposure_ratio),
        total_trades=len(trades),
    )


def verify_trade(trade: Trade) -> bool:
    if trade.side not in {"BUY", "SELL"}:
        raise BacktestError("invalid trade side")
    if trade.quantity == ZERO or trade.price <= ZERO:
        raise BacktestError("invalid trade")
    if trade.notional != _q(abs(trade.quantity) * trade.price):
        raise BacktestError("trade notional mismatch")
    clean = replace(trade, trade_hash="")
    if trade.trade_hash != _hash(_trade_payload(clean)):
        raise BacktestError("trade hash mismatch")
    return True


def verify_point(point: EquityPoint) -> bool:
    if point.equity != _q(point.cash + point.market_value):
        raise BacktestError("equity point mismatch")
    if point.exposure < ZERO:
        raise BacktestError("negative exposure")
    clean = replace(point, point_hash="")
    if point.point_hash != _hash(_point_payload(clean)):
        raise BacktestError("equity point hash mismatch")
    return True


def verify_result(result: BacktestResult) -> bool:
    if result.version != VERSION:
        raise BacktestError("unsupported backtest version")
    if not result.backtest_id.startswith("BT-"):
        raise BacktestError("invalid backtest ID")
    if not result.equity_curve:
        raise BacktestError("equity curve cannot be empty")
    for trade in result.trades:
        verify_trade(trade)
    for point in result.equity_curve:
        verify_point(point)
    if result.metrics.total_trades != len(result.trades):
        raise BacktestError("trade count mismatch")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise BacktestError("backtest result hash mismatch")
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
    policy_data = payload["policy"]
    policy = BacktestPolicy(
        initial_cash=_d(policy_data["initial_cash"]),
        slippage_bps=_d(policy_data["slippage_bps"]),
        commission_per_share=_d(policy_data["commission_per_share"]),
        minimum_commission=_d(policy_data["minimum_commission"]),
        annualization_factor=int(policy_data["annualization_factor"]),
        allow_fractional_shares=bool(policy_data["allow_fractional_shares"]),
    )

    trades = tuple(
        Trade(
            trade_id=item["trade_id"],
            timestamp=item["timestamp"],
            symbol=item["symbol"],
            side=item["side"],
            quantity=_d(item["quantity"]),
            price=_d(item["price"]),
            notional=_d(item["notional"]),
            commission=_d(item["commission"]),
            realized_pnl=_d(item["realized_pnl"]),
            trade_hash=item["trade_hash"],
        )
        for item in payload["trades"]
    )

    curve = tuple(
        EquityPoint(
            timestamp=item["timestamp"],
            cash=_d(item["cash"]),
            market_value=_d(item["market_value"]),
            equity=_d(item["equity"]),
            exposure=_d(item["exposure"]),
            point_hash=item["point_hash"],
        )
        for item in payload["equity_curve"]
    )

    metric_data = payload["metrics"]
    metrics = BacktestMetrics(
        total_return_pct=_d(metric_data["total_return_pct"]),
        cagr_pct=_d(metric_data["cagr_pct"]),
        sharpe_ratio=_d(metric_data["sharpe_ratio"]),
        max_drawdown_pct=_d(metric_data["max_drawdown_pct"]),
        win_rate=_d(metric_data["win_rate"]),
        profit_factor=_d(metric_data["profit_factor"]),
        expectancy=_d(metric_data["expectancy"]),
        exposure_ratio=_d(metric_data["exposure_ratio"]),
        total_trades=int(metric_data["total_trades"]),
    )

    result = BacktestResult(
        version=payload["version"],
        backtest_id=payload["backtest_id"],
        policy=policy,
        trades=trades,
        equity_curve=curve,
        metrics=metrics,
        input_hash=payload["input_hash"],
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
