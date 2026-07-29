#!/usr/bin/env python3
"""
V52.0 Risk-Adjusted Return Metrics Foundation

Consumes one or more V50 account snapshot exports and calculates deterministic,
offline risk-adjusted performance metrics:

- periodic returns
- arithmetic mean return
- annualized return
- volatility
- downside deviation
- Sharpe ratio
- Sortino ratio
- Calmar ratio
- positive / negative / flat period counts
- best / worst period return
- return ledger hash chain
- SHA-256 integrity verification

No broker connectivity, no market-data request, and no network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Sequence

getcontext().prec = 40

VERSION = "52.0"
RATIO_Q = Decimal("0.000001")
MONEY_Q = Decimal("0.0001")


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


def q_ratio(value: Decimal) -> str:
    return format(value.quantize(RATIO_Q, rounding=ROUND_HALF_UP), "f")


def q_money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def decimal_sqrt(value: Decimal) -> Decimal:
    if value < 0:
        raise ValueError("square root input must be non-negative")
    return value.sqrt()


def sample_stddev(values: Sequence[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal("0")
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((x - mean) ** 2 for x in values) / Decimal(len(values) - 1)
    return decimal_sqrt(variance)


def safe_ratio(numerator: Decimal, denominator: Decimal) -> tuple[str, bool]:
    if denominator == 0:
        if numerator > 0:
            return "Infinity", True
        if numerator < 0:
            return "-Infinity", True
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
class ReturnPoint:
    sequence: int
    snapshot_time: str
    beginning_equity: str
    ending_equity: str
    period_return: str
    excess_return: str
    downside_return: str
    snapshot_sha256: str
    point_sha256: str


@dataclass(frozen=True)
class RiskLedgerEntry:
    sequence: int
    event_type: str
    period_count: int
    annualization_factor: str
    mean_return: str
    volatility: str
    sharpe_ratio: str
    sortino_ratio: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class RiskAdjustedMetricsResult:
    schema_version: str
    version: str
    status: str
    decision: str
    snapshot_count: int
    period_count: int
    annualization_factor: str
    risk_free_rate_annual: str
    target_return_annual: str
    risk_free_rate_periodic: str
    target_return_periodic: str
    positive_periods: int
    negative_periods: int
    flat_periods: int
    arithmetic_mean_return: str
    cumulative_return: str
    annualized_return: str
    volatility_periodic: str
    volatility_annualized: str
    downside_deviation_periodic: str
    downside_deviation_annualized: str
    sharpe_ratio: str
    sharpe_ratio_infinite: bool
    sortino_ratio: str
    sortino_ratio_infinite: bool
    maximum_drawdown: str
    calmar_ratio: str
    calmar_ratio_infinite: bool
    best_period_return: str
    worst_period_return: str
    return_points: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    metrics_sha256: str


class RiskAdjustedReturnMetricsEngine:
    def __init__(self, *, mode: str = "paper", enable_live: bool = False) -> None:
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.ledger: list[RiskLedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live risk-adjusted metrics transport is intentionally "
                "not implemented in V52.0"
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
        period_count: int,
        annualization_factor: Decimal,
        mean_return: Decimal,
        volatility: Decimal,
        sharpe_ratio: str,
        sortino_ratio: str,
    ) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": "RISK_ADJUSTED_METRICS_CREATED",
            "period_count": period_count,
            "annualization_factor": q_ratio(annualization_factor),
            "mean_return": q_ratio(mean_return),
            "volatility": q_ratio(volatility),
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
        }
        payload_hash = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_hash,
        }
        self.ledger.append(
            RiskLedgerEntry(
                **core,
                entry_sha256=canonical_hash(core),
            )
        )

    def calculate(
        self,
        snapshots: Sequence[SnapshotInput],
        *,
        annualization_factor: str = "252",
        risk_free_rate_annual: str = "0",
        target_return_annual: str = "0",
    ) -> RiskAdjustedMetricsResult:
        self._live_gate()
        reasons: list[str] = []

        annual_factor = dec(annualization_factor, field="annualization_factor")
        rf_annual = dec(risk_free_rate_annual, field="risk_free_rate_annual")
        target_annual = dec(target_return_annual, field="target_return_annual")

        if annual_factor <= 0:
            reasons.append("annualization_factor must be positive")
        if rf_annual <= Decimal("-1"):
            reasons.append("risk_free_rate_annual must be greater than -1")
        if target_annual <= Decimal("-1"):
            reasons.append("target_return_annual must be greater than -1")
        if not snapshots:
            reasons.append("at least one V50 snapshot is required")

        ordered = sorted(snapshots, key=lambda x: x.snapshot_time)
        seen_times: set[str] = set()
        returns: list[Decimal] = []
        return_points: list[ReturnPoint] = []
        peak = Decimal("0")
        max_drawdown = Decimal("0")

        periodic_rf = (
            (Decimal("1") + rf_annual) ** (Decimal("1") / annual_factor)
            - Decimal("1")
            if annual_factor > 0 and rf_annual > Decimal("-1")
            else Decimal("0")
        )
        periodic_target = (
            (Decimal("1") + target_annual) ** (Decimal("1") / annual_factor)
            - Decimal("1")
            if annual_factor > 0 and target_annual > Decimal("-1")
            else Decimal("0")
        )

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

            ending = dec(
                snapshot.net_liquidation_value,
                field="net_liquidation_value",
            )
            beginning = dec(
                snapshot.prior_net_liquidation_value,
                field="prior_net_liquidation_value",
            )
            if beginning <= 0:
                reasons.append(
                    f"prior_net_liquidation_value must be positive: "
                    f"{snapshot.snapshot_time}"
                )
            if ending <= 0:
                reasons.append(
                    f"net_liquidation_value must be positive: {snapshot.snapshot_time}"
                )

            period_return = (
                (ending - beginning) / beginning
                if beginning > 0
                else Decimal("0")
            )
            excess_return = period_return - periodic_rf
            downside_return = min(
                period_return - periodic_target,
                Decimal("0"),
            )
            returns.append(period_return)

            peak = ending if index == 1 else max(peak, ending)
            drawdown = (
                (peak - ending) / peak
                if peak > 0
                else Decimal("0")
            )
            max_drawdown = max(max_drawdown, drawdown)

            point_core = {
                "sequence": index,
                "snapshot_time": snapshot.snapshot_time,
                "beginning_equity": q_money(beginning),
                "ending_equity": q_money(ending),
                "period_return": q_ratio(period_return),
                "excess_return": q_ratio(excess_return),
                "downside_return": q_ratio(downside_return),
                "snapshot_sha256": snapshot.snapshot_sha256,
            }
            return_points.append(
                ReturnPoint(
                    **point_core,
                    point_sha256=canonical_hash(point_core),
                )
            )

        period_count = len(returns)
        mean_return = (
            sum(returns, Decimal("0")) / Decimal(period_count)
            if period_count
            else Decimal("0")
        )
        periodic_vol = sample_stddev(returns)
        annualized_vol = (
            periodic_vol * decimal_sqrt(annual_factor)
            if annual_factor > 0
            else Decimal("0")
        )

        downside_values = [
            min(x - periodic_target, Decimal("0"))
            for x in returns
        ]
        downside_variance = (
            sum(x * x for x in downside_values) / Decimal(period_count)
            if period_count
            else Decimal("0")
        )
        downside_periodic = decimal_sqrt(downside_variance)
        downside_annualized = (
            downside_periodic * decimal_sqrt(annual_factor)
            if annual_factor > 0
            else Decimal("0")
        )

        mean_excess_periodic = mean_return - periodic_rf
        sharpe_num = (
            mean_excess_periodic * decimal_sqrt(annual_factor)
            if annual_factor > 0
            else Decimal("0")
        )
        sharpe, sharpe_inf = safe_ratio(sharpe_num, periodic_vol)

        mean_downside_excess = mean_return - periodic_target
        sortino_num = (
            mean_downside_excess * decimal_sqrt(annual_factor)
            if annual_factor > 0
            else Decimal("0")
        )
        sortino, sortino_inf = safe_ratio(sortino_num, downside_periodic)

        cumulative_growth = Decimal("1")
        for value in returns:
            cumulative_growth *= Decimal("1") + value
        cumulative_return = cumulative_growth - Decimal("1") if returns else Decimal("0")

        if period_count and annual_factor > 0 and cumulative_growth > 0:
            annualized_return = (
                cumulative_growth
                ** (annual_factor / Decimal(period_count))
                - Decimal("1")
            )
        else:
            annualized_return = Decimal("0")

        calmar, calmar_inf = safe_ratio(annualized_return, max_drawdown)

        positive = sum(1 for x in returns if x > 0)
        negative = sum(1 for x in returns if x < 0)
        flat = sum(1 for x in returns if x == 0)
        best = max(returns) if returns else Decimal("0")
        worst = min(returns) if returns else Decimal("0")

        if not reasons:
            self._append_ledger(
                period_count=period_count,
                annualization_factor=annual_factor,
                mean_return=mean_return,
                volatility=annualized_vol,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
            )

        status = "PASS" if not reasons else "FAIL"
        decision = "risk_metrics" if not reasons else "reject"

        core = {
            "schema_version": "v52.0.risk_adjusted_return_metrics.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "snapshot_count": len(ordered),
            "period_count": period_count,
            "annualization_factor": q_ratio(annual_factor),
            "risk_free_rate_annual": q_ratio(rf_annual),
            "target_return_annual": q_ratio(target_annual),
            "risk_free_rate_periodic": q_ratio(periodic_rf),
            "target_return_periodic": q_ratio(periodic_target),
            "positive_periods": positive,
            "negative_periods": negative,
            "flat_periods": flat,
            "arithmetic_mean_return": q_ratio(mean_return),
            "cumulative_return": q_ratio(cumulative_return),
            "annualized_return": q_ratio(annualized_return),
            "volatility_periodic": q_ratio(periodic_vol),
            "volatility_annualized": q_ratio(annualized_vol),
            "downside_deviation_periodic": q_ratio(downside_periodic),
            "downside_deviation_annualized": q_ratio(downside_annualized),
            "sharpe_ratio": sharpe,
            "sharpe_ratio_infinite": sharpe_inf,
            "sortino_ratio": sortino,
            "sortino_ratio_infinite": sortino_inf,
            "maximum_drawdown": q_ratio(max_drawdown),
            "calmar_ratio": calmar,
            "calmar_ratio_infinite": calmar_inf,
            "best_period_return": q_ratio(best),
            "worst_period_return": q_ratio(worst),
            "return_points": [asdict(x) for x in return_points],
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return RiskAdjustedMetricsResult(
            **core,
            metrics_sha256=canonical_hash(core),
        )

    @staticmethod
    def export(path: Path, result: RiskAdjustedMetricsResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v52.0.risk_adjusted_return_metrics_export.1",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V52.0 Risk-Adjusted Return Metrics Foundation"
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="V50 snapshot JSON path; repeat for multiple snapshots",
    )
    parser.add_argument("--annualization-factor", default="252")
    parser.add_argument("--risk-free-rate-annual", default="0")
    parser.add_argument("--target-return-annual", default="0")
    parser.add_argument(
        "--mode",
        choices=["replay", "paper", "live"],
        default="paper",
    )
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument(
        "--output",
        default=(
            "release/v52/audit/"
            "risk_adjusted_return_metrics_result_v52_0.json"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        engine = RiskAdjustedReturnMetricsEngine(
            mode=args.mode,
            enable_live=args.enable_live,
        )
        snapshots = [load_snapshot(Path(path)) for path in args.input]
        result = engine.calculate(
            snapshots,
            annualization_factor=args.annualization_factor,
            risk_free_rate_annual=args.risk_free_rate_annual,
            target_return_annual=args.target_return_annual,
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
            "schema_version": "v52.0.risk_adjusted_return_metrics_error.1",
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
