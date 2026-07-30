from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


VERSION = "73.1"
SCHEMA_VERSION = "v73.1.offline_candidate_backtest.1"
SUPPORTED_V73_SCHEMA = "v73.0.parameter_optimization.1"


class BacktestError(ValueError):
    pass


@dataclass(frozen=True)
class Bar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BacktestError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BacktestError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise BacktestError("top-level JSON must be an object")
    return data


def validate_plan(plan: Dict[str, Any]) -> None:
    if plan.get("status") != "PASS":
        raise BacktestError("V73 status must be PASS")
    if plan.get("schema_version") != SUPPORTED_V73_SCHEMA:
        raise BacktestError("unsupported V73 schema_version")
    if plan.get("optimization_state") != "CANDIDATES_READY":
        raise BacktestError("V73 optimization_state must be CANDIDATES_READY")
    if plan.get("network_used") is not False:
        raise BacktestError("V73 network_used must be false")
    if plan.get("approved_for_live") is not False:
        raise BacktestError("V73 approved_for_live must be false")
    candidates = plan.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise BacktestError("V73 candidates must be a non-empty list")


def load_ohlcv_csv(path: Path) -> List[Bar]:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError as exc:
        raise BacktestError(f"OHLCV file not found: {path}") from exc

    bars: List[Bar] = []
    with handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise BacktestError(
                "OHLCV CSV requires timestamp,open,high,low,close,volume"
            )
        previous_timestamp: Optional[str] = None
        for row_number, row in enumerate(reader, start=2):
            try:
                bar = Bar(
                    timestamp=str(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            except (TypeError, ValueError) as exc:
                raise BacktestError(
                    f"invalid numeric OHLCV value at row {row_number}"
                ) from exc

            values = [bar.open, bar.high, bar.low, bar.close, bar.volume]
            if not all(math.isfinite(value) for value in values):
                raise BacktestError(f"non-finite OHLCV value at row {row_number}")
            if min(bar.open, bar.high, bar.low, bar.close) <= 0:
                raise BacktestError(f"prices must be positive at row {row_number}")
            if bar.volume < 0:
                raise BacktestError(f"volume must be non-negative at row {row_number}")
            if bar.high < max(bar.open, bar.close, bar.low):
                raise BacktestError(f"high is inconsistent at row {row_number}")
            if bar.low > min(bar.open, bar.close, bar.high):
                raise BacktestError(f"low is inconsistent at row {row_number}")
            if previous_timestamp is not None and bar.timestamp <= previous_timestamp:
                raise BacktestError("timestamps must be strictly increasing")
            previous_timestamp = bar.timestamp
            bars.append(bar)

    if len(bars) < 30:
        raise BacktestError("at least 30 OHLCV bars are required")
    return bars


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def validate_parameters(parameters: Dict[str, Any]) -> None:
    required = [
        "signal_threshold",
        "stop_loss_pct",
        "take_profit_pct",
        "min_volume_ratio",
        "cooldown_bars",
    ]
    for key in required:
        if key not in parameters:
            raise BacktestError(f"candidate parameter missing: {key}")

    signal = float(parameters["signal_threshold"])
    stop = float(parameters["stop_loss_pct"])
    target = float(parameters["take_profit_pct"])
    volume = float(parameters["min_volume_ratio"])
    cooldown = int(parameters["cooldown_bars"])

    if not 0 < signal <= 1:
        raise BacktestError("signal_threshold must be in (0, 1]")
    if not 0 < stop < 1:
        raise BacktestError("stop_loss_pct must be in (0, 1)")
    if not 0 < target < 1:
        raise BacktestError("take_profit_pct must be in (0, 1)")
    if volume <= 0:
        raise BacktestError("min_volume_ratio must be positive")
    if cooldown < 0:
        raise BacktestError("cooldown_bars must be non-negative")


def entry_signal(
    bars: Sequence[Bar],
    index: int,
    parameters: Dict[str, Any],
    lookback: int,
) -> bool:
    if index < lookback:
        return False

    prior = bars[index - lookback:index]
    channel_high = max(bar.high for bar in prior)
    channel_low = min(bar.low for bar in prior)
    channel_width = channel_high - channel_low
    if channel_width <= 0:
        return False

    current = bars[index]
    channel_position = (current.close - channel_low) / channel_width
    avg_volume = mean([bar.volume for bar in prior])
    volume_ratio = current.volume / avg_volume if avg_volume > 0 else 0.0

    return (
        channel_position >= float(parameters["signal_threshold"])
        and current.close > prior[-1].close
        and volume_ratio >= float(parameters["min_volume_ratio"])
    )


def calculate_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    pnls = [float(trade["pnl"]) for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    breakeven = [pnl for pnl in pnls if pnl == 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_pnl = sum(pnls)
    count = len(pnls)

    if gross_loss > 0:
        profit_factor: Optional[float] = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = None
    else:
        profit_factor = 0.0

    return {
        "trade_count": count,
        "win_count": len(wins),
        "loss_count": len(losses),
        "breakeven_count": len(breakeven),
        "win_rate": round(len(wins) / count, 6) if count else 0.0,
        "gross_profit": round(gross_profit, 6),
        "gross_loss": round(gross_loss, 6),
        "net_pnl": round(net_pnl, 6),
        "expectancy": round(net_pnl / count, 6) if count else 0.0,
        "profit_factor": (
            round(profit_factor, 6) if profit_factor is not None else None
        ),
    }


def run_candidate_backtest(
    bars: Sequence[Bar],
    candidate: Dict[str, Any],
    lookback: int = 20,
    initial_capital: float = 10000.0,
    risk_fraction: float = 0.01,
    max_holding_bars: int = 20,
) -> Dict[str, Any]:
    if lookback < 2:
        raise BacktestError("lookback must be at least 2")
    if initial_capital <= 0:
        raise BacktestError("initial_capital must be positive")
    if not 0 < risk_fraction <= 0.1:
        raise BacktestError("risk_fraction must be in (0, 0.1]")
    if max_holding_bars < 1:
        raise BacktestError("max_holding_bars must be at least 1")

    candidate_id = candidate.get("candidate_id")
    parameters = candidate.get("parameters")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise BacktestError("candidate_id is required")
    if not isinstance(parameters, dict):
        raise BacktestError("candidate parameters must be an object")
    validate_parameters(parameters)

    capital = float(initial_capital)
    position: Optional[Dict[str, Any]] = None
    cooldown_until = -1
    trades: List[Dict[str, Any]] = []

    for index in range(lookback, len(bars)):
        bar = bars[index]

        if position is not None:
            stop_price = position["entry_price"] * (
                1.0 - float(parameters["stop_loss_pct"])
            )
            target_price = position["entry_price"] * (
                1.0 + float(parameters["take_profit_pct"])
            )

            exit_price: Optional[float] = None
            reason: Optional[str] = None

            # Conservative same-bar assumption: stop is evaluated before target.
            if bar.low <= stop_price:
                exit_price = stop_price
                reason = "STOP_LOSS"
            elif bar.high >= target_price:
                exit_price = target_price
                reason = "TAKE_PROFIT"
            elif index - position["entry_index"] >= max_holding_bars:
                exit_price = bar.close
                reason = "MAX_HOLDING"

            if exit_price is not None:
                pnl = (exit_price - position["entry_price"]) * position["quantity"]
                capital += pnl
                trades.append({
                    "candidate_id": candidate_id,
                    "entry_index": position["entry_index"],
                    "exit_index": index,
                    "entry_timestamp": position["entry_timestamp"],
                    "exit_timestamp": bar.timestamp,
                    "entry_price": round(position["entry_price"], 6),
                    "exit_price": round(exit_price, 6),
                    "quantity": round(position["quantity"], 6),
                    "pnl": round(pnl, 6),
                    "return_pct": round(
                        (exit_price / position["entry_price"] - 1.0), 6
                    ),
                    "exit_reason": reason,
                })
                cooldown_until = index + int(parameters["cooldown_bars"])
                position = None

        if (
            position is None
            and index > cooldown_until
            and entry_signal(bars, index, parameters, lookback)
        ):
            entry_price = bar.close
            stop_distance = entry_price * float(parameters["stop_loss_pct"])
            risk_budget = capital * risk_fraction
            quantity = risk_budget / stop_distance
            position = {
                "entry_index": index,
                "entry_timestamp": bar.timestamp,
                "entry_price": entry_price,
                "quantity": quantity,
            }

    if position is not None:
        final = bars[-1]
        pnl = (final.close - position["entry_price"]) * position["quantity"]
        capital += pnl
        trades.append({
            "candidate_id": candidate_id,
            "entry_index": position["entry_index"],
            "exit_index": len(bars) - 1,
            "entry_timestamp": position["entry_timestamp"],
            "exit_timestamp": final.timestamp,
            "entry_price": round(position["entry_price"], 6),
            "exit_price": round(final.close, 6),
            "quantity": round(position["quantity"], 6),
            "pnl": round(pnl, 6),
            "return_pct": round(
                (final.close / position["entry_price"] - 1.0), 6
            ),
            "exit_reason": "END_OF_DATA",
        })

    metrics = calculate_metrics(trades)
    return {
        "candidate_id": candidate_id,
        "source_rank": candidate.get("rank"),
        "parameters": parameters,
        "evaluation_state": "BACKTEST_COMPLETED",
        "metrics": metrics,
        "initial_capital": round(initial_capital, 6),
        "ending_capital": round(capital, 6),
        "capital_return_pct": round(capital / initial_capital - 1.0, 6),
        "trades": trades,
        "approved_for_live": False,
    }


def ranking_key(result: Dict[str, Any]) -> tuple:
    metrics = result["metrics"]
    pf = metrics["profit_factor"]
    pf_value = float(pf) if pf is not None else 999999.0
    return (
        -float(metrics["expectancy"]),
        -pf_value,
        -float(metrics["win_rate"]),
        -int(metrics["trade_count"]),
        str(result["candidate_id"]),
    )


def build_backtest_report(
    plan: Dict[str, Any],
    bars: Sequence[Bar],
    lookback: int = 20,
    initial_capital: float = 10000.0,
    risk_fraction: float = 0.01,
    max_holding_bars: int = 20,
    candidate_limit: Optional[int] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_plan(plan)

    candidates = plan["candidates"]
    if candidate_limit is not None:
        if candidate_limit < 1:
            raise BacktestError("candidate_limit must be at least 1")
        candidates = candidates[:candidate_limit]

    results = [
        run_candidate_backtest(
            bars,
            candidate,
            lookback=lookback,
            initial_capital=initial_capital,
            risk_fraction=risk_fraction,
            max_holding_bars=max_holding_bars,
        )
        for candidate in candidates
    ]
    results.sort(key=ranking_key)

    for rank, result in enumerate(results, start=1):
        result["backtest_rank"] = rank

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    completed_with_trades = sum(
        1 for result in results if result["metrics"]["trade_count"] > 0
    )
    report = {
        "status": "PASS",
        "decision": "offline_candidate_backtests_completed",
        "execution_state": "BACKTESTS_COMPLETED",
        "created_at": created_at,
        "champion_strategy": plan.get("champion_strategy"),
        "revision_id": plan.get("revision_id"),
        "candidate_count": len(results),
        "candidate_count_with_trades": completed_with_trades,
        "bar_count": len(bars),
        "data_start": bars[0].timestamp,
        "data_end": bars[-1].timestamp,
        "assumptions": {
            "strategy_model": "long_only_channel_position_breakout",
            "lookback": lookback,
            "initial_capital": initial_capital,
            "risk_fraction": risk_fraction,
            "max_holding_bars": max_holding_bars,
            "same_bar_stop_before_target": True,
            "commission": 0.0,
            "slippage": 0.0,
        },
        "candidate_results": results,
        "best_candidate_id": results[0]["candidate_id"] if results else None,
        "next_step": {
            "version": "73.2",
            "action": "aggregate_and_apply_minimum_quality_gates",
            "warning": (
                "Backtest ranking alone is not promotion approval. "
                "Survivors must pass V68, V70, and V71."
            ),
        },
        "requires_quality_gate": True,
        "approved_for_live": False,
        "network_used": False,
        "source_v73_report_sha256": plan.get(
            "parameter_optimization_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    report["candidate_results_sha256"] = sha256_of(report["candidate_results"])
    report["offline_candidate_backtest_report_sha256"] = sha256_of(report)
    return report


def run(
    plan_path: Path,
    data_path: Path,
    output_path: Path,
    lookback: int,
    initial_capital: float,
    risk_fraction: float,
    max_holding_bars: int,
    candidate_limit: Optional[int],
) -> Dict[str, Any]:
    plan = read_json(plan_path)
    bars = load_ohlcv_csv(data_path)
    result = build_backtest_report(
        plan,
        bars,
        lookback=lookback,
        initial_capital=initial_capital,
        risk_fraction=risk_fraction,
        max_holding_bars=max_holding_bars,
        candidate_limit=candidate_limit,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V73.1 Offline Candidate Backtest Executor"
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    parser.add_argument("--risk-fraction", type=float, default=0.01)
    parser.add_argument("--max-holding-bars", type=int, default=20)
    parser.add_argument("--candidate-limit", type=int)
    args = parser.parse_args(argv)

    try:
        result = run(
            plan_path=args.plan,
            data_path=args.data,
            output_path=args.output,
            lookback=args.lookback,
            initial_capital=args.initial_capital,
            risk_fraction=args.risk_fraction,
            max_holding_bars=args.max_holding_bars,
            candidate_limit=args.candidate_limit,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_candidate_backtests_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    best = (
        result["candidate_results"][0]
        if result["candidate_results"]
        else None
    )
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "execution_state": result["execution_state"],
        "candidate_count": result["candidate_count"],
        "candidate_count_with_trades": result["candidate_count_with_trades"],
        "bar_count": result["bar_count"],
        "best_candidate_id": result["best_candidate_id"],
        "best_candidate_expectancy": (
            best["metrics"]["expectancy"] if best else None
        ),
        "best_candidate_profit_factor": (
            best["metrics"]["profit_factor"] if best else None
        ),
        "best_candidate_win_rate": (
            best["metrics"]["win_rate"] if best else None
        ),
        "requires_quality_gate": result["requires_quality_gate"],
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "offline_candidate_backtest_report_sha256": result[
            "offline_candidate_backtest_report_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
