from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import math

EVENT_KEYS = ("event_type", "event", "stage", "type")
TIME_KEYS = ("timestamp_utc", "generated_at_utc", "timestamp", "time", "checkpoint_et", "created_at")
SYMBOL_KEYS = ("symbol", "ticker")
SIDE_KEYS = ("side", "action")
QTY_KEYS = ("qty", "quantity")
PNL_KEYS = ("realized_pnl", "pnl", "profit_loss", "net_pnl", "net_profit", "realized_pl")
REASON_KEYS = ("exit_reason", "reason", "close_reason")
ID_KEYS = ("trade_id", "position_id", "order_id", "event_id", "id")


def _first(record, keys):
    if not isinstance(record, dict):
        return None
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _read_jsonl(path: Path, max_rows=5000):
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


def _candidate_ledgers(root: Path):
    runtime = root / "runtime"
    if not runtime.exists():
        return []
    candidates = []
    for path in runtime.rglob("*.jsonl"):
        name = path.name.lower()
        if not any(token in name for token in ("ledger", "trade", "order", "session", "position")):
            continue
        try:
            candidates.append((path.stat().st_mtime, path))
        except Exception:
            pass
    return [path for _, path in sorted(candidates, reverse=True)[:180]]


def _load_v3_6_normalizer(root: Path):
    import importlib.util

    module_path = root / "dashboard" / "trade_ledger_normalizer_v3_6.py"

    spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_trade_ledger_normalizer_v3_6",
        module_path,
    )

    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"Unable to load V3.6 normalizer: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_closed_trades(root: Path):
    rows, sources, seen = [], [], set()
    normalizer = _load_v3_6_normalizer(root)

    import importlib.util
    canonical_path = root / "dashboard" / "canonical_lifecycle_source_v3_8.py"
    canonical_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_canonical_lifecycle_v3_8",
        canonical_path,
    )
    if canonical_spec is None or canonical_spec.loader is None:
        raise ModuleNotFoundError(str(canonical_path))
    canonical_module = importlib.util.module_from_spec(canonical_spec)
    canonical_spec.loader.exec_module(canonical_module)
    canonical_trades = canonical_module.load_canonical_trades(root)

    for trade in canonical_trades:
        key = ("CANONICAL", trade.get("record_id"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(trade)

    if canonical_trades:
        sources.append("runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl")

    for path in _candidate_ledgers(root):
        rel = str(path.relative_to(root)).replace("\\", "/")
        source_used = False

        for record in _read_jsonl(path):
            trade = normalizer.normalize_closed_trade(record, rel)
            if trade is None:
                continue
            if trade["record_id"]:
                key = (trade["record_id"], trade["time"], trade["symbol"], trade["pnl"])
            else:
                key = (trade["time"], trade["symbol"], trade["qty"], trade["pnl"], trade["reason"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(trade)
            source_used = True
        if source_used:
            sources.append(rel)
    canonical_rows = [
        row for row in rows
        if row.get("canonical_actual_round_trip")
    ]

    if canonical_rows:
        rows = canonical_rows
        sources = [
            "runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl"
        ]

    rows.sort(key=lambda x: x["time"])
    import importlib.util
    reconstruction_path = root / "dashboard" / "cross_ledger_trade_reconstruction_v3_7.py"
    spec = importlib.util.spec_from_file_location("ai_stock_bot_cross_ledger_v3_7", reconstruction_path)
    if spec is None or spec.loader is None: raise ModuleNotFoundError(str(reconstruction_path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rows, audit = module.reconstruct_missing_pnl(root, rows)
    collect_closed_trades.last_reconstruction_audit = audit
    return rows, sorted(set(sources))


def _stats(trades):
    numeric = [t for t in trades if t["pnl"] is not None]
    pnls = [t["pnl"] for t in numeric]
    wins = [v for v in pnls if v > 0]
    losses = [v for v in pnls if v < 0]
    breakeven = [v for v in pnls if v == 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = "INF"
    else:
        pf = None
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    cumulative = []
    for trade in numeric:
        equity += trade["pnl"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        cumulative.append({"time": trade["time"], "value": equity})
    return {
        "observed_closed_trade_count": len(trades),
        "numeric_trade_count": len(numeric),
        "win_count": len(wins),
        "loss_count": len(losses),
        "breakeven_count": len(breakeven),
        "win_rate": len(wins) / len(pnls) if pnls else None,
        "net_realized_pnl": sum(pnls) if pnls else None,
        "gross_profit": gross_profit if pnls else None,
        "gross_loss": gross_loss if pnls else None,
        "profit_factor": pf,
        "average_trade": sum(pnls) / len(pnls) if pnls else None,
        "average_win": sum(wins) / len(wins) if wins else None,
        "average_loss": sum(losses) / len(losses) if losses else None,
        "best_trade": max(pnls) if pnls else None,
        "worst_trade": min(pnls) if pnls else None,
        "max_realized_drawdown": max_dd if pnls else None,
        "cumulative_realized_pnl": cumulative,
        "data_status": "PASS" if pnls else "INSUFFICIENT_DATA",
    }


def _group_stats(trades, key_name):
    grouped = defaultdict(list)
    for trade in trades:
        grouped[str(trade.get(key_name) or "UNKNOWN")].append(trade)
    result = []
    for name, rows in grouped.items():
        s = _stats(rows)
        result.append({
            "name": name,
            "observed_closed_trade_count": s["observed_closed_trade_count"],
            "numeric_trade_count": s["numeric_trade_count"],
            "net_realized_pnl": s["net_realized_pnl"],
            "win_rate": s["win_rate"],
            "profit_factor": s["profit_factor"],
            "average_trade": s["average_trade"],
        })
    result.sort(key=lambda x: (x["net_realized_pnl"] is not None, x["net_realized_pnl"] if x["net_realized_pnl"] is not None else -1e30), reverse=True)
    return result


def _daily(trades):
    grouped = defaultdict(list)
    for trade in trades:
        date = str(trade.get("time") or "")[:10]
        if date:
            grouped[date].append(trade)
    result = []
    for date in sorted(grouped):
        s = _stats(grouped[date])
        result.append({"date": date, "observed_closed_trade_count": s["observed_closed_trade_count"], "numeric_trade_count": s["numeric_trade_count"], "net_realized_pnl": s["net_realized_pnl"]})
    return result


def build_trade_analytics(root: Path, status_payload):
    trades, sources = collect_closed_trades(root)
    validation_start = (status_payload.get("two_week") or {}).get("start_date")
    historical = _stats(trades)
    if validation_start:
        validation_trades = [t for t in trades if str(t.get("time") or "")[:10] >= str(validation_start)]
        validation = _stats(validation_trades)
        validation_status = validation["data_status"]
    else:
        validation = _stats([])
        validation_status = "WAITING_FOR_VALIDATION_START"
    numeric = [t for t in trades if t["pnl"] is not None]
    normalizer = _load_v3_6_normalizer(root)
    recovery_audit = normalizer.build_recovery_audit(trades)

    import importlib.util
    lifecycle_path = root / "dashboard" / "canonical_lifecycle_source_v3_8.py"
    lifecycle_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_canonical_lifecycle_v3_8_status",
        lifecycle_path,
    )
    if lifecycle_spec is None or lifecycle_spec.loader is None:
        raise ModuleNotFoundError(str(lifecycle_path))
    lifecycle_module = importlib.util.module_from_spec(lifecycle_spec)
    lifecycle_spec.loader.exec_module(lifecycle_module)
    lifecycle_discovery = lifecycle_module.build_lifecycle_discovery(root)

    reconstruction_audit = getattr(collect_closed_trades, "last_reconstruction_audit", {"status":"NOT_RUN"})

    import importlib.util
    diagnostics_path = root / "dashboard" / "performance_diagnostics_v3_11.py"
    diagnostics_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_performance_diagnostics_v3_11",
        diagnostics_path,
    )
    if diagnostics_spec is None or diagnostics_spec.loader is None:
        raise ModuleNotFoundError(str(diagnostics_path))
    diagnostics_module = importlib.util.module_from_spec(diagnostics_spec)
    diagnostics_spec.loader.exec_module(diagnostics_module)
    diagnostics = diagnostics_module.build_performance_diagnostics(
        list(reversed(numeric[-500:]))
    )

    readiness_path = root / "dashboard" / "strategy_readiness_v3_12.py"
    readiness_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_strategy_readiness_v3_12",
        readiness_path,
    )
    if readiness_spec is None or readiness_spec.loader is None:
        raise ModuleNotFoundError(str(readiness_path))
    readiness_module = importlib.util.module_from_spec(readiness_spec)
    readiness_spec.loader.exec_module(readiness_module)
    readiness = readiness_module.build_strategy_readiness({
        "historical": historical,
        "performance_diagnostics": diagnostics,
    })

    return {
        "status": historical["data_status"],
        "historical": historical,
        "recovery_audit": recovery_audit,
        "cross_ledger_reconstruction": reconstruction_audit,
        "canonical_lifecycle_discovery": lifecycle_discovery,
        "validation": {**validation, "data_status": validation_status, "start_date": validation_start},
        "by_symbol": _group_stats(trades, "symbol"),
        "by_exit_reason": _group_stats(trades, "reason"),
        "daily": _daily(trades),
        "recent_numeric_trades": list(reversed(numeric[-20:])),
        "trade_details": list(reversed(numeric[-500:])),
        "trade_detail_contract": {
            "canonical_source_only_when_available": True,
            "max_rows": 500,
            "read_only": True,
        },
        "performance_diagnostics": diagnostics,
        "strategy_readiness": readiness,
        "source_ledgers": sources,
        "contracts": {"read_only": True, "broker_network_used": False, "broker_write_performed": False, "order_submission_performed": False, "paper_runtime_modified": False, "production_parameter_modified": False, "production_selector_modified": False, "duplicate_engine_created": False},
    }
