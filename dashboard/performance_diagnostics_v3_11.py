
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import math

MIN_SAMPLE = 10
MIN_GROUP_SAMPLE = 5

def _num(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except Exception:
        return None

def _holding_minutes(trade):
    try:
        a = trade.get("entry_time")
        b = trade.get("exit_time") or trade.get("time")
        if not a or not b:
            return None
        da = datetime.fromisoformat(str(a).replace("Z","+00:00"))
        db = datetime.fromisoformat(str(b).replace("Z","+00:00"))
        m = (db-da).total_seconds()/60.0
        return m if m >= 0 else None
    except Exception:
        return None

def _result(trade):
    p = _num(trade.get("pnl"))
    if p is None or p == 0:
        return "BREAKEVEN"
    return "WIN" if p > 0 else "LOSS"

def _group(trades, key_fn):
    grouped = defaultdict(list)
    for t in trades:
        grouped[str(key_fn(t) or "UNKNOWN")].append(t)
    out = []
    for name, rows in grouped.items():
        pnls = [_num(r.get("pnl")) for r in rows]
        pnls = [v for v in pnls if v is not None]
        wins = [v for v in pnls if v > 0]
        losses = [v for v in pnls if v < 0]
        holds = [_holding_minutes(r) for r in rows]
        holds = [v for v in holds if v is not None]
        gp = sum(wins)
        gl = abs(sum(losses))
        pf = gp/gl if gl > 0 else ("INF" if gp > 0 else None)
        out.append({
            "name": name,
            "trade_count": len(rows),
            "numeric_trade_count": len(pnls),
            "net_realized_pnl": sum(pnls) if pnls else None,
            "win_rate": len(wins)/len(pnls) if pnls else None,
            "profit_factor": pf,
            "average_trade": sum(pnls)/len(pnls) if pnls else None,
            "average_holding_minutes": sum(holds)/len(holds) if holds else None,
            "sample_status": "PASS_SAMPLE" if len(pnls) >= MIN_GROUP_SAMPLE else "INSUFFICIENT_SAMPLE",
        })
    out.sort(
        key=lambda x: (
            x["net_realized_pnl"] is not None,
            x["net_realized_pnl"] if x["net_realized_pnl"] is not None else -1e30,
        ),
        reverse=True,
    )
    return out

def _streaks(trades):
    ordered = list(reversed(trades))
    max_w = max_l = cur_w = cur_l = 0
    for t in ordered:
        r = _result(t)
        if r == "WIN":
            cur_w += 1
            cur_l = 0
            max_w = max(max_w, cur_w)
        elif r == "LOSS":
            cur_l += 1
            cur_w = 0
            max_l = max(max_l, cur_l)
        else:
            cur_w = cur_l = 0
    return {"max_consecutive_wins": max_w, "max_consecutive_losses": max_l}

def build_performance_diagnostics(trades):
    numeric = [t for t in trades if _num(t.get("pnl")) is not None]
    wins = [t for t in numeric if _num(t.get("pnl")) > 0]
    losses = [t for t in numeric if _num(t.get("pnl")) < 0]
    holds = [_holding_minutes(t) for t in numeric]
    holds = [v for v in holds if v is not None]
    best = max(numeric, key=lambda t: _num(t.get("pnl")), default=None)
    worst = min(numeric, key=lambda t: _num(t.get("pnl")), default=None)
    status = "PASS_SAMPLE" if len(numeric) >= MIN_SAMPLE else "INSUFFICIENT_SAMPLE"

    notes = []
    if status == "INSUFFICIENT_SAMPLE":
        notes.append(
            f"Only {len(numeric)} canonical numeric trades are available; "
            f"minimum diagnostic sample is {MIN_SAMPLE}."
        )
    if not losses:
        notes.append(
            "No losing canonical trades are present yet; downside diagnostics are not stable."
        )
    if len(set(str(t.get("symbol") or "UNKNOWN") for t in numeric)) <= 1:
        notes.append(
            "Symbol diversification is insufficient for cross-symbol conclusions."
        )

    return {
        "status": status,
        "minimum_sample_required": MIN_SAMPLE,
        "minimum_group_sample_required": MIN_GROUP_SAMPLE,
        "canonical_numeric_trade_count": len(numeric),
        "win_count": len(wins),
        "loss_count": len(losses),
        "breakeven_count": len(numeric)-len(wins)-len(losses),
        "best_trade": best,
        "worst_trade": worst,
        "average_holding_minutes": sum(holds)/len(holds) if holds else None,
        "streaks": _streaks(trades),
        "by_symbol": _group(numeric, lambda t: t.get("symbol")),
        "by_exit_reason": _group(numeric, lambda t: t.get("reason")),
        "by_date": _group(
            numeric,
            lambda t: str(t.get("exit_time") or t.get("time") or "")[:10],
        ),
        "notes": notes,
        "contracts": {
            "read_only": True,
            "canonical_source_only": True,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "production_selector_modified": False,
            "duplicate_engine_created": False,
        },
    }
