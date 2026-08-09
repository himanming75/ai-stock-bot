
from __future__ import annotations

from collections import Counter
import math

PNL_KEYS = {
    "realized_pnl", "realized_pl", "realized_profit_loss",
    "realized_profit", "net_realized_pnl", "net_pnl",
    "pnl", "profit_loss", "net_profit",
}
EVENT_KEYS = {"event_type", "event", "stage", "type"}
TIME_KEYS = {
    "timestamp_utc", "generated_at_utc", "timestamp", "time",
    "checkpoint_et", "created_at", "closed_at", "exit_time",
}
SYMBOL_KEYS = {"symbol", "ticker"}
SIDE_KEYS = {"side", "action", "position_side"}
QTY_KEYS = {"qty", "quantity", "filled_qty", "closed_qty"}
REASON_KEYS = {"exit_reason", "reason", "close_reason"}
ID_KEYS = {"trade_id", "position_id", "order_id", "event_id", "id"}
MAX_DEPTH = 8


def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _walk(obj, path="", depth=0):
    if depth > MAX_DEPTH:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{path}.{key}" if path else str(key)
            yield current, str(key), value
            if isinstance(value, (dict, list)):
                yield from _walk(value, current, depth + 1)

    elif isinstance(obj, list):
        for index, value in enumerate(obj[:200]):
            current = f"{path}[{index}]"
            if isinstance(value, (dict, list)):
                yield from _walk(value, current, depth + 1)


def find_first(record, keys):
    wanted = {key.lower() for key in keys}

    if isinstance(record, dict):
        for key, value in record.items():
            if key.lower() in wanted and value is not None:
                return value, key

    for path, key, value in _walk(record):
        if key.lower() in wanted and value is not None:
            return value, path

    return None, None


def collect_identifier_values(record):
    wanted={"order_id","client_order_id","trade_id","position_id","parent_order_id","execution_id","fill_id"}
    result={}
    for path,key,value in _walk(record):
        normalized=key.lower()
        if normalized not in wanted or value is None: continue
        s=str(value).strip()
        if s: result.setdefault(normalized,set()).add(s)
    return {k:sorted(v) for k,v in result.items()}


def find_numeric_pnl(record):
    priority = {
        "realized_pnl": 0,
        "realized_pl": 0,
        "realized_profit_loss": 0,
        "net_realized_pnl": 0,
        "realized_profit": 1,
        "net_pnl": 2,
        "pnl": 3,
        "profit_loss": 3,
        "net_profit": 3,
    }
    candidates = []

    for path, key, value in _walk(record):
        normalized = key.lower()
        if normalized not in PNL_KEYS:
            continue

        numeric = _num(value)
        if numeric is None:
            continue

        candidates.append(
            (
                priority.get(normalized, 99),
                path.count(".") + path.count("["),
                path,
                normalized,
                numeric,
            )
        )

    if not candidates:
        return None, None, None

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    _, _, path, key, value = candidates[0]
    return value, path, key


def normalize_closed_trade(record, source):
    event, event_path = find_first(record, EVENT_KEYS)

    if "CLOSED_TRADE" not in str(event or "").upper():
        return None

    pnl, pnl_path, pnl_key = find_numeric_pnl(record)

    time_value, time_path = find_first(record, TIME_KEYS)
    symbol, symbol_path = find_first(record, SYMBOL_KEYS)
    side, side_path = find_first(record, SIDE_KEYS)
    qty, qty_path = find_first(record, QTY_KEYS)
    reason, reason_path = find_first(record, REASON_KEYS)
    record_id, id_path = find_first(record, ID_KEYS)

    return {
        "time": str(time_value or ""),
        "symbol": str(symbol or "UNKNOWN"),
        "side": str(side or ""),
        "qty": _num(qty),
        "pnl": pnl,
        "reason": str(reason or "UNKNOWN"),
        "record_id": str(record_id or ""),
        "source": source,
        "normalization": {
            "event_path": event_path,
            "time_path": time_path,
            "symbol_path": symbol_path,
            "side_path": side_path,
            "qty_path": qty_path,
            "reason_path": reason_path,
            "id_path": id_path,
            "pnl_path": pnl_path,
            "pnl_key": pnl_key,
            "pnl_recovered": pnl is not None,
            "identifiers": collect_identifier_values(record),
        },
    }


def build_recovery_audit(trades):
    path_counts = Counter()
    key_counts = Counter()
    recovered = 0
    missing = 0
    samples = []

    for trade in trades:
        normalization = trade.get("normalization") or {}

        if trade.get("pnl") is None:
            missing += 1
        else:
            recovered += 1
            if normalization.get("pnl_path"):
                path_counts[normalization["pnl_path"]] += 1
            if normalization.get("pnl_key"):
                key_counts[normalization["pnl_key"]] += 1

        if len(samples) < 20:
            samples.append({
                "time": trade.get("time"),
                "symbol": trade.get("symbol"),
                "pnl": trade.get("pnl"),
                "pnl_path": normalization.get("pnl_path"),
                "source": trade.get("source"),
            })

    return {
        "observed_closed_trade_count": len(trades),
        "numeric_pnl_recovered_count": recovered,
        "numeric_pnl_missing_count": missing,
        "recovery_rate": recovered / len(trades) if trades else None,
        "pnl_path_counts": dict(path_counts.most_common()),
        "pnl_key_counts": dict(key_counts.most_common()),
        "samples": samples,
        "recovery_status": "PASS" if recovered > 0 else "NO_NUMERIC_PNL_FOUND",
    }
