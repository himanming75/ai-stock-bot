#!/usr/bin/env python3
"""
V51.0 Paper Performance Metrics Foundation

Consumes one or more V50 account snapshot exports and optional realized trade
P&L values. Produces deterministic offline performance metrics including:

- equity curve
- total return
- cumulative return
- gross profit / gross loss / net profit
- win / loss / breakeven counts
- win rate / loss rate
- average win / average loss
- payoff ratio
- profit factor
- expectancy
- peak equity / lowest equity
- current drawdown / maximum drawdown
- recovery factor
- SHA-256 integrity verification
- hash-chained metrics ledger

No broker connectivity, no market-data request, and no network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Sequence

VERSION = "51.0"
MONEY_Q = Decimal("0.0001")
RATIO_Q = Decimal("0.000001")


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dec(value: Any, *, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def q_money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def q_ratio(value: Decimal) -> str:
    return format(value.quantize(RATIO_Q, rounding=ROUND_HALF_UP), "f")


def safe_ratio(numerator: Decimal, denominator: Decimal) -> tuple[str, bool]:
    if denominator == 0:
        if numerator > 0:
            return "Infinity", True
        return "0.000000", False
    return q_ratio(numerator / denominator), False


@dataclass(frozen=True)
class SnapshotInput:
    schema_version: str
    version: str
    status: str
    decision: str
    snapshot_time: str
    reconciliation_sha256: str
    cash_balance: str
    buying_power: str
    total_market_value: str
    net_liquidation_value: str
    prior_net_liquidation_value: str
    daily_pnl: str
    daily_return: str
    cumulative_pnl: str
    cumulative_return: str
    cash_allocation: str
    invested_allocation: str
    gross_exposure: str
    net_exposure: str
    leverage_ratio: str
    long_market_value: str
    short_market_value: str
    position_count: int
    positions: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    snapshot_sha256: str


@dataclass(frozen=True)
class EquityPoint:
    sequence: int
    snapshot_time: str
    net_liquidation_value: str
    daily_pnl: str
    cumulative_pnl: str
    peak_equity: str
    drawdown_amount: str
    drawdown_rate: str
    snapshot_sha256: str
    point_sha256: str


@dataclass(frozen=True)
class MetricsLedgerEntry:
    sequence: int
    event_type: str
    snapshot_count: int
    trade_count: int
    net_profit: str
    maximum_drawdown: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class PerformanceMetricsResult:
    schema_version: str
    version: str
    status: str
    decision: str
    snapshot_count: int
    trade_count: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    starting_equity: str
    ending_equity: str
    total_return: str
    cumulative_return: str
    gross_profit: str
    gross_loss: str
    net_profit: str
    win_rate: str
    loss_rate: str
    breakeven_rate: str
    average_win: str
    average_loss: str
    payoff_ratio: str
    profit_factor: str
    profit_factor_infinite: bool
    expectancy: str
    peak_equity: str
    lowest_equity: str
    current_drawdown_amount: str
    current_drawdown: str
    maximum_drawdown_amount: str
    maximum_drawdown: str
    recovery_factor: str
    recovery_factor_infinite: bool
    equity_curve: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    metrics_sha256: str


class PaperPerformanceMetricsEngine:
    def __init__(self, *, mode: str = "paper", enable_live: bool = False) -> None:
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.ledger: list[MetricsLedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live performance transport is intentionally not implemented in V51.0"
            )

    @staticmethod
    def snapshot_hash_payload(snapshot: SnapshotInput) -> dict[str, Any]:
        return {
            "schema_version": snapshot.schema_version,
            "version": snapshot.version,
            "status": snapshot.status,
            "decision": snapshot.decision,
            "snapshot_time": snapshot.snapshot_time,
            "reconciliation_sha256": snapshot.reconciliation_sha256,
            "cash_balance": snapshot.cash_balance,
            "buying_power": snapshot.buying_power,
            "total_market_value": snapshot.total_market_value,
            "net_liquidation_value": snapshot.net_liquidation_value,
            "prior_net_liquidation_value": snapshot.prior_net_liquidation_value,
            "daily_pnl": snapshot.daily_pnl,
            "daily_return": snapshot.daily_return,
            "cumulative_pnl": snapshot.cumulative_pnl,
            "cumulative_return": snapshot.cumulative_return,
            "cash_allocation": snapshot.cash_allocation,
            "invested_allocation": snapshot.invested_allocation,
            "gross_exposure": snapshot.gross_exposure,
            "net_exposure": snapshot.net_exposure,
            "leverage_ratio": snapshot.leverage_ratio,
            "long_market_value": snapshot.long_market_value,
            "short_market_value": snapshot.short_market_value,
            "position_count": snapshot.position_count,
            "positions": snapshot.positions,
            "ledger": snapshot.ledger,
            "rejection_reasons": snapshot.rejection_reasons,
            "network_used": snapshot.network_used,
        }

    def _append_ledger(
        self,
        *,
        snapshot_count: int,
        trade_count: int,
        net_profit: Decimal,
        maximum_drawdown: Decimal,
    ) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": "PERFORMANCE_METRICS_CREATED",
            "snapshot_count": snapshot_count,
            "trade_count": trade_count,
            "net_profit": q_money(net_profit),
            "maximum_drawdown": q_ratio(maximum_drawdown),
        }
        payload_hash = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_hash,
        }
        self.ledger.append(
            MetricsLedgerEntry(
                **core,
                entry_sha256=canonical_hash(core),
            )
        )

    def calculate(
        self,
        snapshots: Sequence[SnapshotInput],
        *,
        trade_pnls: Sequence[str] | None = None,
        initial_equity: str | None = None,
    ) -> PerformanceMetricsResult:
        self._live_gate()
        reasons: list[str] = []
        if not snapshots:
            reasons.append("at least one V50 snapshot is required")

        ordered = sorted(snapshots, key=lambda x: x.snapshot_time)
        seen_times: set[str] = set()
        equity_curve: list[EquityPoint] = []
        peak = Decimal("0")
        lowest: Decimal | None = None
        max_dd_amount = Decimal("0")
        max_dd_rate = Decimal("0")

        for index, snapshot in enumerate(ordered, start=1):
            if snapshot.snapshot_time in seen_times:
                reasons.append(f"duplicate snapshot_time: {snapshot.snapshot_time}")
            seen_times.add(snapshot.snapshot_time)
            if snapshot.status != "PASS":
                reasons.append(f"snapshot status must be PASS: {snapshot.snapshot_time}")
            if snapshot.decision != "snapshot":
                reasons.append(
                    f"snapshot decision must be snapshot: {snapshot.snapshot_time}"
                )
            if snapshot.network_used is not False:
                reasons.append(
                    f"snapshot network_used must be false: {snapshot.snapshot_time}"
                )
            if snapshot.rejection_reasons:
                reasons.append(
                    f"snapshot contains rejection reasons: {snapshot.snapshot_time}"
                )
            if snapshot.position_count != len(snapshot.positions):
                reasons.append(
                    f"snapshot position_count mismatch: {snapshot.snapshot_time}"
                )
            expected_hash = canonical_hash(self.snapshot_hash_payload(snapshot))
            if expected_hash != snapshot.snapshot_sha256:
                reasons.append(
                    f"snapshot SHA-256 verification failed: {snapshot.snapshot_time}"
                )

            equity = dec(
                snapshot.net_liquidation_value,
                field="net_liquidation_value",
            )
            if equity <= 0:
                reasons.append(
                    f"net_liquidation_value must be positive: {snapshot.snapshot_time}"
                )
            if index == 1:
                peak = equity
                lowest = equity
            else:
                peak = max(peak, equity)
                lowest = min(lowest if lowest is not None else equity, equity)

            dd_amount = max(peak - equity, Decimal("0"))
            dd_rate = dd_amount / peak if peak > 0 else Decimal("0")
            max_dd_amount = max(max_dd_amount, dd_amount)
            max_dd_rate = max(max_dd_rate, dd_rate)

            point_core = {
                "sequence": index,
                "snapshot_time": snapshot.snapshot_time,
                "net_liquidation_value": q_money(equity),
                "daily_pnl": q_money(dec(snapshot.daily_pnl, field="daily_pnl")),
                "cumulative_pnl": q_money(
                    dec(snapshot.cumulative_pnl, field="cumulative_pnl")
                ),
                "peak_equity": q_money(peak),
                "drawdown_amount": q_money(dd_amount),
                "drawdown_rate": q_ratio(dd_rate),
                "snapshot_sha256": snapshot.snapshot_sha256,
            }
            equity_curve.append(
                EquityPoint(
                    **point_core,
                    point_sha256=canonical_hash(point_core),
                )
            )

        if ordered:
            starting = (
                dec(initial_equity, field="initial_equity")
                if initial_equity is not None
                else dec(
                    ordered[0].prior_net_liquidation_value,
                    field="prior_net_liquidation_value",
                )
            )
            ending = dec(
                ordered[-1].net_liquidation_value,
                field="net_liquidation_value",
            )
        else:
            starting = Decimal("0")
            ending = Decimal("0")

        if starting <= 0 and snapshots:
            reasons.append("initial equity must be positive")

        raw_trade_pnls = list(trade_pnls or [])
        if raw_trade_pnls:
            pnl_values = [dec(x, field="trade_pnl") for x in raw_trade_pnls]
        else:
            pnl_values = [
                dec(snapshot.daily_pnl, field="daily_pnl")
                for snapshot in ordered
            ]

        wins = [x for x in pnl_values if x > 0]
        losses = [x for x in pnl_values if x < 0]
        breakeven = [x for x in pnl_values if x == 0]
        gross_profit = sum(wins, Decimal("0"))
        gross_loss = sum((-x for x in losses), Decimal("0"))
        net_profit = sum(pnl_values, Decimal("0"))
        trade_count = len(pnl_values)

        win_rate = Decimal(len(wins)) / trade_count if trade_count else Decimal("0")
        loss_rate = Decimal(len(losses)) / trade_count if trade_count else Decimal("0")
        breakeven_rate = (
            Decimal(len(breakeven)) / trade_count if trade_count else Decimal("0")
        )
        avg_win = gross_profit / len(wins) if wins else Decimal("0")
        avg_loss = gross_loss / len(losses) if losses else Decimal("0")
        payoff_ratio, _ = safe_ratio(avg_win, avg_loss)
        profit_factor, profit_factor_inf = safe_ratio(gross_profit, gross_loss)
        expectancy = net_profit / trade_count if trade_count else Decimal("0")

        total_return = ending - starting
        cumulative_return = (
            total_return / starting if starting > 0 else Decimal("0")
        )
        peak_equity = peak if ordered else Decimal("0")
        lowest_equity = lowest if lowest is not None else Decimal("0")
        current_dd_amount = (
            max(peak_equity - ending, Decimal("0")) if ordered else Decimal("0")
        )
        current_dd = (
            current_dd_amount / peak_equity
            if peak_equity > 0
            else Decimal("0")
        )
        recovery_factor, recovery_inf = safe_ratio(net_profit, max_dd_amount)

        if not reasons:
            self._append_ledger(
                snapshot_count=len(ordered),
                trade_count=trade_count,
                net_profit=net_profit,
                maximum_drawdown=max_dd_rate,
            )

        status = "PASS" if not reasons else "FAIL"
        decision = "metrics" if not reasons else "reject"
        core = {
            "schema_version": "v51.0.paper_performance_metrics.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "snapshot_count": len(ordered),
            "trade_count": trade_count,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "breakeven_trades": len(breakeven),
            "starting_equity": q_money(starting),
            "ending_equity": q_money(ending),
            "total_return": q_money(total_return),
            "cumulative_return": q_ratio(cumulative_return),
            "gross_profit": q_money(gross_profit),
            "gross_loss": q_money(gross_loss),
            "net_profit": q_money(net_profit),
            "win_rate": q_ratio(win_rate),
            "loss_rate": q_ratio(loss_rate),
            "breakeven_rate": q_ratio(breakeven_rate),
            "average_win": q_money(avg_win),
            "average_loss": q_money(avg_loss),
            "payoff_ratio": payoff_ratio,
            "profit_factor": profit_factor,
            "profit_factor_infinite": profit_factor_inf,
            "expectancy": q_money(expectancy),
            "peak_equity": q_money(peak_equity),
            "lowest_equity": q_money(lowest_equity),
            "current_drawdown_amount": q_money(current_dd_amount),
            "current_drawdown": q_ratio(current_dd),
            "maximum_drawdown_amount": q_money(max_dd_amount),
            "maximum_drawdown": q_ratio(max_dd_rate),
            "recovery_factor": recovery_factor,
            "recovery_factor_infinite": recovery_inf,
            "equity_curve": [asdict(x) for x in equity_curve],
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return PerformanceMetricsResult(
            **core,
            metrics_sha256=canonical_hash(core),
        )

    @staticmethod
    def export(path: Path, result: PerformanceMetricsResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v51.0.paper_performance_metrics_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_snapshot(path: Path) -> SnapshotInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("result", payload)
    return SnapshotInput(**raw)


def parse_trade_pnls(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for token in value.split(","):
            token = token.strip()
            if token:
                dec(token, field="trade_pnl")
                result.append(token)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V51.0 Paper Performance Metrics Foundation"
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="V50 snapshot JSON path; repeat for multiple snapshots",
    )
    parser.add_argument(
        "--trade-pnl",
        action="append",
        default=[],
        help="realized trade P&L value or comma-separated values",
    )
    parser.add_argument("--initial-equity")
    parser.add_argument(
        "--mode",
        choices=["replay", "paper", "live"],
        default="paper",
    )
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument(
        "--output",
        default=(
            "release/v51/audit/"
            "paper_performance_metrics_result_v51_0.json"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        engine = PaperPerformanceMetricsEngine(
            mode=args.mode,
            enable_live=args.enable_live,
        )
        snapshots = [load_snapshot(Path(path)) for path in args.input]
        result = engine.calculate(
            snapshots,
            trade_pnls=parse_trade_pnls(args.trade_pnl),
            initial_equity=args.initial_equity,
        )
        engine.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (
        TypeError,
        ValueError,
        PermissionError,
        NotImplementedError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        error = {
            "schema_version": "v51.0.paper_performance_metrics_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(error, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
