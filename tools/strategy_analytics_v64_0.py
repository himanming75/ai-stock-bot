#!/usr/bin/env python3
"""
V64.0 Strategy Analytics Foundation

Consumes V60 trade history and V63 risk analytics to build offline,
strategy-level analytics suitable for later ranking and optimization.

Features:
- closed-trade extraction from flexible V60 history schemas
- strategy, symbol, side, weekday, and hour breakdowns
- win rate, average win/loss, profit factor, expectancy
- payoff ratio and bounded Kelly fraction
- average holding duration
- deterministic strategy ranking
- SHA-256 integrity hashes
- no network access
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

VERSION = "64.0"
SCHEMA_VERSION = "v64.0.strategy_analytics.1"
ERROR_SCHEMA_VERSION = "v64.0.strategy_analytics_error.1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dec(value: Any, field: str, default: Optional[Decimal] = None) -> Decimal:
    if value is None and default is not None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def q4(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def q6(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def parse_time(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def first_present(mapping: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def validate_sources(v60: Dict[str, Any], v63: Dict[str, Any]) -> None:
    if not isinstance(v60, dict):
        raise ValueError("v60 must be an object")
    if v60.get("status") != "PASS":
        raise ValueError("v60 status must be PASS")
    if v60.get("network_used") is not False:
        raise ValueError("v60 network_used must be false")

    history_hash = str(first_present(v60, ("history_sha256", "trade_history_sha256"), ""))
    if len(history_hash) != 64:
        raise ValueError("v60 history hash must be 64 characters")

    if not isinstance(v63, dict):
        raise ValueError("v63 must be an object")
    if v63.get("status") != "PASS":
        raise ValueError("v63 status must be PASS")
    if v63.get("network_used") is not False:
        raise ValueError("v63 network_used must be false")
    if len(str(v63.get("risk_report_sha256", ""))) != 64:
        raise ValueError("v63 risk_report_sha256 must be 64 characters")


def locate_trade_events(v60: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("trades", "trade_events", "history", "events", "ledger"):
        value = v60.get(key)
        if isinstance(value, list):
            return [deepcopy(x) for x in value if isinstance(x, dict)]
    return []


def normalize_trade_event(event: Dict[str, Any], index: int) -> Dict[str, Any]:
    symbol = str(first_present(event, ("symbol", "ticker"), "UNKNOWN")).upper()
    side = str(first_present(event, ("side", "direction", "position_side"), "LONG")).upper()
    strategy = str(first_present(
        event,
        ("strategy", "strategy_name", "strategy_id", "signal_name"),
        "UNSPECIFIED",
    ))

    opened_raw = first_present(
        event,
        ("opened_at", "entry_time", "open_time", "entry_timestamp", "execution_time", "event_time"),
    )
    closed_raw = first_present(
        event,
        ("closed_at", "exit_time", "close_time", "exit_timestamp"),
    )
    status = str(first_present(event, ("status", "trade_status", "lot_status"), "")).upper()

    realized_raw = first_present(
        event,
        ("realized_pnl", "net_realized_pnl", "net_pnl", "pnl", "profit_loss"),
    )

    is_closed = (
        closed_raw is not None
        or status in {"CLOSED", "EXITED", "COMPLETE", "COMPLETED"}
        or realized_raw is not None
    )

    normalized = {
        "trade_id": str(first_present(event, ("trade_id", "id", "event_id"), index + 1)),
        "symbol": symbol,
        "side": side,
        "strategy": strategy,
        "is_closed": bool(is_closed),
    }

    if opened_raw is not None:
        opened = parse_time(opened_raw, f"trade[{index}].opened_at")
        normalized["opened_at"] = opened.isoformat().replace("+00:00", "Z")
        normalized["entry_weekday"] = opened.strftime("%A")
        normalized["entry_hour_utc"] = opened.hour
    else:
        normalized["opened_at"] = None
        normalized["entry_weekday"] = "UNKNOWN"
        normalized["entry_hour_utc"] = -1

    if is_closed:
        pnl = dec(realized_raw, f"trade[{index}].realized_pnl", Decimal("0"))
        normalized["realized_pnl"] = q4(pnl)

        if closed_raw is not None:
            closed = parse_time(closed_raw, f"trade[{index}].closed_at")
            normalized["closed_at"] = closed.isoformat().replace("+00:00", "Z")
            if normalized["opened_at"] is not None:
                opened = parse_time(normalized["opened_at"], f"trade[{index}].opened_at")
                seconds = max(Decimal("0"), Decimal(str((closed - opened).total_seconds())))
                normalized["holding_minutes"] = q4(seconds / Decimal("60"))
            else:
                normalized["holding_minutes"] = "0.0000"
        else:
            normalized["closed_at"] = None
            holding = dec(first_present(event, ("holding_minutes", "duration_minutes"), "0"),
                          f"trade[{index}].holding_minutes")
            normalized["holding_minutes"] = q4(max(Decimal("0"), holding))
    return normalized


def aggregate_group(name: str, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    closed = [t for t in trades if t["is_closed"]]
    pnls = [dec(t["realized_pnl"], "realized_pnl") for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    flats = [p for p in pnls if p == 0]

    trade_count = len(closed)
    win_count = len(wins)
    loss_count = len(losses)
    flat_count = len(flats)

    gross_profit = sum(wins, Decimal("0"))
    gross_loss_abs = abs(sum(losses, Decimal("0")))
    net_pnl = sum(pnls, Decimal("0"))
    win_rate = Decimal(win_count) / Decimal(trade_count) if trade_count else Decimal("0")
    avg_win = gross_profit / Decimal(win_count) if win_count else Decimal("0")
    avg_loss_abs = gross_loss_abs / Decimal(loss_count) if loss_count else Decimal("0")
    profit_factor = gross_profit / gross_loss_abs if gross_loss_abs != 0 else (
        Decimal("999999") if gross_profit > 0 else Decimal("0")
    )
    expectancy = net_pnl / Decimal(trade_count) if trade_count else Decimal("0")
    payoff_ratio = avg_win / avg_loss_abs if avg_loss_abs != 0 else Decimal("0")

    if avg_loss_abs != 0 and payoff_ratio != 0:
        loss_rate = Decimal("1") - win_rate
        kelly = win_rate - (loss_rate / payoff_ratio)
        kelly = max(Decimal("0"), min(Decimal("1"), kelly))
    else:
        kelly = Decimal("0")

    holding_values = [dec(t.get("holding_minutes", "0"), "holding_minutes") for t in closed]
    average_holding = (
        sum(holding_values, Decimal("0")) / Decimal(len(holding_values))
        if holding_values else Decimal("0")
    )

    core = {
        "group": name,
        "trade_count": trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "flat_count": flat_count,
        "win_rate": q6(win_rate),
        "gross_profit": q4(gross_profit),
        "gross_loss": q4(-gross_loss_abs),
        "net_pnl": q4(net_pnl),
        "average_win": q4(avg_win),
        "average_loss": q4(-avg_loss_abs),
        "profit_factor": q6(profit_factor),
        "expectancy": q4(expectancy),
        "payoff_ratio": q6(payoff_ratio),
        "kelly_fraction": q6(kelly),
        "average_holding_minutes": q4(average_holding),
    }
    result = dict(core)
    result["group_sha256"] = sha256_hex(core)
    return result


def build_breakdown(trades: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        grouped[str(trade.get(key, "UNKNOWN"))].append(trade)
    return [aggregate_group(name, grouped[name]) for name in sorted(grouped)]


class StrategyAnalyticsEngine:
    def build(self, v60: Dict[str, Any], v63: Dict[str, Any]) -> Dict[str, Any]:
        validate_sources(v60, v63)

        raw_events = locate_trade_events(v60)
        trades = [normalize_trade_event(event, index) for index, event in enumerate(raw_events)]
        closed = [t for t in trades if t["is_closed"]]
        open_trades = [t for t in trades if not t["is_closed"]]

        overall = aggregate_group("ALL", trades)
        by_strategy = build_breakdown(closed, "strategy")
        by_symbol = build_breakdown(closed, "symbol")
        by_side = build_breakdown(closed, "side")
        by_weekday = build_breakdown(closed, "entry_weekday")
        by_hour = build_breakdown(closed, "entry_hour_utc")

        ranked = []
        for item in by_strategy:
            score = (
                dec(item["expectancy"], "expectancy")
                + dec(item["net_pnl"], "net_pnl") / Decimal("100")
                + dec(item["win_rate"], "win_rate") * Decimal("10")
                - Decimal(str(v63.get("analytics", {}).get("risk_score", "0"))) / Decimal("100")
            )
            ranked.append({
                "rank": 0,
                "strategy": item["group"],
                "score": q6(score),
                "trade_count": item["trade_count"],
                "net_pnl": item["net_pnl"],
                "win_rate": item["win_rate"],
                "profit_factor": item["profit_factor"],
                "expectancy": item["expectancy"],
            })
        ranked.sort(
            key=lambda x: (
                -dec(x["score"], "score"),
                -int(x["trade_count"]),
                str(x["strategy"]),
            )
        )
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index
            item["ranking_sha256"] = sha256_hex({
                "rank": item["rank"],
                "strategy": item["strategy"],
                "score": item["score"],
                "trade_count": item["trade_count"],
                "net_pnl": item["net_pnl"],
                "win_rate": item["win_rate"],
                "profit_factor": item["profit_factor"],
                "expectancy": item["expectancy"],
            })

        result = {
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "decision": "strategy_analytics_built",
            "network_used": False,
            "source_v60_history_sha256": first_present(
                v60, ("history_sha256", "trade_history_sha256")
            ),
            "source_v63_risk_report_sha256": v63["risk_report_sha256"],
            "source_event_count": len(raw_events),
            "closed_trade_count": len(closed),
            "open_trade_count": len(open_trades),
            "overall": overall,
            "by_strategy": by_strategy,
            "by_symbol": by_symbol,
            "by_side": by_side,
            "by_weekday": by_weekday,
            "by_entry_hour_utc": by_hour,
            "strategy_ranking": ranked,
            "normalized_closed_trades": closed,
        }
        result["strategy_report_sha256"] = sha256_hex({
            "schema_version": SCHEMA_VERSION,
            "source_v60_history_sha256": result["source_v60_history_sha256"],
            "source_v63_risk_report_sha256": result["source_v63_risk_report_sha256"],
            "overall": overall,
            "by_strategy": by_strategy,
            "by_symbol": by_symbol,
            "by_side": by_side,
            "by_weekday": by_weekday,
            "by_entry_hour_utc": by_hour,
            "strategy_ranking": ranked,
            "normalized_closed_trades": closed,
        })
        return result


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V64.0 Strategy Analytics Foundation")
    parser.add_argument("--trade-history", required=True)
    parser.add_argument("--risk-analytics", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    output = Path(args.output)
    try:
        result = StrategyAnalyticsEngine().build(
            read_json(Path(args.trade_history)),
            read_json(Path(args.risk_analytics)),
        )
        write_json(output, result)
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "source_event_count": result["source_event_count"],
            "closed_trade_count": result["closed_trade_count"],
            "open_trade_count": result["open_trade_count"],
            "net_pnl": result["overall"]["net_pnl"],
            "win_rate": result["overall"]["win_rate"],
            "profit_factor": result["overall"]["profit_factor"],
            "expectancy": result["overall"]["expectancy"],
            "strategy_count": len(result["by_strategy"]),
            "strategy_report_sha256": result["strategy_report_sha256"],
            "network_used": result["network_used"],
        }, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error = {
            "version": VERSION,
            "schema_version": ERROR_SCHEMA_VERSION,
            "status": "FAIL",
            "network_used": False,
            "error": str(exc),
        }
        write_json(output, error)
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
