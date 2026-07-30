#!/usr/bin/env python3
"""
V61.1 Daily Performance Journal Snapshot Compatibility Patch

Builds an append-only daily journal from:
- V59 paper portfolio update result
- V60 trade ledger/history result
- Optional prior V61 journal state

Offline only. No network access.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VERSION = "61.1"
SCHEMA_VERSION = "v61.0.daily_performance_journal.1"
ERROR_SCHEMA_VERSION = "v61.0.daily_performance_journal_error.1"
ZERO4 = Decimal("0.0000")
ZERO6 = Decimal("0.000000")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def decimal_value(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def q4(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def q6(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def empty_journal() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "decision": "empty_journal",
        "network_used": False,
        "entry_count": 0,
        "entries": [],
        "summary": {
            "first_date": None,
            "latest_date": None,
            "starting_equity": "0.0000",
            "latest_equity": "0.0000",
            "cumulative_return": "0.000000",
            "best_daily_return": "0.000000",
            "worst_daily_return": "0.000000",
            "positive_day_count": 0,
            "negative_day_count": 0,
            "flat_day_count": 0,
            "total_trade_events": 0,
            "total_closed_trades": 0,
            "summary_sha256": "",
        },
        "journal_sha256": "",
    }


def validate_result(value: Dict[str, Any], name: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    if value.get("status") != "PASS":
        raise ValueError(f"{name} status must be PASS")
    if value.get("network_used") is not False:
        raise ValueError(f"{name} network_used must be false")


def get_snapshot(v59: Dict[str, Any]) -> Dict[str, Any]:
    """Return the best available V59 account-value source.

    Official V59.0 output stores values in:
      snapshot.cash_balance
      snapshot.total_market_value
      snapshot.net_liquidation_value
      snapshot.positions[].unrealized_pnl

    Older/sample variants may use portfolio or reconciliation, so those
    remain supported as compatibility fallbacks.
    """
    for key in ("snapshot", "account_snapshot", "paper_account_snapshot"):
        candidate = v59.get(key)
        if isinstance(candidate, dict):
            return candidate

    for key in ("portfolio", "reconciliation"):
        candidate = v59.get(key)
        if isinstance(candidate, dict):
            return candidate

    raise ValueError("V59 snapshot/portfolio/reconciliation object not found")


def sum_position_field(mapping: Dict[str, Any], field: str) -> Decimal:
    positions = mapping.get("positions", [])
    if not isinstance(positions, list):
        raise ValueError("positions must be a list")
    total = Decimal("0")
    for index, position in enumerate(positions):
        if not isinstance(position, dict):
            raise ValueError(f"positions[{index}] must be an object")
        total += decimal_value(position.get(field, "0"), f"positions[{index}].{field}")
    return total


def extract_account_values(v59: Dict[str, Any]) -> Dict[str, Decimal]:
    snapshot = get_snapshot(v59)
    reconciliation = v59.get("reconciliation")
    if not isinstance(reconciliation, dict):
        reconciliation = {}

    cash_raw = first_present(
        snapshot,
        ("cash_balance", "cash", "ending_cash"),
        first_present(reconciliation, ("ending_cash", "cash_balance", "cash"), "0"),
    )
    market_raw = first_present(
        snapshot,
        ("total_market_value", "market_value", "positions_market_value"),
        first_present(reconciliation, ("total_market_value", "market_value"), None),
    )
    equity_raw = first_present(
        snapshot,
        ("net_liquidation_value", "total_equity", "equity", "account_equity"),
        first_present(reconciliation, ("total_equity", "net_liquidation_value", "equity"), None),
    )
    unrealized_raw = first_present(
        snapshot,
        ("total_unrealized_pnl", "unrealized_pnl", "unrealized_profit_loss"),
        first_present(reconciliation, ("total_unrealized_pnl", "unrealized_pnl"), None),
    )

    cash = decimal_value(cash_raw, "cash")
    market_value = (
        decimal_value(market_raw, "market_value")
        if market_raw is not None
        else sum_position_field(snapshot, "market_value")
    )
    equity = (
        decimal_value(equity_raw, "equity")
        if equity_raw is not None
        else cash + market_value
    )
    unrealized = (
        decimal_value(unrealized_raw, "unrealized_pnl")
        if unrealized_raw is not None
        else sum_position_field(snapshot, "unrealized_pnl")
    )

    return {
        "cash": cash,
        "market_value": market_value,
        "equity": equity,
        "unrealized_pnl": unrealized,
    }


def first_present(mapping: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


class DailyPerformanceJournal:
    def update(
        self,
        v59: Dict[str, Any],
        v60: Dict[str, Any],
        prior: Optional[Dict[str, Any]],
        journal_time: str,
    ) -> Dict[str, Any]:
        validate_result(v59, "v59")
        validate_result(v60, "v60")

        when = parse_utc(journal_time, "journal_time")
        journal_date = when.date().isoformat()

        state = deepcopy(prior) if prior else empty_journal()
        entries = deepcopy(state.get("entries", []))
        if not isinstance(entries, list):
            raise ValueError("prior entries must be a list")

        if any(item.get("journal_date") == journal_date for item in entries):
            raise ValueError(f"duplicate journal_date rejected: {journal_date}")

        v59_sha = str(v59.get("integration_sha256") or v59.get("portfolio_update_sha256") or "")
        if len(v59_sha) != 64:
            raise ValueError("V59 integration hash must be 64 characters")

        v60_sha = str(v60.get("history_sha256") or "")
        if len(v60_sha) != 64:
            raise ValueError("V60 history_sha256 must be 64 characters")

        if any(item.get("v59_integration_sha256") == v59_sha for item in entries):
            raise ValueError(f"duplicate V59 integration rejected: {v59_sha}")
        if any(item.get("v60_history_sha256") == v60_sha for item in entries):
            raise ValueError(f"duplicate V60 history rejected: {v60_sha}")

        account_values = extract_account_values(v59)
        cash = account_values["cash"]
        market_value = account_values["market_value"]
        equity = account_values["equity"]
        unrealized = account_values["unrealized_pnl"]

        stats = v60.get("statistics", {})
        if not isinstance(stats, dict):
            raise ValueError("V60 statistics must be an object")
        net_realized = decimal_value(stats.get("net_realized_pnl", "0"), "net_realized_pnl")
        trade_count = int(v60.get("trade_count", stats.get("event_count", 0)))
        closed_count = int(stats.get("win_count", 0)) + int(stats.get("loss_count", 0)) + int(stats.get("breakeven_count", 0))

        previous = entries[-1] if entries else None
        previous_equity = decimal_value(previous["equity"], "previous_equity") if previous else equity
        daily_pnl = equity - previous_equity if previous else ZERO4
        daily_return = (daily_pnl / previous_equity) if previous and previous_equity != 0 else ZERO6

        previous_trade_count = int(previous["trade_count"]) if previous else 0
        previous_closed_count = int(previous["closed_trade_count"]) if previous else 0
        daily_trade_events = trade_count - previous_trade_count
        daily_closed_trades = closed_count - previous_closed_count
        if daily_trade_events < 0 or daily_closed_trades < 0:
            raise ValueError("trade counters cannot decrease")

        previous_entry_sha = entries[-1]["entry_sha256"] if entries else "GENESIS"
        core = {
            "sequence": len(entries) + 1,
            "journal_date": journal_date,
            "journal_time": utc_text(when),
            "cash": q4(cash),
            "market_value": q4(market_value),
            "equity": q4(equity),
            "unrealized_pnl": q4(unrealized),
            "net_realized_pnl": q4(net_realized),
            "daily_pnl": q4(daily_pnl),
            "daily_return": q6(daily_return),
            "trade_count": trade_count,
            "daily_trade_events": daily_trade_events,
            "closed_trade_count": closed_count,
            "daily_closed_trades": daily_closed_trades,
            "open_lot_count": int(v60.get("open_lot_count", stats.get("open_lot_count", 0))),
            "win_rate": str(stats.get("win_rate", "0.000000")),
            "profit_factor": str(stats.get("profit_factor", "0.000000")),
            "v59_integration_sha256": v59_sha,
            "v60_history_sha256": v60_sha,
            "previous_entry_sha256": previous_entry_sha,
        }
        entry = dict(core)
        entry["entry_sha256"] = sha256_hex(core)
        entries.append(entry)

        summary = self._summary(entries)
        result = {
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "decision": "daily_journal_updated",
            "network_used": False,
            "latest_entry_sha256": entry["entry_sha256"],
            "entry_count": len(entries),
            "entries": entries,
            "summary": summary,
        }
        result["journal_sha256"] = sha256_hex({
            "entries": entries,
            "summary": summary,
            "schema_version": SCHEMA_VERSION,
        })
        return result

    @staticmethod
    def _summary(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not entries:
            return empty_journal()["summary"]

        returns = [decimal_value(item["daily_return"], "daily_return") for item in entries]
        equities = [decimal_value(item["equity"], "equity") for item in entries]
        start = equities[0]
        latest = equities[-1]
        cumulative = ((latest - start) / start) if start != 0 else ZERO6

        positive = sum(1 for value in returns if value > 0)
        negative = sum(1 for value in returns if value < 0)
        flat = sum(1 for value in returns if value == 0)

        core = {
            "first_date": entries[0]["journal_date"],
            "latest_date": entries[-1]["journal_date"],
            "starting_equity": q4(start),
            "latest_equity": q4(latest),
            "cumulative_return": q6(cumulative),
            "best_daily_return": q6(max(returns)),
            "worst_daily_return": q6(min(returns)),
            "positive_day_count": positive,
            "negative_day_count": negative,
            "flat_day_count": flat,
            "total_trade_events": int(entries[-1]["trade_count"]),
            "total_closed_trades": int(entries[-1]["closed_trade_count"]),
        }
        result = dict(core)
        result["summary_sha256"] = sha256_hex(core)
        return result


def export_csv(result: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sequence", "journal_date", "journal_time", "cash", "market_value",
        "equity", "unrealized_pnl", "net_realized_pnl", "daily_pnl",
        "daily_return", "trade_count", "daily_trade_events",
        "closed_trade_count", "daily_closed_trades", "open_lot_count",
        "win_rate", "profit_factor", "entry_sha256",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in result.get("entries", []):
            writer.writerow({key: entry.get(key) for key in fields})


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V61.1 Daily Performance Journal Snapshot Compatibility Patch")
    parser.add_argument("--portfolio-input", required=True)
    parser.add_argument("--trade-history", required=True)
    parser.add_argument("--journal-state")
    parser.add_argument("--journal-time", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--csv-output")
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    try:
        v59 = read_json(Path(args.portfolio_input))
        v60 = read_json(Path(args.trade_history))
        prior = read_json(Path(args.journal_state)) if args.journal_state else None
        result = DailyPerformanceJournal().update(v59, v60, prior, args.journal_time)
        write_json(output_path, result)
        if args.csv_output:
            export_csv(result, Path(args.csv_output))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "entry_count": result["entry_count"],
            "latest_entry_sha256": result["latest_entry_sha256"],
            "journal_sha256": result["journal_sha256"],
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
        write_json(output_path, error)
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
