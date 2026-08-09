
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import json

TIME_KEYS = (
    "timestamp_utc", "generated_at_utc", "timestamp",
    "time", "checkpoint_et", "created_at", "updated_at",
)
EQUITY_KEYS = ("equity", "portfolio_value", "account_equity")
PNL_KEYS = ("realized_pnl", "daily_pnl", "pnl", "profit_loss", "net_pnl")


def _number(value):
    try:
        return float(value)
    except Exception:
        return None


def _first_nested(obj, keys):
    wanted = {key.lower() for key in keys}
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in wanted and value is not None:
                return value
        for value in obj.values():
            result = _first_nested(value, keys)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for value in obj[:100]:
            result = _first_nested(value, keys)
            if result is not None:
                return result
    return None


def _read_jsonl_tail(path: Path, max_rows=1200):
    if not path.exists():
        return []
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()[-max_rows:]
    except Exception:
        return []

    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _candidate_files(root: Path):
    runtime = root / "runtime"
    if not runtime.exists():
        return []

    selected = []
    tokens = (
        "account", "portfolio", "snapshot", "metrics",
        "ledger", "position", "paper",
    )

    for path in runtime.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        if not any(token in path.name.lower() for token in tokens):
            continue
        try:
            selected.append((path.stat().st_mtime, path))
        except Exception:
            pass

    return [path for _, path in sorted(selected, reverse=True)[:160]]


def _iter_records(root: Path):
    for path in _candidate_files(root):
        if path.suffix.lower() == ".jsonl":
            records = _read_jsonl_tail(path)
        else:
            obj = _read_json(path)
            records = [obj] if obj is not None else []

        for record in records:
            if isinstance(record, dict):
                yield record


def _extract_history(root: Path):
    equity_points = []
    pnl_points = []
    seen_equity = set()
    seen_pnl = set()

    for record in _iter_records(root):
        timestamp = _first_nested(record, TIME_KEYS)
        if timestamp is None:
            continue
        timestamp = str(timestamp)

        equity = _number(_first_nested(record, EQUITY_KEYS))
        if equity is not None:
            key = (timestamp, round(equity, 8))
            if key not in seen_equity:
                seen_equity.add(key)
                equity_points.append({"time": timestamp, "value": equity})

        pnl = _number(_first_nested(record, PNL_KEYS))
        if pnl is not None:
            key = (timestamp, round(pnl, 8))
            if key not in seen_pnl:
                seen_pnl.add(key)
                pnl_points.append({"time": timestamp, "value": pnl})

    equity_points.sort(key=lambda item: item["time"])
    pnl_points.sort(key=lambda item: item["time"])
    return equity_points[-120:], pnl_points[-120:]


def _daily_realized_from_timeline(timeline):
    daily = defaultdict(float)
    numeric_count = 0

    for row in timeline or []:
        if "CLOSED_TRADE" not in str(row.get("event", "")).upper():
            continue

        value = _number(row.get("pnl"))
        if value is None:
            continue

        date = str(row.get("time") or "")[:10]
        if not date:
            continue

        daily[date] += value
        numeric_count += 1

    return (
        [{"date": date, "value": daily[date]} for date in sorted(daily)],
        numeric_count,
    )


def _position_allocation(positions):
    raw = []

    for position in positions or []:
        symbol = str(position.get("symbol") or "")
        if not symbol:
            continue

        market_value = _number(position.get("market_value"))
        if market_value is None:
            qty = _number(position.get("qty"))
            avg = _number(position.get("avg_entry_price"))
            if qty is not None and avg is not None:
                market_value = qty * avg

        if market_value is None:
            continue

        raw.append({"symbol": symbol, "value": abs(market_value)})

    total = sum(item["value"] for item in raw)
    if total <= 0:
        return []

    return [
        {
            "symbol": item["symbol"],
            "value": item["value"],
            "weight": item["value"] / total,
        }
        for item in raw
    ]


def build_visualization(root: Path, status_payload):
    equity_history, generic_pnl_history = _extract_history(root)

    account = status_payload.get("account") or {}
    current_equity = _number(account.get("equity"))

    if current_equity is not None:
        current_stamp = str(status_payload.get("generated_at_utc") or "")
        if not equity_history or equity_history[-1]["value"] != current_equity:
            equity_history.append({"time": current_stamp, "value": current_equity})

    daily_realized, closed_trade_numeric_count = _daily_realized_from_timeline(
        status_payload.get("timeline") or []
    )

    positions = status_payload.get("positions") or []
    allocation = _position_allocation(positions)

    unrealized_values = [
        _number(position.get("unrealized_pl"))
        for position in positions
    ]
    total_unrealized = sum(
        value for value in unrealized_values
        if value is not None
    )

    two_week = status_payload.get("two_week") or {}
    completed = int(two_week.get("completed_days", 0) or 0)
    required = int(two_week.get("required_days", 10) or 10)

    validation_slots = [
        {"day": index + 1, "completed": index < completed}
        for index in range(required)
    ]

    return {
        "equity_history": equity_history[-120:],
        "daily_realized_pnl": daily_realized[-30:],
        "generic_pnl_history": generic_pnl_history[-120:],
        "position_allocation": allocation,
        "validation_slots": validation_slots,
        "summary": {
            "current_equity": current_equity,
            "current_unrealized_pnl": total_unrealized,
            "historical_realized_pnl": (
                status_payload.get("performance") or {}
            ).get("historical_realized_pnl"),
            "equity_point_count": len(equity_history),
            "daily_realized_point_count": len(daily_realized),
            "closed_trade_numeric_pnl_count": closed_trade_numeric_count,
        },
        "contracts": {
            "read_only": True,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "production_parameter_modified": False,
        },
    }
