from __future__ import annotations

"""
V26.5 Offline Trade Analytics Engine

Analyzes closed trade records from the V26.4 trade journal model.

Features:
- win/loss and LONG/SHORT classification
- symbol, strategy, exit-reason, weekday, and hour aggregation
- holding-time and P&L distributions
- consecutive win/loss streak analysis
- rolling P&L windows
- symbol contribution ranking
- deterministic filtering
- JSON persistence
- CSV export
- SHA-256 integrity verification
- tamper detection

Safety boundary:
- no network access
- no account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import csv
import json

VERSION = "26.5"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class AnalyticsError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise AnalyticsError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise AnalyticsError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnalyticsError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AnalyticsError("timestamp must include timezone")
    return parsed


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(ch.isalnum() or ch in ".-" for ch in result):
        raise AnalyticsError("invalid symbol")
    return result


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AnalyticsTrade:
    trade_id: str
    symbol: str
    direction: str
    strategy: str
    entry_time: str
    exit_time: str
    exit_reason: str
    net_pnl: Decimal
    holding_seconds: int
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroupStat:
    key: str
    trades: int
    wins: int
    losses: int
    total_pnl: Decimal
    average_pnl: Decimal
    win_rate_pct: Decimal


@dataclass(frozen=True)
class BucketStat:
    bucket: str
    trades: int
    total_pnl: Decimal


@dataclass(frozen=True)
class RollingPoint:
    end_trade_id: str
    window_trades: int
    rolling_pnl: Decimal
    rolling_win_rate_pct: Decimal


@dataclass(frozen=True)
class AnalyticsResult:
    version: str
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate_pct: Decimal
    total_pnl: Decimal
    average_pnl: Decimal
    best_trade_pnl: Decimal
    worst_trade_pnl: Decimal
    average_holding_seconds: Decimal
    max_consecutive_wins: int
    max_consecutive_losses: int
    long_stats: GroupStat
    short_stats: GroupStat
    symbol_stats: tuple[GroupStat, ...]
    strategy_stats: tuple[GroupStat, ...]
    exit_reason_stats: tuple[GroupStat, ...]
    weekday_stats: tuple[GroupStat, ...]
    hour_stats: tuple[GroupStat, ...]
    pnl_distribution: tuple[BucketStat, ...]
    holding_distribution: tuple[BucketStat, ...]
    rolling_performance: tuple[RollingPoint, ...]
    symbol_contribution: tuple[GroupStat, ...]
    input_hash: str
    result_hash: str


def _trade_payload(trade: AnalyticsTrade) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "symbol": trade.symbol,
        "direction": trade.direction,
        "strategy": trade.strategy,
        "entry_time": trade.entry_time,
        "exit_time": trade.exit_time,
        "exit_reason": trade.exit_reason,
        "net_pnl": str(trade.net_pnl),
        "holding_seconds": trade.holding_seconds,
        "tags": list(trade.tags),
    }


def _group_payload(stat: GroupStat) -> dict[str, Any]:
    return {
        "key": stat.key,
        "trades": stat.trades,
        "wins": stat.wins,
        "losses": stat.losses,
        "total_pnl": str(stat.total_pnl),
        "average_pnl": str(stat.average_pnl),
        "win_rate_pct": str(stat.win_rate_pct),
    }


def _bucket_payload(stat: BucketStat) -> dict[str, Any]:
    return {
        "bucket": stat.bucket,
        "trades": stat.trades,
        "total_pnl": str(stat.total_pnl),
    }


def _rolling_payload(point: RollingPoint) -> dict[str, Any]:
    return {
        "end_trade_id": point.end_trade_id,
        "window_trades": point.window_trades,
        "rolling_pnl": str(point.rolling_pnl),
        "rolling_win_rate_pct": str(point.rolling_win_rate_pct),
    }


def _result_payload(result: AnalyticsResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "total_trades": result.total_trades,
        "wins": result.wins,
        "losses": result.losses,
        "breakeven": result.breakeven,
        "win_rate_pct": str(result.win_rate_pct),
        "total_pnl": str(result.total_pnl),
        "average_pnl": str(result.average_pnl),
        "best_trade_pnl": str(result.best_trade_pnl),
        "worst_trade_pnl": str(result.worst_trade_pnl),
        "average_holding_seconds": str(result.average_holding_seconds),
        "max_consecutive_wins": result.max_consecutive_wins,
        "max_consecutive_losses": result.max_consecutive_losses,
        "long_stats": _group_payload(result.long_stats),
        "short_stats": _group_payload(result.short_stats),
        "symbol_stats": [_group_payload(x) for x in result.symbol_stats],
        "strategy_stats": [_group_payload(x) for x in result.strategy_stats],
        "exit_reason_stats": [_group_payload(x) for x in result.exit_reason_stats],
        "weekday_stats": [_group_payload(x) for x in result.weekday_stats],
        "hour_stats": [_group_payload(x) for x in result.hour_stats],
        "pnl_distribution": [_bucket_payload(x) for x in result.pnl_distribution],
        "holding_distribution": [_bucket_payload(x) for x in result.holding_distribution],
        "rolling_performance": [_rolling_payload(x) for x in result.rolling_performance],
        "symbol_contribution": [_group_payload(x) for x in result.symbol_contribution],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_trade(trade: AnalyticsTrade) -> AnalyticsTrade:
    trade_id = trade.trade_id.strip()
    if not trade_id:
        raise AnalyticsError("trade_id is required")
    symbol = _symbol(trade.symbol)
    direction = trade.direction.strip().upper()
    if direction not in {"LONG", "SHORT"}:
        raise AnalyticsError("direction must be LONG or SHORT")
    strategy = trade.strategy.strip().upper()
    if not strategy:
        raise AnalyticsError("strategy is required")
    entry = _timestamp(trade.entry_time)
    exit_ = _timestamp(trade.exit_time)
    if exit_ <= entry:
        raise AnalyticsError("exit_time must be after entry_time")
    reason = trade.exit_reason.strip().upper()
    if not reason:
        raise AnalyticsError("exit_reason is required")
    pnl = _q(trade.net_pnl)
    holding = int(trade.holding_seconds)
    if holding <= 0:
        raise AnalyticsError("holding_seconds must be positive")
    tags = tuple(sorted({str(tag).strip().lower() for tag in trade.tags if str(tag).strip()}))
    return AnalyticsTrade(
        trade_id=trade_id,
        symbol=symbol,
        direction=direction,
        strategy=strategy,
        entry_time=entry.isoformat(),
        exit_time=exit_.isoformat(),
        exit_reason=reason,
        net_pnl=pnl,
        holding_seconds=holding,
        tags=tags,
    )


def filter_trades(
    trades: Iterable[AnalyticsTrade],
    *,
    symbol: str | None = None,
    strategy: str | None = None,
    direction: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> tuple[AnalyticsTrade, ...]:
    normalized = tuple(sorted(
        (_normalize_trade(trade) for trade in trades),
        key=lambda item: (item.exit_time, item.trade_id),
    ))
    if len({trade.trade_id for trade in normalized}) != len(normalized):
        raise AnalyticsError("duplicate trade IDs detected")

    symbol_n = None if symbol is None else _symbol(symbol)
    strategy_n = None if strategy is None else strategy.strip().upper()
    direction_n = None if direction is None else direction.strip().upper()
    if direction_n is not None and direction_n not in {"LONG", "SHORT"}:
        raise AnalyticsError("invalid direction filter")
    start = None if start_time is None else _timestamp(start_time)
    end = None if end_time is None else _timestamp(end_time)
    if start is not None and end is not None and end < start:
        raise AnalyticsError("end_time cannot precede start_time")

    output = []
    for trade in normalized:
        exit_dt = _timestamp(trade.exit_time)
        if symbol_n is not None and trade.symbol != symbol_n:
            continue
        if strategy_n is not None and trade.strategy != strategy_n:
            continue
        if direction_n is not None and trade.direction != direction_n:
            continue
        if start is not None and exit_dt < start:
            continue
        if end is not None and exit_dt > end:
            continue
        output.append(trade)
    return tuple(output)


def _group_stat(key: str, items: list[AnalyticsTrade]) -> GroupStat:
    trades = len(items)
    wins = sum(1 for trade in items if trade.net_pnl > ZERO)
    losses = sum(1 for trade in items if trade.net_pnl < ZERO)
    total = sum((trade.net_pnl for trade in items), ZERO)
    average = total / Decimal(trades) if trades else ZERO
    win_rate = Decimal(wins) / Decimal(trades) * Decimal("100") if trades else ZERO
    return GroupStat(key, trades, wins, losses, _q(total), _q(average), _q(win_rate))


def _group_by(trades: tuple[AnalyticsTrade, ...], key_fn) -> tuple[GroupStat, ...]:
    grouped: dict[str, list[AnalyticsTrade]] = {}
    for trade in trades:
        grouped.setdefault(str(key_fn(trade)), []).append(trade)
    return tuple(_group_stat(key, grouped[key]) for key in sorted(grouped))


def _streaks(trades: tuple[AnalyticsTrade, ...]) -> tuple[int, int]:
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


def _pnl_bucket(pnl: Decimal) -> str:
    if pnl < Decimal("-1000"):
        return "<-1000"
    if pnl < Decimal("-250"):
        return "-1000_to_-250"
    if pnl < ZERO:
        return "-250_to_0"
    if pnl == ZERO:
        return "0"
    if pnl <= Decimal("250"):
        return "0_to_250"
    if pnl <= Decimal("1000"):
        return "250_to_1000"
    return ">1000"


def _holding_bucket(seconds: int) -> str:
    if seconds < 3600:
        return "<1h"
    if seconds < 86400:
        return "1h_to_1d"
    if seconds < 604800:
        return "1d_to_7d"
    return ">=7d"


def _bucket_stats(trades: tuple[AnalyticsTrade, ...], bucket_fn) -> tuple[BucketStat, ...]:
    grouped: dict[str, list[AnalyticsTrade]] = {}
    for trade in trades:
        grouped.setdefault(bucket_fn(trade), []).append(trade)
    return tuple(
        BucketStat(
            bucket=key,
            trades=len(grouped[key]),
            total_pnl=_q(sum((trade.net_pnl for trade in grouped[key]), ZERO)),
        )
        for key in sorted(grouped)
    )


def _rolling(trades: tuple[AnalyticsTrade, ...], window: int) -> tuple[RollingPoint, ...]:
    if window <= 0:
        raise AnalyticsError("rolling window must be positive")
    output = []
    for index in range(window - 1, len(trades)):
        segment = trades[index - window + 1:index + 1]
        pnl = sum((trade.net_pnl for trade in segment), ZERO)
        wins = sum(1 for trade in segment if trade.net_pnl > ZERO)
        win_rate = Decimal(wins) / Decimal(window) * Decimal("100")
        output.append(RollingPoint(
            end_trade_id=segment[-1].trade_id,
            window_trades=window,
            rolling_pnl=_q(pnl),
            rolling_win_rate_pct=_q(win_rate),
        ))
    return tuple(output)


def analyze_trades(
    trades: Iterable[AnalyticsTrade],
    *,
    rolling_window: int = 3,
) -> AnalyticsResult:
    normalized = filter_trades(trades)
    if not normalized:
        raise AnalyticsError("at least one trade is required")

    total = len(normalized)
    wins = sum(1 for trade in normalized if trade.net_pnl > ZERO)
    losses = sum(1 for trade in normalized if trade.net_pnl < ZERO)
    breakeven = total - wins - losses
    total_pnl = sum((trade.net_pnl for trade in normalized), ZERO)
    avg_pnl = total_pnl / Decimal(total)
    best = max(trade.net_pnl for trade in normalized)
    worst = min(trade.net_pnl for trade in normalized)
    avg_holding = Decimal(sum(trade.holding_seconds for trade in normalized)) / Decimal(total)
    max_wins, max_losses = _streaks(normalized)

    long_items = [trade for trade in normalized if trade.direction == "LONG"]
    short_items = [trade for trade in normalized if trade.direction == "SHORT"]

    symbol_stats = _group_by(normalized, lambda trade: trade.symbol)
    strategy_stats = _group_by(normalized, lambda trade: trade.strategy)
    exit_stats = _group_by(normalized, lambda trade: trade.exit_reason)
    weekday_stats = _group_by(
        normalized,
        lambda trade: _timestamp(trade.exit_time).strftime("%A").upper(),
    )
    hour_stats = _group_by(
        normalized,
        lambda trade: f"{_timestamp(trade.exit_time).hour:02d}:00",
    )
    contribution = tuple(sorted(
        symbol_stats,
        key=lambda stat: (stat.total_pnl, stat.key),
        reverse=True,
    ))

    pnl_distribution = _bucket_stats(normalized, lambda trade: _pnl_bucket(trade.net_pnl))
    holding_distribution = _bucket_stats(normalized, lambda trade: _holding_bucket(trade.holding_seconds))
    rolling = _rolling(normalized, rolling_window)

    input_hash = _hash({
        "trades": [_trade_payload(trade) for trade in normalized],
        "rolling_window": rolling_window,
    })
    result = AnalyticsResult(
        version=VERSION,
        total_trades=total,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate_pct=_q(Decimal(wins) / Decimal(total) * Decimal("100")),
        total_pnl=_q(total_pnl),
        average_pnl=_q(avg_pnl),
        best_trade_pnl=_q(best),
        worst_trade_pnl=_q(worst),
        average_holding_seconds=_q(avg_holding),
        max_consecutive_wins=max_wins,
        max_consecutive_losses=max_losses,
        long_stats=_group_stat("LONG", long_items),
        short_stats=_group_stat("SHORT", short_items),
        symbol_stats=symbol_stats,
        strategy_stats=strategy_stats,
        exit_reason_stats=exit_stats,
        weekday_stats=weekday_stats,
        hour_stats=hour_stats,
        pnl_distribution=pnl_distribution,
        holding_distribution=holding_distribution,
        rolling_performance=rolling,
        symbol_contribution=contribution,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: AnalyticsResult) -> bool:
    if result.version != VERSION:
        raise AnalyticsError("unsupported result version")
    if result.total_trades != result.wins + result.losses + result.breakeven:
        raise AnalyticsError("trade classification count mismatch")
    if result.total_trades <= 0:
        raise AnalyticsError("total_trades must be positive")
    if result.win_rate_pct < ZERO or result.win_rate_pct > Decimal("100"):
        raise AnalyticsError("win rate out of range")
    if tuple(stat.key for stat in result.symbol_stats) != tuple(sorted(stat.key for stat in result.symbol_stats)):
        raise AnalyticsError("symbol stats must be sorted")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise AnalyticsError("result hash mismatch")
    return True


def save_result(result: AnalyticsResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def _load_group(item: dict[str, Any]) -> GroupStat:
    return GroupStat(
        key=item["key"],
        trades=int(item["trades"]),
        wins=int(item["wins"]),
        losses=int(item["losses"]),
        total_pnl=_d(item["total_pnl"]),
        average_pnl=_d(item["average_pnl"]),
        win_rate_pct=_d(item["win_rate_pct"]),
    )


def load_result(path: str | Path) -> AnalyticsResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result = AnalyticsResult(
        version=payload["version"],
        total_trades=int(payload["total_trades"]),
        wins=int(payload["wins"]),
        losses=int(payload["losses"]),
        breakeven=int(payload["breakeven"]),
        win_rate_pct=_d(payload["win_rate_pct"]),
        total_pnl=_d(payload["total_pnl"]),
        average_pnl=_d(payload["average_pnl"]),
        best_trade_pnl=_d(payload["best_trade_pnl"]),
        worst_trade_pnl=_d(payload["worst_trade_pnl"]),
        average_holding_seconds=_d(payload["average_holding_seconds"]),
        max_consecutive_wins=int(payload["max_consecutive_wins"]),
        max_consecutive_losses=int(payload["max_consecutive_losses"]),
        long_stats=_load_group(payload["long_stats"]),
        short_stats=_load_group(payload["short_stats"]),
        symbol_stats=tuple(_load_group(x) for x in payload["symbol_stats"]),
        strategy_stats=tuple(_load_group(x) for x in payload["strategy_stats"]),
        exit_reason_stats=tuple(_load_group(x) for x in payload["exit_reason_stats"]),
        weekday_stats=tuple(_load_group(x) for x in payload["weekday_stats"]),
        hour_stats=tuple(_load_group(x) for x in payload["hour_stats"]),
        pnl_distribution=tuple(BucketStat(x["bucket"], int(x["trades"]), _d(x["total_pnl"])) for x in payload["pnl_distribution"]),
        holding_distribution=tuple(BucketStat(x["bucket"], int(x["trades"]), _d(x["total_pnl"])) for x in payload["holding_distribution"]),
        rolling_performance=tuple(RollingPoint(
            x["end_trade_id"], int(x["window_trades"]), _d(x["rolling_pnl"]), _d(x["rolling_win_rate_pct"])
        ) for x in payload["rolling_performance"]),
        symbol_contribution=tuple(_load_group(x) for x in payload["symbol_contribution"]),
        input_hash=payload["input_hash"],
        result_hash=payload["result_hash"],
    )
    verify_result(result)
    return result


def export_summary_csv(result: AnalyticsResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "group_type", "key", "trades", "wins", "losses",
            "total_pnl", "average_pnl", "win_rate_pct",
        ])
        writer.writeheader()
        groups = (
            ("SYMBOL", result.symbol_stats),
            ("STRATEGY", result.strategy_stats),
            ("EXIT_REASON", result.exit_reason_stats),
            ("WEEKDAY", result.weekday_stats),
            ("HOUR", result.hour_stats),
        )
        for group_type, stats in groups:
            for stat in stats:
                writer.writerow({
                    "group_type": group_type,
                    "key": stat.key,
                    "trades": stat.trades,
                    "wins": stat.wins,
                    "losses": stat.losses,
                    "total_pnl": stat.total_pnl,
                    "average_pnl": stat.average_pnl,
                    "win_rate_pct": stat.win_rate_pct,
                })
    return target


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
