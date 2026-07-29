#!/usr/bin/env python3
"""
V50.0 Paper Account Snapshot & Daily P&L Foundation

Consumes a V49 portfolio reconciliation result and produces a deterministic,
offline account snapshot with:
- cash balance
- market value
- net liquidation value
- buying power
- daily P&L
- cumulative P&L
- cash allocation
- gross/net exposure
- per-position allocation
- SHA-256 integrity and ledger chaining

No live broker connection, network request, or real market-data access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Sequence

VERSION = "50.0"
MONEY_Q = Decimal("0.0001")
RATIO_Q = Decimal("0.000001")
QTY_Q = Decimal("0.000001")


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def d(value: Any, *, field: str) -> Decimal:
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


def q_qty(value: Decimal) -> str:
    value = value.quantize(QTY_Q, rounding=ROUND_HALF_UP)
    text = format(value, "f").rstrip("0").rstrip(".")
    return text or "0"


def parse_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("snapshot_time must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("snapshot_time must include timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class PositionInput:
    symbol: str
    quantity: str
    average_cost: str
    market_price: str
    market_value: str
    cost_basis: str
    unrealized_pnl: str
    realized_pnl: str
    total_commission: str
    position_sha256: str


@dataclass(frozen=True)
class ReconciliationInput:
    schema_version: str
    version: str
    status: str
    decision: str
    simulation_sha256: str
    starting_cash: str
    ending_cash: str
    total_market_value: str
    total_cost_basis: str
    total_realized_pnl: str
    total_unrealized_pnl: str
    total_commission: str
    total_equity: str
    position_count: int
    positions: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    reconciliation_sha256: str


@dataclass(frozen=True)
class PositionAllocation:
    symbol: str
    quantity: str
    market_value: str
    allocation: str
    gross_exposure_contribution: str
    net_exposure_contribution: str
    unrealized_pnl: str
    realized_pnl: str
    allocation_sha256: str


@dataclass(frozen=True)
class SnapshotLedgerEntry:
    sequence: int
    event_type: str
    snapshot_time: str
    reconciliation_sha256: str
    net_liquidation_value: str
    daily_pnl: str
    cumulative_pnl: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class AccountSnapshotResult:
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


class PaperAccountSnapshotBuilder:
    def __init__(
        self,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        buying_power_multiplier: str = "1.0",
    ) -> None:
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.buying_power_multiplier = d(
            buying_power_multiplier,
            field="buying_power_multiplier",
        )
        if self.buying_power_multiplier < 0:
            raise ValueError("buying_power_multiplier must be non-negative")
        self.ledger: list[SnapshotLedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live account transport is intentionally not implemented in V50.0"
            )

    @staticmethod
    def _reconciliation_hash_payload(rec: ReconciliationInput) -> dict[str, Any]:
        return {
            "schema_version": rec.schema_version,
            "version": rec.version,
            "status": rec.status,
            "decision": rec.decision,
            "simulation_sha256": rec.simulation_sha256,
            "starting_cash": rec.starting_cash,
            "ending_cash": rec.ending_cash,
            "total_market_value": rec.total_market_value,
            "total_cost_basis": rec.total_cost_basis,
            "total_realized_pnl": rec.total_realized_pnl,
            "total_unrealized_pnl": rec.total_unrealized_pnl,
            "total_commission": rec.total_commission,
            "total_equity": rec.total_equity,
            "position_count": rec.position_count,
            "positions": rec.positions,
            "ledger": rec.ledger,
            "rejection_reasons": rec.rejection_reasons,
            "network_used": rec.network_used,
        }

    @staticmethod
    def _position_hash_payload(position: PositionInput) -> dict[str, Any]:
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "average_cost": position.average_cost,
            "market_price": position.market_price,
            "market_value": position.market_value,
            "cost_basis": position.cost_basis,
            "unrealized_pnl": position.unrealized_pnl,
            "realized_pnl": position.realized_pnl,
            "total_commission": position.total_commission,
        }

    def _append_ledger(
        self,
        *,
        snapshot_time: str,
        reconciliation_sha256: str,
        nlv: Decimal,
        daily_pnl: Decimal,
        cumulative_pnl: Decimal,
    ) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": "ACCOUNT_SNAPSHOT_CREATED",
            "snapshot_time": snapshot_time,
            "reconciliation_sha256": reconciliation_sha256,
            "net_liquidation_value": q_money(nlv),
            "daily_pnl": q_money(daily_pnl),
            "cumulative_pnl": q_money(cumulative_pnl),
        }
        payload_hash = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_hash,
        }
        self.ledger.append(
            SnapshotLedgerEntry(
                **core,
                entry_sha256=canonical_hash(core),
            )
        )

    def build(
        self,
        reconciliation: ReconciliationInput,
        *,
        snapshot_time: str,
        prior_net_liquidation_value: str,
        initial_equity: str,
    ) -> AccountSnapshotResult:
        self._live_gate()
        reasons: list[str] = []
        timestamp = parse_timestamp(snapshot_time)

        expected_reconciliation_hash = canonical_hash(
            self._reconciliation_hash_payload(reconciliation)
        )
        if reconciliation.status != "PASS":
            reasons.append("V49 reconciliation status must be PASS.")
        if reconciliation.decision != "reconcile":
            reasons.append("V49 reconciliation decision must be reconcile.")
        if reconciliation.network_used is not False:
            reasons.append("V49 reconciliation must report network_used=false.")
        if reconciliation.rejection_reasons:
            reasons.append("V49 reconciliation contains rejection reasons.")
        if reconciliation.position_count != len(reconciliation.positions):
            reasons.append("V49 position_count does not match positions length.")
        if expected_reconciliation_hash != reconciliation.reconciliation_sha256:
            reasons.append("V49 reconciliation SHA-256 verification failed.")

        cash = d(reconciliation.ending_cash, field="ending_cash")
        total_market_value = d(
            reconciliation.total_market_value,
            field="total_market_value",
        )
        nlv = d(reconciliation.total_equity, field="total_equity")
        prior_nlv = d(
            prior_net_liquidation_value,
            field="prior_net_liquidation_value",
        )
        initial = d(initial_equity, field="initial_equity")

        if prior_nlv <= 0:
            reasons.append("prior_net_liquidation_value must be positive.")
        if initial <= 0:
            reasons.append("initial_equity must be positive.")
        if q_money(cash + total_market_value) != q_money(nlv):
            reasons.append("V49 total_equity does not equal cash plus market value.")

        allocations: list[PositionAllocation] = []
        long_mv = Decimal("0")
        short_mv_abs = Decimal("0")
        net_mv = Decimal("0")

        if not reasons:
            for raw in reconciliation.positions:
                try:
                    position = PositionInput(**raw)
                except TypeError as exc:
                    reasons.append(f"invalid V49 position shape: {exc}")
                    break

                if canonical_hash(
                    self._position_hash_payload(position)
                ) != position.position_sha256:
                    reasons.append(
                        f"position SHA-256 verification failed: {position.symbol}"
                    )
                    break

                qty = d(position.quantity, field="position.quantity")
                market_value = d(
                    position.market_value,
                    field="position.market_value",
                )
                unrealized = d(
                    position.unrealized_pnl,
                    field="position.unrealized_pnl",
                )
                realized = d(
                    position.realized_pnl,
                    field="position.realized_pnl",
                )

                if qty >= 0:
                    long_mv += market_value
                else:
                    short_mv_abs += abs(market_value)
                net_mv += market_value

                allocation = (
                    market_value / nlv if nlv != 0 else Decimal("0")
                )
                gross_contribution = (
                    abs(market_value) / nlv if nlv != 0 else Decimal("0")
                )
                net_contribution = (
                    market_value / nlv if nlv != 0 else Decimal("0")
                )
                core = {
                    "symbol": position.symbol.upper(),
                    "quantity": q_qty(qty),
                    "market_value": q_money(market_value),
                    "allocation": q_ratio(allocation),
                    "gross_exposure_contribution": q_ratio(
                        gross_contribution
                    ),
                    "net_exposure_contribution": q_ratio(
                        net_contribution
                    ),
                    "unrealized_pnl": q_money(unrealized),
                    "realized_pnl": q_money(realized),
                }
                allocations.append(
                    PositionAllocation(
                        **core,
                        allocation_sha256=canonical_hash(core),
                    )
                )

        daily_pnl = nlv - prior_nlv
        daily_return = (
            daily_pnl / prior_nlv if prior_nlv != 0 else Decimal("0")
        )
        cumulative_pnl = nlv - initial
        cumulative_return = (
            cumulative_pnl / initial if initial != 0 else Decimal("0")
        )
        cash_allocation = cash / nlv if nlv != 0 else Decimal("0")
        invested_allocation = (
            total_market_value / nlv if nlv != 0 else Decimal("0")
        )
        gross_exposure = (
            (long_mv + short_mv_abs) / nlv if nlv != 0 else Decimal("0")
        )
        net_exposure = net_mv / nlv if nlv != 0 else Decimal("0")
        leverage_ratio = gross_exposure
        buying_power = max(cash, Decimal("0")) * self.buying_power_multiplier

        if not reasons:
            self._append_ledger(
                snapshot_time=timestamp,
                reconciliation_sha256=reconciliation.reconciliation_sha256,
                nlv=nlv,
                daily_pnl=daily_pnl,
                cumulative_pnl=cumulative_pnl,
            )

        status = "PASS" if not reasons else "FAIL"
        decision = "snapshot" if not reasons else "reject"
        core = {
            "schema_version": "v50.0.paper_account_snapshot.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "snapshot_time": timestamp,
            "reconciliation_sha256": reconciliation.reconciliation_sha256,
            "cash_balance": q_money(cash),
            "buying_power": q_money(buying_power),
            "total_market_value": q_money(total_market_value),
            "net_liquidation_value": q_money(nlv),
            "prior_net_liquidation_value": q_money(prior_nlv),
            "daily_pnl": q_money(daily_pnl),
            "daily_return": q_ratio(daily_return),
            "cumulative_pnl": q_money(cumulative_pnl),
            "cumulative_return": q_ratio(cumulative_return),
            "cash_allocation": q_ratio(cash_allocation),
            "invested_allocation": q_ratio(invested_allocation),
            "gross_exposure": q_ratio(gross_exposure),
            "net_exposure": q_ratio(net_exposure),
            "leverage_ratio": q_ratio(leverage_ratio),
            "long_market_value": q_money(long_mv),
            "short_market_value": q_money(short_mv_abs),
            "position_count": len(allocations),
            "positions": [asdict(x) for x in allocations],
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return AccountSnapshotResult(
            **core,
            snapshot_sha256=canonical_hash(core),
        )

    @staticmethod
    def export(path: Path, result: AccountSnapshotResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v50.0.paper_account_snapshot_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_reconciliation(path: Path) -> ReconciliationInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("result", payload)
    return ReconciliationInput(**raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V50.0 Paper Account Snapshot & Daily P&L Foundation"
    )
    parser.add_argument(
        "--input",
        default=(
            "release/v49/audit/"
            "paper_portfolio_reconciliation_result_v49_0.json"
        ),
    )
    parser.add_argument("--snapshot-time", required=True)
    parser.add_argument("--prior-net-liquidation-value", required=True)
    parser.add_argument("--initial-equity", required=True)
    parser.add_argument("--buying-power-multiplier", default="1.0")
    parser.add_argument(
        "--mode",
        choices=["replay", "paper", "live"],
        default="paper",
    )
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument(
        "--output",
        default=(
            "release/v50/audit/"
            "paper_account_snapshot_result_v50_0.json"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        builder = PaperAccountSnapshotBuilder(
            mode=args.mode,
            enable_live=args.enable_live,
            buying_power_multiplier=args.buying_power_multiplier,
        )
        reconciliation = load_reconciliation(Path(args.input))
        result = builder.build(
            reconciliation,
            snapshot_time=args.snapshot_time,
            prior_net_liquidation_value=args.prior_net_liquidation_value,
            initial_equity=args.initial_equity,
        )
        builder.export(output, result)
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
            "schema_version": "v50.0.paper_account_snapshot_error.1",
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
