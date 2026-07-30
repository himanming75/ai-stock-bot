#!/usr/bin/env python3
"""
V62.0 Performance Dashboard Data Foundation

Transforms a V61 daily performance journal into dashboard-ready data:
- equity curve
- daily returns
- running peak
- drawdown curve
- headline performance metrics
- recent-period summary

Offline only. No network access.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "62.0"
SCHEMA_VERSION = "v62.0.performance_dashboard_data.1"
ERROR_SCHEMA_VERSION = "v62.0.performance_dashboard_data_error.1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dec(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def q4(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def q6(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def validate_v61(v61: Dict[str, Any]) -> None:
    if not isinstance(v61, dict):
        raise ValueError("v61 must be an object")
    if v61.get("status") != "PASS":
        raise ValueError("v61 status must be PASS")
    if v61.get("network_used") is not False:
        raise ValueError("v61 network_used must be false")
    entries = v61.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("v61 entries must be a non-empty list")
    journal_sha = str(v61.get("journal_sha256", ""))
    if len(journal_sha) != 64:
        raise ValueError("v61 journal_sha256 must be 64 characters")


class PerformanceDashboardBuilder:
    def build(self, v61: Dict[str, Any], recent_days: int = 5) -> Dict[str, Any]:
        validate_v61(v61)
        if recent_days <= 0:
            raise ValueError("recent_days must be greater than zero")

        entries = deepcopy(v61["entries"])
        chart: List[Dict[str, Any]] = []
        running_peak: Optional[Decimal] = None
        max_drawdown = Decimal("0")
        max_drawdown_date: Optional[str] = None

        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"entries[{index}] must be an object")

            equity = dec(entry.get("equity"), f"entries[{index}].equity")
            daily_pnl = dec(entry.get("daily_pnl", "0"), f"entries[{index}].daily_pnl")
            daily_return = dec(entry.get("daily_return", "0"), f"entries[{index}].daily_return")

            if running_peak is None or equity > running_peak:
                running_peak = equity

            drawdown_amount = equity - running_peak
            drawdown = drawdown_amount / running_peak if running_peak != 0 else Decimal("0")

            if drawdown < max_drawdown:
                max_drawdown = drawdown
                max_drawdown_date = str(entry.get("journal_date"))

            point_core = {
                "sequence": int(entry.get("sequence", index + 1)),
                "journal_date": str(entry.get("journal_date")),
                "equity": q4(equity),
                "daily_pnl": q4(daily_pnl),
                "daily_return": q6(daily_return),
                "running_peak": q4(running_peak),
                "drawdown_amount": q4(drawdown_amount),
                "drawdown": q6(drawdown),
                "trade_count": int(entry.get("trade_count", 0)),
                "daily_trade_events": int(entry.get("daily_trade_events", 0)),
                "closed_trade_count": int(entry.get("closed_trade_count", 0)),
                "daily_closed_trades": int(entry.get("daily_closed_trades", 0)),
            }
            point = dict(point_core)
            point["point_sha256"] = sha256_hex(point_core)
            chart.append(point)

        first_equity = dec(chart[0]["equity"], "first_equity")
        latest_equity = dec(chart[-1]["equity"], "latest_equity")
        total_pnl = latest_equity - first_equity
        total_return = total_pnl / first_equity if first_equity != 0 else Decimal("0")

        positive_days = sum(1 for p in chart if dec(p["daily_return"], "daily_return") > 0)
        negative_days = sum(1 for p in chart if dec(p["daily_return"], "daily_return") < 0)
        flat_days = len(chart) - positive_days - negative_days
        profitable_ratio = Decimal(positive_days) / Decimal(len(chart)) if chart else Decimal("0")

        recent = chart[-recent_days:]
        recent_start = dec(recent[0]["equity"], "recent_start")
        recent_end = dec(recent[-1]["equity"], "recent_end")
        recent_pnl = recent_end - recent_start
        recent_return = recent_pnl / recent_start if recent_start != 0 else Decimal("0")

        metrics_core = {
            "first_date": chart[0]["journal_date"],
            "latest_date": chart[-1]["journal_date"],
            "trading_day_count": len(chart),
            "starting_equity": q4(first_equity),
            "latest_equity": q4(latest_equity),
            "total_pnl": q4(total_pnl),
            "total_return": q6(total_return),
            "max_drawdown": q6(max_drawdown),
            "max_drawdown_date": max_drawdown_date,
            "positive_day_count": positive_days,
            "negative_day_count": negative_days,
            "flat_day_count": flat_days,
            "profitable_day_ratio": q6(profitable_ratio),
            "total_trade_events": int(chart[-1]["trade_count"]),
            "total_closed_trades": int(chart[-1]["closed_trade_count"]),
        }
        metrics = dict(metrics_core)
        metrics["metrics_sha256"] = sha256_hex(metrics_core)

        recent_core = {
            "window_days_requested": recent_days,
            "window_days_used": len(recent),
            "first_date": recent[0]["journal_date"],
            "latest_date": recent[-1]["journal_date"],
            "starting_equity": q4(recent_start),
            "latest_equity": q4(recent_end),
            "pnl": q4(recent_pnl),
            "return": q6(recent_return),
            "trade_events": int(recent[-1]["trade_count"]) - (
                int(chart[-len(recent)-1]["trade_count"]) if len(chart) > len(recent) else 0
            ),
            "closed_trades": int(recent[-1]["closed_trade_count"]) - (
                int(chart[-len(recent)-1]["closed_trade_count"]) if len(chart) > len(recent) else 0
            ),
        }
        recent_summary = dict(recent_core)
        recent_summary["recent_sha256"] = sha256_hex(recent_core)

        result = {
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "decision": "dashboard_data_built",
            "network_used": False,
            "source_v61_journal_sha256": v61["journal_sha256"],
            "chart_point_count": len(chart),
            "chart": chart,
            "metrics": metrics,
            "recent_summary": recent_summary,
        }
        result["dashboard_sha256"] = sha256_hex({
            "source_v61_journal_sha256": result["source_v61_journal_sha256"],
            "chart": chart,
            "metrics": metrics,
            "recent_summary": recent_summary,
            "schema_version": SCHEMA_VERSION,
        })
        return result


def export_chart_csv(result: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sequence", "journal_date", "equity", "daily_pnl", "daily_return",
        "running_peak", "drawdown_amount", "drawdown", "trade_count",
        "daily_trade_events", "closed_trade_count", "daily_closed_trades",
        "point_sha256",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for point in result.get("chart", []):
            writer.writerow({field: point.get(field) for field in fields})


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V62.0 Performance Dashboard Data Foundation")
    parser.add_argument("--journal-input", required=True)
    parser.add_argument("--recent-days", type=int, default=5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--csv-output")
    args = parser.parse_args(argv)

    output = Path(args.output)
    try:
        result = PerformanceDashboardBuilder().build(
            read_json(Path(args.journal_input)),
            recent_days=args.recent_days,
        )
        write_json(output, result)
        if args.csv_output:
            export_chart_csv(result, Path(args.csv_output))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "chart_point_count": result["chart_point_count"],
            "latest_equity": result["metrics"]["latest_equity"],
            "total_return": result["metrics"]["total_return"],
            "max_drawdown": result["metrics"]["max_drawdown"],
            "dashboard_sha256": result["dashboard_sha256"],
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
