
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import math

CANONICAL_CLOSED = Path("runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl")
EXIT_LEDGER = Path("runtime/paper_full_auto_lifecycle/exit_ledger.jsonl")
POSITION_REGISTRY = Path("runtime/paper_full_auto_lifecycle/position_registry.json")
LATEST_LIFECYCLE = Path("runtime/paper_full_auto_lifecycle/latest_lifecycle_status.json")
SESSION_LEDGER = Path("runtime/paper_autonomous_daily_session/session_ledger.jsonl")


def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _read_jsonl(path: Path, max_rows=10000):
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_rows:]
    except Exception:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _read_json(path: Path):
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def normalize_canonical_trade(row, source):
    trade_id = str(row.get("trade_id") or "").strip()
    if not trade_id:
        return None

    realized_pl = _num(row.get("realized_pl"))

    return {
        "time": str(row.get("exit_time") or row.get("entry_time") or ""),
        "symbol": str(row.get("symbol") or "UNKNOWN").upper(),
        "side": str(row.get("side") or "LONG").upper(),
        "qty": _num(row.get("quantity")),
        "pnl": realized_pl,
        "reason": str(row.get("exit_reason") or "UNKNOWN"),
        "record_id": trade_id,
        "source": source,
        "entry_price": _num(row.get("entry_price")),
        "exit_price": _num(row.get("exit_price")),
        "entry_time": row.get("entry_time"),
        "exit_time": row.get("exit_time"),
        "realized_return": _num(row.get("realized_return")),
        "exit_order_id": str(row.get("exit_order_id") or ""),
        "paper_only": bool(row.get("paper_only", True)),
        "canonical_actual_round_trip": True,
        "normalization": {
            "pnl_recovered": realized_pl is not None,
            "pnl_path": "canonical.realized_pl",
            "pnl_key": "realized_pl",
            "identifiers": {
                "trade_id": [trade_id],
                "order_id": [str(row.get("exit_order_id"))] if row.get("exit_order_id") else [],
            },
        },
    }


def load_canonical_trades(root: Path):
    path = root / CANONICAL_CLOSED
    source = str(CANONICAL_CLOSED).replace("\\", "/")
    trades = []
    for row in _read_jsonl(path):
        trade = normalize_canonical_trade(row, source)
        if trade is not None:
            trades.append(trade)
    trades.sort(key=lambda item: item["time"])
    return trades


def build_lifecycle_discovery(root: Path):
    closed_path = root / CANONICAL_CLOSED
    exit_path = root / EXIT_LEDGER
    registry_path = root / POSITION_REGISTRY
    latest_path = root / LATEST_LIFECYCLE
    session_path = root / SESSION_LEDGER

    closed_rows = _read_jsonl(closed_path)
    exit_rows = _read_jsonl(exit_path)
    registry = _read_json(registry_path)
    latest = _read_json(latest_path)
    session_rows = _read_jsonl(session_path)
    canonical = load_canonical_trades(root)

    exit_by_id = {}
    for row in exit_rows:
        oid = str(row.get("order_id") or "").strip()
        if oid:
            exit_by_id[oid] = row

    matrix = []
    for trade in canonical:
        exit_order_id = str(trade.get("exit_order_id") or "")
        exit_submission = exit_by_id.get(exit_order_id) if exit_order_id else None
        matrix.append({
            "trade_id": trade["record_id"],
            "symbol": trade["symbol"],
            "entry_found": trade.get("entry_price") is not None,
            "entry_price": trade.get("entry_price"),
            "exit_found": trade.get("exit_price") is not None,
            "exit_price": trade.get("exit_price"),
            "quantity_found": trade.get("qty") is not None,
            "quantity": trade.get("qty"),
            "pnl_found": trade.get("pnl") is not None,
            "realized_pl": trade.get("pnl"),
            "exit_order_id": exit_order_id,
            "exit_submission_found": exit_submission is not None,
            "exit_reason": trade.get("reason"),
            "entry_time": trade.get("entry_time"),
            "exit_time": trade.get("exit_time"),
        })

    positions = registry.get("positions", {}) if isinstance(registry.get("positions", {}), dict) else {}
    stage_counts = Counter(str(row.get("stage") or "UNKNOWN") for row in session_rows)
    numeric_pnl_count = sum(1 for trade in canonical if trade.get("pnl") is not None)

    return {
        "canonical_paths": {
            "closed_round_trips": str(CANONICAL_CLOSED).replace("\\", "/"),
            "exit_ledger": str(EXIT_LEDGER).replace("\\", "/"),
            "position_registry": str(POSITION_REGISTRY).replace("\\", "/"),
            "latest_lifecycle": str(LATEST_LIFECYCLE).replace("\\", "/"),
            "session_ledger": str(SESSION_LEDGER).replace("\\", "/"),
        },
        "existence": {
            "closed_round_trips": closed_path.exists(),
            "exit_ledger": exit_path.exists(),
            "position_registry": registry_path.exists(),
            "latest_lifecycle": latest_path.exists(),
            "session_ledger": session_path.exists(),
        },
        "counts": {
            "canonical_closed_round_trip_rows": len(closed_rows),
            "normalized_canonical_trade_count": len(canonical),
            "canonical_numeric_pnl_count": numeric_pnl_count,
            "exit_submission_rows": len(exit_rows),
            "open_registry_position_count": len(positions),
            "session_ledger_rows": len(session_rows),
        },
        "lifecycle_matrix": matrix,
        "session_stage_counts": dict(stage_counts),
        "latest_lifecycle_status": latest.get("status"),
        "latest_lifecycle_action_count": latest.get("action_count"),
        "source_of_truth": "runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl",
        "status": (
            "PASS_CANONICAL_PNL_AVAILABLE"
            if numeric_pnl_count > 0
            else ("PASS_CANONICAL_EMPTY" if len(canonical) == 0 else "PASS_CANONICAL_TRADES_WITHOUT_PNL")
        ),
        "contracts": {
            "source_files_modified": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "duplicate_engine_created": False,
        },
    }
