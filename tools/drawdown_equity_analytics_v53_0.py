#!/usr/bin/env python3
"""
V53.0 Drawdown & Equity Analytics Foundation

Consumes one or more V50 account snapshot exports and calculates deterministic,
offline drawdown and equity analytics:

- equity curve
- rolling peak
- underwater curve
- drawdown amount / rate
- drawdown duration
- recovery duration
- maximum drawdown event
- longest drawdown duration
- recovered / unrecovered events
- rolling high / low
- equity statistics
- SHA-256 verification
- drawdown event ledger

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

VERSION = "53.0"
MONEY_Q = Decimal("0.0001")
RATIO_Q = Decimal("0.000001")


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
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
    equity: str
    rolling_peak: str
    rolling_low: str
    drawdown_amount: str
    drawdown_rate: str
    underwater: bool
    drawdown_duration_periods: int
    snapshot_sha256: str
    point_sha256: str


@dataclass(frozen=True)
class DrawdownEvent:
    event_id: int
    peak_sequence: int
    peak_time: str
    peak_equity: str
    trough_sequence: int
    trough_time: str
    trough_equity: str
    drawdown_amount: str
    drawdown_rate: str
    duration_to_trough_periods: int
    recovery_sequence: int | None
    recovery_time: str | None
    recovery_duration_periods: int | None
    total_underwater_periods: int
    recovered: bool
    event_sha256: str


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event_type: str
    snapshot_count: int
    drawdown_event_count: int
    maximum_drawdown: str
    longest_drawdown_duration_periods: int
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class DrawdownAnalyticsResult:
    schema_version: str
    version: str
    status: str
    decision: str
    snapshot_count: int
    starting_equity: str
    ending_equity: str
    highest_equity: str
    lowest_equity: str
    equity_change: str
    total_return: str
    positive_equity_periods: int
    negative_equity_periods: int
    flat_equity_periods: int
    drawdown_event_count: int
    recovered_drawdown_events: int
    unrecovered_drawdown_events: int
    maximum_drawdown_amount: str
    maximum_drawdown: str
    maximum_drawdown_peak_time: str | None
    maximum_drawdown_trough_time: str | None
    longest_drawdown_duration_periods: int
    current_drawdown_amount: str
    current_drawdown: str
    current_drawdown_duration_periods: int
    underwater_now: bool
    equity_curve: list[dict[str, Any]]
    drawdown_events: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    analytics_sha256: str


class DrawdownEquityAnalyticsEngine:
    def __init__(self, *, mode: str = "paper", enable_live: bool = False) -> None:
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.ledger: list[LedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError("live drawdown transport is intentionally not implemented in V53.0")

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

    def _append_ledger(self, snapshot_count: int, event_count: int, max_dd: Decimal, longest: int) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": "DRAWDOWN_ANALYTICS_CREATED",
            "snapshot_count": snapshot_count,
            "drawdown_event_count": event_count,
            "maximum_drawdown": q_ratio(max_dd),
            "longest_drawdown_duration_periods": longest,
        }
        payload_sha = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_sha,
        }
        self.ledger.append(LedgerEntry(**core, entry_sha256=canonical_hash(core)))

    def calculate(self, snapshots: Sequence[SnapshotInput]) -> DrawdownAnalyticsResult:
        self._live_gate()
        reasons: list[str] = []
        if not snapshots:
            reasons.append("at least one V50 snapshot is required")

        ordered = sorted(snapshots, key=lambda x: x.snapshot_time)
        seen: set[str] = set()
        curve: list[EquityPoint] = []
        events: list[DrawdownEvent] = []
        equities: list[Decimal] = []

        peak = Decimal("0")
        rolling_low = Decimal("0")
        underwater_duration = 0
        active = None

        for i, snapshot in enumerate(ordered, start=1):
            if snapshot.snapshot_time in seen:
                reasons.append(f"duplicate snapshot_time: {snapshot.snapshot_time}")
            seen.add(snapshot.snapshot_time)
            if snapshot.status != "PASS":
                reasons.append(f"snapshot status must be PASS: {snapshot.snapshot_time}")
            if snapshot.decision != "snapshot":
                reasons.append(f"snapshot decision must be snapshot: {snapshot.snapshot_time}")
            if snapshot.network_used is not False:
                reasons.append(f"snapshot network_used must be false: {snapshot.snapshot_time}")
            if snapshot.rejection_reasons:
                reasons.append(f"snapshot contains rejection reasons: {snapshot.snapshot_time}")
            if snapshot.position_count != len(snapshot.positions):
                reasons.append(f"snapshot position_count mismatch: {snapshot.snapshot_time}")
            if canonical_hash(self.snapshot_hash_payload(snapshot)) != snapshot.snapshot_sha256:
                reasons.append(f"snapshot SHA-256 verification failed: {snapshot.snapshot_time}")

            equity = dec(snapshot.net_liquidation_value, field="net_liquidation_value")
            if equity <= 0:
                reasons.append(f"net_liquidation_value must be positive: {snapshot.snapshot_time}")
            equities.append(equity)

            if i == 1:
                peak = equity
                rolling_low = equity
            rolling_low = min(rolling_low, equity)

            if equity >= peak:
                if active is not None:
                    trough_seq, trough_time, trough_eq = active["trough"]
                    peak_seq, peak_time, peak_eq = active["peak"]
                    core = {
                        "event_id": len(events) + 1,
                        "peak_sequence": peak_seq,
                        "peak_time": peak_time,
                        "peak_equity": q_money(peak_eq),
                        "trough_sequence": trough_seq,
                        "trough_time": trough_time,
                        "trough_equity": q_money(trough_eq),
                        "drawdown_amount": q_money(peak_eq - trough_eq),
                        "drawdown_rate": q_ratio((peak_eq - trough_eq) / peak_eq),
                        "duration_to_trough_periods": trough_seq - peak_seq,
                        "recovery_sequence": i,
                        "recovery_time": snapshot.snapshot_time,
                        "recovery_duration_periods": i - peak_seq,
                        "total_underwater_periods": i - peak_seq - 1,
                        "recovered": True,
                    }
                    events.append(DrawdownEvent(**core, event_sha256=canonical_hash(core)))
                    active = None
                    underwater_duration = 0
                peak = equity
                dd_amount = Decimal("0")
                dd_rate = Decimal("0")
                underwater = False
            else:
                underwater = True
                underwater_duration += 1
                dd_amount = peak - equity
                dd_rate = dd_amount / peak
                if active is None:
                    peak_point = curve[-1]
                    active = {
                        "peak": (
                            peak_point.sequence,
                            peak_point.snapshot_time,
                            Decimal(peak_point.equity),
                        ),
                        "trough": (i, snapshot.snapshot_time, equity),
                    }
                elif equity < active["trough"][2]:
                    active["trough"] = (i, snapshot.snapshot_time, equity)

            point_core = {
                "sequence": i,
                "snapshot_time": snapshot.snapshot_time,
                "equity": q_money(equity),
                "rolling_peak": q_money(peak),
                "rolling_low": q_money(rolling_low),
                "drawdown_amount": q_money(dd_amount),
                "drawdown_rate": q_ratio(dd_rate),
                "underwater": underwater,
                "drawdown_duration_periods": underwater_duration,
                "snapshot_sha256": snapshot.snapshot_sha256,
            }
            curve.append(EquityPoint(**point_core, point_sha256=canonical_hash(point_core)))

        if active is not None:
            trough_seq, trough_time, trough_eq = active["trough"]
            peak_seq, peak_time, peak_eq = active["peak"]
            core = {
                "event_id": len(events) + 1,
                "peak_sequence": peak_seq,
                "peak_time": peak_time,
                "peak_equity": q_money(peak_eq),
                "trough_sequence": trough_seq,
                "trough_time": trough_time,
                "trough_equity": q_money(trough_eq),
                "drawdown_amount": q_money(peak_eq - trough_eq),
                "drawdown_rate": q_ratio((peak_eq - trough_eq) / peak_eq),
                "duration_to_trough_periods": trough_seq - peak_seq,
                "recovery_sequence": None,
                "recovery_time": None,
                "recovery_duration_periods": None,
                "total_underwater_periods": len(ordered) - peak_seq,
                "recovered": False,
            }
            events.append(DrawdownEvent(**core, event_sha256=canonical_hash(core)))

        starting = equities[0] if equities else Decimal("0")
        ending = equities[-1] if equities else Decimal("0")
        highest = max(equities) if equities else Decimal("0")
        lowest = min(equities) if equities else Decimal("0")
        equity_change = ending - starting
        total_return = equity_change / starting if starting > 0 else Decimal("0")

        changes = [equities[i] - equities[i - 1] for i in range(1, len(equities))]
        pos = sum(1 for x in changes if x > 0)
        neg = sum(1 for x in changes if x < 0)
        flat = sum(1 for x in changes if x == 0)

        max_event = max(events, key=lambda e: Decimal(e.drawdown_rate), default=None)
        max_dd = Decimal(max_event.drawdown_rate) if max_event else Decimal("0")
        max_dd_amount = Decimal(max_event.drawdown_amount) if max_event else Decimal("0")
        longest = max((e.total_underwater_periods for e in events), default=0)
        current_point = curve[-1] if curve else None

        if not reasons:
            self._append_ledger(len(ordered), len(events), max_dd, longest)

        core = {
            "schema_version": "v53.0.drawdown_equity_analytics.1",
            "version": VERSION,
            "status": "PASS" if not reasons else "FAIL",
            "decision": "drawdown_analytics" if not reasons else "reject",
            "snapshot_count": len(ordered),
            "starting_equity": q_money(starting),
            "ending_equity": q_money(ending),
            "highest_equity": q_money(highest),
            "lowest_equity": q_money(lowest),
            "equity_change": q_money(equity_change),
            "total_return": q_ratio(total_return),
            "positive_equity_periods": pos,
            "negative_equity_periods": neg,
            "flat_equity_periods": flat,
            "drawdown_event_count": len(events),
            "recovered_drawdown_events": sum(1 for e in events if e.recovered),
            "unrecovered_drawdown_events": sum(1 for e in events if not e.recovered),
            "maximum_drawdown_amount": q_money(max_dd_amount),
            "maximum_drawdown": q_ratio(max_dd),
            "maximum_drawdown_peak_time": max_event.peak_time if max_event else None,
            "maximum_drawdown_trough_time": max_event.trough_time if max_event else None,
            "longest_drawdown_duration_periods": longest,
            "current_drawdown_amount": current_point.drawdown_amount if current_point else q_money(Decimal("0")),
            "current_drawdown": current_point.drawdown_rate if current_point else q_ratio(Decimal("0")),
            "current_drawdown_duration_periods": current_point.drawdown_duration_periods if current_point else 0,
            "underwater_now": current_point.underwater if current_point else False,
            "equity_curve": [asdict(x) for x in curve],
            "drawdown_events": [asdict(x) for x in events],
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return DrawdownAnalyticsResult(**core, analytics_sha256=canonical_hash(core))

    @staticmethod
    def export(path: Path, result: DrawdownAnalyticsResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v53.0.drawdown_equity_analytics_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_snapshot(path: Path) -> SnapshotInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SnapshotInput(**payload.get("result", payload))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V53.0 Drawdown & Equity Analytics Foundation")
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--output", default="release/v53/audit/drawdown_equity_analytics_result_v53_0.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        engine = DrawdownEquityAnalyticsEngine(mode=args.mode, enable_live=args.enable_live)
        result = engine.calculate([load_snapshot(Path(p)) for p in args.input])
        engine.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError, json.JSONDecodeError, OSError) as exc:
        error = {
            "schema_version": "v53.0.drawdown_equity_analytics_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(error, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
