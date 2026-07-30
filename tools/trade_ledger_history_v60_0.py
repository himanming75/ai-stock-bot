#!/usr/bin/env python3
"""V60.1 Trade Ledger & History Foundation with Duplicate Execution Protection.

Consumes a V59 portfolio-update integration result and a prior trade-history
state, then appends a deterministic trade event. It links entries and exits,
tracks realized P&L, win/loss statistics, profit factor, expectancy, CSV export,
and SHA-256 ledger integrity.

Offline only:
- no broker connection
- no market-data request
- no network use
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Sequence

VERSION = "60.1"
MONEY_Q = Decimal("0.0001")
QTY_Q = Decimal("0.000001")
RATIO_Q = Decimal("0.000001")


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
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    return parsed


def q_money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def q_qty(value: Decimal) -> str:
    value = value.quantize(QTY_Q, rounding=ROUND_HALF_UP)
    text = format(value, "f").rstrip("0").rstrip(".")
    return text or "0"


def q_ratio(value: Decimal) -> str:
    return format(value.quantize(RATIO_Q, rounding=ROUND_HALF_UP), "f")


def parse_time(value: str, *, field: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


def unwrap(data: dict[str, Any]) -> dict[str, Any]:
    result = data.get("result", data)
    if not isinstance(result, dict):
        raise ValueError("result must be an object")
    return result


class TradeLedgerHistoryV600:
    def __init__(self, *, mode: str = "paper", enable_live: bool = False) -> None:
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live trade-history transport is intentionally not implemented in V60.1"
            )

    @staticmethod
    def _validate_prior_history(state: dict[str, Any]) -> None:
        if state.get("network_used") is True:
            raise ValueError("history state network_used must be false")
        trades = state.get("trades", [])
        if not isinstance(trades, list):
            raise ValueError("trades must be a list")
        ids: set[str] = set()
        for item in trades:
            if not isinstance(item, dict):
                raise ValueError("each trade must be an object")
            trade_id = str(item.get("trade_id", "")).strip()
            if not trade_id or trade_id in ids:
                raise ValueError("trade IDs must be unique and non-empty")
            ids.add(trade_id)

    def update(
        self,
        v59_raw: dict[str, Any],
        history_raw: dict[str, Any],
        *,
        event_time: str,
    ) -> dict[str, Any]:
        self._live_gate()
        v59 = unwrap(v59_raw)
        history = deepcopy(unwrap(history_raw))
        self._validate_prior_history(history)

        if v59.get("network_used") is True:
            raise ValueError("V59 network_used must be false")
        if v59.get("status") != "PASS":
            raise ValueError("V59 status must be PASS")

        rec = v59.get("reconciliation")
        if not isinstance(rec, dict):
            raise ValueError("V59 reconciliation is required")
        ledger = rec.get("ledger")
        if not isinstance(ledger, list) or not ledger:
            raise ValueError("V59 reconciliation ledger is required")
        event = ledger[-1]

        symbol = str(event.get("symbol", "")).strip().upper()
        action = str(event.get("action", "")).strip().upper()
        event_type = str(event.get("event_type", "")).strip()
        if not symbol:
            raise ValueError("symbol is required")
        if action not in {"BUY", "SELL"}:
            raise ValueError("action must be BUY or SELL")
        if event_type not in {
            "POSITION_OPENED",
            "POSITION_INCREASED",
            "POSITION_REDUCED",
            "POSITION_CLOSED",
        }:
            raise ValueError("unsupported position event type")

        quantity = d(event.get("quantity"), field="quantity")
        price = d(event.get("price"), field="price")
        commission = d(event.get("commission", "0"), field="commission")
        realized_delta = d(
            event.get("realized_pnl_delta", "0"),
            field="realized_pnl_delta",
        )
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        if commission < 0:
            raise ValueError("commission must be non-negative")

        timestamp = parse_time(event_time, field="event_time")
        existing_trades = deepcopy(history.get("trades", []))
        open_lots = deepcopy(history.get("open_lots", []))
        if not isinstance(open_lots, list):
            raise ValueError("open_lots must be a list")

        sequence = len(existing_trades) + 1
        execution_sha = str(v59.get("execution_sha256", ""))
        if len(execution_sha) != 64:
            raise ValueError("execution_sha256 must be 64 characters")

        integration_sha = str(v59.get("integration_sha256", ""))
        if len(integration_sha) != 64:
            raise ValueError("integration_sha256 must be 64 characters")

        duplicate_execution = any(
            str(item.get("execution_sha256", "")) == execution_sha
            for item in existing_trades
        )
        if duplicate_execution:
            raise ValueError(
                f"duplicate execution_sha256 rejected: {execution_sha}"
            )

        duplicate_integration = any(
            str(item.get("v59_integration_sha256", "")) == integration_sha
            for item in existing_trades
        )
        if duplicate_integration:
            raise ValueError(
                f"duplicate v59_integration_sha256 rejected: {integration_sha}"
            )

        event_core = {
            "sequence": sequence,
            "event_time": timestamp,
            "symbol": symbol,
            "action": action,
            "event_type": event_type,
            "quantity": q_qty(quantity),
            "price": q_money(price),
            "gross_notional": q_money(quantity * price),
            "commission": q_money(commission),
            "realized_pnl_delta": q_money(realized_delta),
            "execution_sha256": execution_sha,
            "v59_integration_sha256": integration_sha,
        }
        trade_id = "TRD-" + canonical_hash(event_core)[:20].upper()
        event_core["trade_id"] = trade_id

        if action == "BUY":
            lot_core = {
                "lot_id": "LOT-" + canonical_hash(
                    {
                        "trade_id": trade_id,
                        "symbol": symbol,
                        "quantity": q_qty(quantity),
                        "price": q_money(price),
                    }
                )[:20].upper(),
                "symbol": symbol,
                "opened_trade_id": trade_id,
                "opened_at": timestamp,
                "original_quantity": q_qty(quantity),
                "remaining_quantity": q_qty(quantity),
                "entry_price": q_money(price),
                "entry_commission": q_money(commission),
                "lot_sha256": "",
            }
            lot_hash_payload = {k: v for k, v in lot_core.items() if k != "lot_sha256"}
            lot_core["lot_sha256"] = canonical_hash(lot_hash_payload)
            open_lots.append(lot_core)
            event_core.update(
                {
                    "matched_lot_ids": [],
                    "closed_quantity": "0",
                    "average_entry_price": None,
                    "holding_period_seconds": None,
                    "trade_outcome": "OPEN",
                }
            )
        else:
            remaining = quantity
            matched_ids: list[str] = []
            weighted_entry = Decimal("0")
            latest_open: datetime | None = None
            new_lots: list[dict[str, Any]] = []

            for lot in open_lots:
                if lot.get("symbol") != symbol or remaining <= 0:
                    new_lots.append(lot)
                    continue
                lot_remaining = d(
                    lot.get("remaining_quantity"),
                    field="lot remaining_quantity",
                )
                if lot_remaining <= 0:
                    raise ValueError("open lot remaining_quantity must be positive")

                matched = min(remaining, lot_remaining)
                weighted_entry += matched * d(
                    lot.get("entry_price"),
                    field="lot entry_price",
                )
                matched_ids.append(str(lot.get("lot_id")))
                opened_at = datetime.fromisoformat(
                    str(lot.get("opened_at")).replace("Z", "+00:00")
                )
                if latest_open is None or opened_at > latest_open:
                    latest_open = opened_at

                lot_remaining -= matched
                remaining -= matched
                if lot_remaining > 0:
                    updated = deepcopy(lot)
                    updated["remaining_quantity"] = q_qty(lot_remaining)
                    lot_hash_payload = {
                        k: v for k, v in updated.items() if k != "lot_sha256"
                    }
                    updated["lot_sha256"] = canonical_hash(lot_hash_payload)
                    new_lots.append(updated)

            if remaining > 0:
                raise ValueError("sell quantity exceeds tracked open lots")
            open_lots = new_lots

            avg_entry = weighted_entry / quantity
            close_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            holding_seconds = (
                int((close_dt - latest_open).total_seconds())
                if latest_open is not None
                else 0
            )
            if holding_seconds < 0:
                raise ValueError("event_time cannot precede lot open time")

            if realized_delta > 0:
                outcome = "WIN"
            elif realized_delta < 0:
                outcome = "LOSS"
            else:
                outcome = "BREAKEVEN"

            event_core.update(
                {
                    "matched_lot_ids": matched_ids,
                    "closed_quantity": q_qty(quantity),
                    "average_entry_price": q_money(avg_entry),
                    "holding_period_seconds": holding_seconds,
                    "trade_outcome": outcome,
                }
            )

        prior_entry_hash = (
            str(existing_trades[-1].get("entry_sha256"))
            if existing_trades
            else "GENESIS"
        )
        payload_sha = canonical_hash(event_core)
        ledger_entry_core = {
            **event_core,
            "previous_entry_sha256": prior_entry_hash,
            "payload_sha256": payload_sha,
        }
        ledger_entry = {
            **ledger_entry_core,
            "entry_sha256": canonical_hash(ledger_entry_core),
        }
        existing_trades.append(ledger_entry)

        closed = [
            item
            for item in existing_trades
            if item.get("action") == "SELL"
        ]
        wins = [item for item in closed if item.get("trade_outcome") == "WIN"]
        losses = [item for item in closed if item.get("trade_outcome") == "LOSS"]
        breakeven = [
            item for item in closed if item.get("trade_outcome") == "BREAKEVEN"
        ]

        gross_profit = sum(
            (
                d(item.get("realized_pnl_delta", "0"), field="realized P&L")
                for item in wins
            ),
            Decimal("0"),
        )
        gross_loss_abs = abs(
            sum(
                (
                    d(item.get("realized_pnl_delta", "0"), field="realized P&L")
                    for item in losses
                ),
                Decimal("0"),
            )
        )
        total_realized = gross_profit - gross_loss_abs
        closed_count = len(closed)
        win_rate = (
            Decimal(len(wins)) / Decimal(closed_count)
            if closed_count
            else Decimal("0")
        )
        avg_win = (
            gross_profit / Decimal(len(wins))
            if wins
            else Decimal("0")
        )
        avg_loss = (
            gross_loss_abs / Decimal(len(losses))
            if losses
            else Decimal("0")
        )
        expectancy = (
            total_realized / Decimal(closed_count)
            if closed_count
            else Decimal("0")
        )
        profit_factor = (
            q_ratio(gross_profit / gross_loss_abs)
            if gross_loss_abs > 0
            else ("INF" if gross_profit > 0 else "0.000000")
        )

        stats_core = {
            "event_count": len(existing_trades),
            "buy_event_count": sum(
                1 for item in existing_trades if item.get("action") == "BUY"
            ),
            "sell_event_count": closed_count,
            "win_count": len(wins),
            "loss_count": len(losses),
            "breakeven_count": len(breakeven),
            "win_rate": q_ratio(win_rate),
            "gross_profit": q_money(gross_profit),
            "gross_loss": q_money(gross_loss_abs),
            "net_realized_pnl": q_money(total_realized),
            "average_win": q_money(avg_win),
            "average_loss": q_money(avg_loss),
            "profit_factor": profit_factor,
            "expectancy": q_money(expectancy),
            "open_lot_count": len(open_lots),
        }
        stats = {
            **stats_core,
            "statistics_sha256": canonical_hash(stats_core),
        }

        result_core = {
            "schema_version": "v60.0.trade_ledger_history.1",
            "version": VERSION,
            "status": "PASS",
            "decision": "trade_history_updated",
            "latest_trade_id": trade_id,
            "trade_count": len(existing_trades),
            "open_lot_count": len(open_lots),
            "trades": existing_trades,
            "open_lots": open_lots,
            "statistics": stats,
            "rejection_reasons": [],
            "network_used": False,
        }
        return {
            **result_core,
            "history_sha256": canonical_hash(result_core),
        }


def write_csv(path: Path, trades: list[dict[str, Any]]) -> None:
    fields = [
        "sequence",
        "trade_id",
        "event_time",
        "symbol",
        "action",
        "event_type",
        "quantity",
        "price",
        "gross_notional",
        "commission",
        "realized_pnl_delta",
        "trade_outcome",
        "closed_quantity",
        "average_entry_price",
        "holding_period_seconds",
        "execution_sha256",
        "entry_sha256",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for trade in trades:
            writer.writerow(trade)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V60.1 Trade Ledger & History Duplicate Protection"
    )
    parser.add_argument("--input", required=True, help="V59 result JSON")
    parser.add_argument("--history-state", required=True)
    parser.add_argument("--event-time", required=True)
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--csv-output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        result = TradeLedgerHistoryV600(
            mode=args.mode,
            enable_live=args.enable_live,
        ).update(
            load_json(Path(args.input)),
            load_json(Path(args.history_state)),
            event_time=args.event_time,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if args.csv_output:
            write_csv(Path(args.csv_output), result["trades"])
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (
        OSError,
        ValueError,
        PermissionError,
        NotImplementedError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        error = {
            "schema_version": "v60.0.trade_ledger_history_error.1",
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
