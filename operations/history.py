from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line in path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except Exception:
            continue
    return result


def order_history(root: Path) -> list[dict[str, Any]]:
    return read_jsonl(
        root / "release/p1_broker_consolidation/actual/"
               "order_ledger.jsonl"
    )


def fill_history(root: Path) -> list[dict[str, Any]]:
    return read_jsonl(
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "actual_fill_ledger.jsonl"
    )


def position_history(root: Path) -> list[dict[str, Any]]:
    records = read_jsonl(
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "position_history.jsonl"
    )
    if records:
        return records

    validation_path = (
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "p3_actual_validation.json"
    )
    if not validation_path.exists():
        return []
    value = json.loads(
        validation_path.read_text(encoding="utf-8-sig")
    )
    observed_at = value.get("observed_at")
    return [
        {
            "observed_at": observed_at,
            **position,
        }
        for position in value.get("positions", [])
    ]


def performance_summary(root: Path) -> dict[str, Any]:
    fills = fill_history(root)
    realized_values = []
    for record in fills:
        value = (
            record.get("realized_pl")
            or record.get("realized_pnl")
        )
        if value is not None:
            try:
                realized_values.append(Decimal(str(value)))
            except Exception:
                pass

    wins = [value for value in realized_values if value > 0]
    losses = [value for value in realized_values if value < 0]
    total = sum(realized_values, Decimal("0"))

    equity_points = []
    for record in read_jsonl(
        root / "release/operations_bundle/actual/"
               "equity_history.jsonl"
    ):
        try:
            equity_points.append(Decimal(str(record["equity"])))
        except Exception:
            pass

    peak = None
    maximum_drawdown = Decimal("0")
    for equity in equity_points:
        peak = equity if peak is None else max(peak, equity)
        if peak and peak > 0:
            drawdown = (peak - equity) / peak
            maximum_drawdown = max(maximum_drawdown, drawdown)

    return {
        "realized_pnl": str(total),
        "trade_count_with_realized_pnl": len(realized_values),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": (
            len(wins) / len(realized_values)
            if realized_values else 0.0
        ),
        "average_profit": str(
            sum(wins, Decimal("0")) / len(wins)
            if wins else Decimal("0")
        ),
        "average_loss": str(
            sum(losses, Decimal("0")) / len(losses)
            if losses else Decimal("0")
        ),
        "maximum_drawdown": str(maximum_drawdown),
        "equity_point_count": len(equity_points),
    }
