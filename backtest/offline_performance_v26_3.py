from __future__ import annotations

"""
V26.3 Offline Performance Analyzer

Calculates professional backtest metrics from an offline equity curve,
trade returns, and optional benchmark returns.

Metrics:
- total return, CAGR, annual return, annual volatility
- Sharpe, Sortino, Calmar, MAR
- profit factor, expectancy, win rate
- average win/loss, payoff ratio
- max consecutive wins/losses
- recovery factor, SQN
- alpha, beta, information ratio
- monthly and yearly return summaries
- immutable SHA-256 result hashing
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no broker/account APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import sqrt
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable
import json

VERSION = "26.3"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class PerformanceError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise PerformanceError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise PerformanceError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PerformanceError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PerformanceError("timestamp must include timezone")
    return parsed


@dataclass(frozen=True)
class EquitySample:
    timestamp: str
    equity: Decimal


@dataclass(frozen=True)
class TradeSample:
    return_pct: Decimal
    net_pnl: Decimal
    holding_period_bars: int


@dataclass(frozen=True)
class PeriodReturn:
    period: str
    return_pct: Decimal


@dataclass(frozen=True)
class PerformanceResult:
    version: str
    total_return_pct: Decimal
    cagr_pct: Decimal
    annual_return_pct: Decimal
    annual_volatility_pct: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown_pct: Decimal
    calmar_ratio: Decimal
    mar_ratio: Decimal
    win_rate_pct: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    average_win: Decimal
    average_loss: Decimal
    payoff_ratio: Decimal
    average_holding_period: Decimal
    max_consecutive_wins: int
    max_consecutive_losses: int
    recovery_factor: Decimal
    sqn: Decimal
    alpha_pct: Decimal
    beta: Decimal
    information_ratio: Decimal
    monthly_returns: tuple[PeriodReturn, ...]
    yearly_returns: tuple[PeriodReturn, ...]
    input_hash: str
    result_hash: str


def _equity_payload(item: EquitySample) -> dict[str, str]:
    return {"timestamp": item.timestamp, "equity": str(item.equity)}


def _trade_payload(item: TradeSample) -> dict[str, str]:
    return {
        "return_pct": str(item.return_pct),
        "net_pnl": str(item.net_pnl),
        "holding_period_bars": str(item.holding_period_bars),
    }


def _period_payload(item: PeriodReturn) -> dict[str, str]:
    return {"period": item.period, "return_pct": str(item.return_pct)}


def _result_payload(result: PerformanceResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "total_return_pct": str(result.total_return_pct),
        "cagr_pct": str(result.cagr_pct),
        "annual_return_pct": str(result.annual_return_pct),
        "annual_volatility_pct": str(result.annual_volatility_pct),
        "sharpe_ratio": str(result.sharpe_ratio),
        "sortino_ratio": str(result.sortino_ratio),
        "max_drawdown_pct": str(result.max_drawdown_pct),
        "calmar_ratio": str(result.calmar_ratio),
        "mar_ratio": str(result.mar_ratio),
        "win_rate_pct": str(result.win_rate_pct),
        "profit_factor": str(result.profit_factor),
        "expectancy": str(result.expectancy),
        "average_win": str(result.average_win),
        "average_loss": str(result.average_loss),
        "payoff_ratio": str(result.payoff_ratio),
        "average_holding_period": str(result.average_holding_period),
        "max_consecutive_wins": result.max_consecutive_wins,
        "max_consecutive_losses": result.max_consecutive_losses,
        "recovery_factor": str(result.recovery_factor),
        "sqn": str(result.sqn),
        "alpha_pct": str(result.alpha_pct),
        "beta": str(result.beta),
        "information_ratio": str(result.information_ratio),
        "monthly_returns": [_period_payload(x) for x in result.monthly_returns],
        "yearly_returns": [_period_payload(x) for x in result.yearly_returns],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_equity(items: Iterable[EquitySample]) -> tuple[EquitySample, ...]:
    normalized = []
    for item in items:
        equity = _d(item.equity)
        if equity <= ZERO:
            raise PerformanceError("equity must be positive")
        parsed = _timestamp(item.timestamp)
        normalized.append(EquitySample(parsed.isoformat(), _q(equity)))
    normalized.sort(key=lambda x: x.timestamp)
    if len(normalized) < 2:
        raise PerformanceError("at least two equity samples are required")
    times = [x.timestamp for x in normalized]
    if len(times) != len(set(times)):
        raise PerformanceError("duplicate equity timestamps detected")
    return tuple(normalized)


def _normalize_trades(items: Iterable[TradeSample]) -> tuple[TradeSample, ...]:
    normalized = []
    for item in items:
        if item.holding_period_bars < 0:
            raise PerformanceError("holding_period_bars cannot be negative")
        normalized.append(TradeSample(
            return_pct=_q(item.return_pct),
            net_pnl=_q(item.net_pnl),
            holding_period_bars=int(item.holding_period_bars),
        ))
    return tuple(normalized)


def _returns(equity: tuple[EquitySample, ...]) -> list[float]:
    result = []
    for left, right in zip(equity, equity[1:]):
        result.append(float((right.equity - left.equity) / left.equity))
    return result


def _drawdown(equity: tuple[EquitySample, ...]) -> Decimal:
    peak = equity[0].equity
    worst = ZERO
    for item in equity:
        peak = max(peak, item.equity)
        dd = (item.equity - peak) / peak * Decimal("100")
        worst = min(worst, dd)
    return _q(worst)


def _period_returns(equity: tuple[EquitySample, ...], yearly: bool) -> tuple[PeriodReturn, ...]:
    grouped: dict[str, list[EquitySample]] = {}
    for item in equity:
        parsed = _timestamp(item.timestamp)
        key = f"{parsed.year:04d}" if yearly else f"{parsed.year:04d}-{parsed.month:02d}"
        grouped.setdefault(key, []).append(item)
    output = []
    for key in sorted(grouped):
        values = grouped[key]
        if len(values) < 2:
            ret = ZERO
        else:
            ret = (values[-1].equity - values[0].equity) / values[0].equity * Decimal("100")
        output.append(PeriodReturn(key, _q(ret)))
    return tuple(output)


def _consecutive(trades: tuple[TradeSample, ...]) -> tuple[int, int]:
    max_wins = max_losses = current_wins = current_losses = 0
    for trade in trades:
        if trade.net_pnl > ZERO:
            current_wins += 1
            current_losses = 0
        elif trade.net_pnl < ZERO:
            current_losses += 1
            current_wins = 0
        else:
            current_wins = current_losses = 0
        max_wins = max(max_wins, current_wins)
        max_losses = max(max_losses, current_losses)
    return max_wins, max_losses


def analyze_performance(
    equity_curve: Iterable[EquitySample],
    trades: Iterable[TradeSample],
    benchmark_returns: Iterable[Any] | None = None,
    *,
    periods_per_year: int = 252,
    risk_free_rate_pct: Any = 0,
) -> PerformanceResult:
    if periods_per_year <= 0:
        raise PerformanceError("periods_per_year must be positive")

    equity = _normalize_equity(equity_curve)
    trade_data = _normalize_trades(trades)
    returns = _returns(equity)
    benchmark = [] if benchmark_returns is None else [float(_d(x)) for x in benchmark_returns]
    if benchmark and len(benchmark) != len(returns):
        raise PerformanceError("benchmark return count must match equity return count")

    start = equity[0].equity
    end = equity[-1].equity
    total_return = (end - start) / start * Decimal("100")

    start_time = _timestamp(equity[0].timestamp)
    end_time = _timestamp(equity[-1].timestamp)
    years = max((end_time - start_time).total_seconds() / (365.25 * 24 * 3600), 1 / periods_per_year)
    cagr = (float(end / start) ** (1 / years) - 1) * 100

    avg_return = mean(returns) if returns else 0.0
    volatility = pstdev(returns) if len(returns) > 1 else 0.0
    annual_return = avg_return * periods_per_year * 100
    annual_volatility = volatility * sqrt(periods_per_year) * 100
    rf_period = float(_d(risk_free_rate_pct)) / 100 / periods_per_year
    excess = [r - rf_period for r in returns]
    sharpe = (mean(excess) / pstdev(excess) * sqrt(periods_per_year)) if len(excess) > 1 and pstdev(excess) > 0 else 0.0

    downside = [min(r - rf_period, 0.0) for r in returns]
    downside_dev = sqrt(mean([x * x for x in downside])) if downside else 0.0
    sortino = (mean(excess) / downside_dev * sqrt(periods_per_year)) if downside_dev > 0 else 0.0

    max_dd = _drawdown(equity)
    calmar = cagr / abs(float(max_dd)) if max_dd < ZERO else 0.0
    mar = calmar

    wins = [t for t in trade_data if t.net_pnl > ZERO]
    losses = [t for t in trade_data if t.net_pnl < ZERO]
    win_rate = (len(wins) / len(trade_data) * 100) if trade_data else 0.0
    gross_profit = sum((t.net_pnl for t in wins), ZERO)
    gross_loss = abs(sum((t.net_pnl for t in losses), ZERO))
    profit_factor = float(gross_profit / gross_loss) if gross_loss > ZERO else (999.0 if gross_profit > ZERO else 0.0)
    expectancy = float(sum((t.net_pnl for t in trade_data), ZERO) / Decimal(len(trade_data))) if trade_data else 0.0
    average_win = float(gross_profit / Decimal(len(wins))) if wins else 0.0
    average_loss = float(gross_loss / Decimal(len(losses))) if losses else 0.0
    payoff = average_win / average_loss if average_loss > 0 else (999.0 if average_win > 0 else 0.0)
    avg_holding = mean([t.holding_period_bars for t in trade_data]) if trade_data else 0.0
    max_wins, max_losses = _consecutive(trade_data)

    net_profit = end - start
    recovery = float(net_profit / (start * abs(max_dd) / Decimal("100"))) if max_dd < ZERO else 0.0

    trade_returns = [float(t.return_pct) for t in trade_data]
    sqn = (
        mean(trade_returns) / pstdev(trade_returns) * sqrt(len(trade_returns))
        if len(trade_returns) > 1 and pstdev(trade_returns) > 0 else 0.0
    )

    alpha = beta = info_ratio = 0.0
    if benchmark:
        bench_mean = mean(benchmark)
        bench_var = mean([(x - bench_mean) ** 2 for x in benchmark])
        if bench_var > 0:
            covariance = mean([
                (r - mean(returns)) * (b - bench_mean)
                for r, b in zip(returns, benchmark)
            ])
            beta = covariance / bench_var
        alpha = (mean(returns) - beta * bench_mean) * periods_per_year * 100
        active = [r - b for r, b in zip(returns, benchmark)]
        active_dev = pstdev(active)
        info_ratio = mean(active) / active_dev * sqrt(periods_per_year) if active_dev > 0 else 0.0

    monthly = _period_returns(equity, yearly=False)
    yearly = _period_returns(equity, yearly=True)

    input_hash = _hash({
        "equity": [_equity_payload(x) for x in equity],
        "trades": [_trade_payload(x) for x in trade_data],
        "benchmark": [str(x) for x in benchmark],
        "periods_per_year": periods_per_year,
        "risk_free_rate_pct": str(_d(risk_free_rate_pct)),
    })

    result = PerformanceResult(
        version=VERSION,
        total_return_pct=_q(total_return),
        cagr_pct=_q(cagr),
        annual_return_pct=_q(annual_return),
        annual_volatility_pct=_q(annual_volatility),
        sharpe_ratio=_q(sharpe),
        sortino_ratio=_q(sortino),
        max_drawdown_pct=max_dd,
        calmar_ratio=_q(calmar),
        mar_ratio=_q(mar),
        win_rate_pct=_q(win_rate),
        profit_factor=_q(profit_factor),
        expectancy=_q(expectancy),
        average_win=_q(average_win),
        average_loss=_q(average_loss),
        payoff_ratio=_q(payoff),
        average_holding_period=_q(avg_holding),
        max_consecutive_wins=max_wins,
        max_consecutive_losses=max_losses,
        recovery_factor=_q(recovery),
        sqn=_q(sqn),
        alpha_pct=_q(alpha),
        beta=_q(beta),
        information_ratio=_q(info_ratio),
        monthly_returns=monthly,
        yearly_returns=yearly,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: PerformanceResult) -> bool:
    if result.version != VERSION:
        raise PerformanceError("unsupported result version")
    if result.win_rate_pct < ZERO or result.win_rate_pct > Decimal("100"):
        raise PerformanceError("win rate out of range")
    if result.max_drawdown_pct > ZERO:
        raise PerformanceError("max drawdown cannot be positive")
    if result.max_consecutive_wins < 0 or result.max_consecutive_losses < 0:
        raise PerformanceError("consecutive counts cannot be negative")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise PerformanceError("result hash mismatch")
    return True


def save_result(result: PerformanceResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> PerformanceResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    monthly = tuple(PeriodReturn(x["period"], _d(x["return_pct"])) for x in payload["monthly_returns"])
    yearly = tuple(PeriodReturn(x["period"], _d(x["return_pct"])) for x in payload["yearly_returns"])
    result = PerformanceResult(
        version=payload["version"],
        total_return_pct=_d(payload["total_return_pct"]),
        cagr_pct=_d(payload["cagr_pct"]),
        annual_return_pct=_d(payload["annual_return_pct"]),
        annual_volatility_pct=_d(payload["annual_volatility_pct"]),
        sharpe_ratio=_d(payload["sharpe_ratio"]),
        sortino_ratio=_d(payload["sortino_ratio"]),
        max_drawdown_pct=_d(payload["max_drawdown_pct"]),
        calmar_ratio=_d(payload["calmar_ratio"]),
        mar_ratio=_d(payload["mar_ratio"]),
        win_rate_pct=_d(payload["win_rate_pct"]),
        profit_factor=_d(payload["profit_factor"]),
        expectancy=_d(payload["expectancy"]),
        average_win=_d(payload["average_win"]),
        average_loss=_d(payload["average_loss"]),
        payoff_ratio=_d(payload["payoff_ratio"]),
        average_holding_period=_d(payload["average_holding_period"]),
        max_consecutive_wins=int(payload["max_consecutive_wins"]),
        max_consecutive_losses=int(payload["max_consecutive_losses"]),
        recovery_factor=_d(payload["recovery_factor"]),
        sqn=_d(payload["sqn"]),
        alpha_pct=_d(payload["alpha_pct"]),
        beta=_d(payload["beta"]),
        information_ratio=_d(payload["information_ratio"]),
        monthly_returns=monthly,
        yearly_returns=yearly,
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
