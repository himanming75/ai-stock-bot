from __future__ import annotations
from datetime import date, datetime, timezone
import csv
import json
from pathlib import Path
from typing import Any

from .diagnostics import build_diagnostic_report
from .health_score import calculate_health_score
from .history import performance_summary
from .timeline import build_timeline


def build_daily_report(
    root: Path,
    *,
    trading_day: str | None = None,
) -> dict[str, Any]:
    day = trading_day or date.today().isoformat()
    timeline = [
        item for item in build_timeline(root, limit=10000)
        if str(
            item.get("observed_at")
            or item.get("created_at")
            or item.get("updated_at")
            or ""
        ).startswith(day)
    ]
    diagnostics = build_diagnostic_report(root)
    health = calculate_health_score(root)
    performance = performance_summary(root)

    counts: dict[str, int] = {}
    for item in timeline:
        source = str(item.get("_source", "unknown"))
        counts[source] = counts.get(source, 0) + 1

    return {
        "stage": "O4_DAILY_REPORT",
        "trading_day": day,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "performance": performance,
        "event_counts": counts,
        "timeline_record_count": len(timeline),
        "diagnostics": diagnostics,
        "paper_complete": False,
        "live_complete": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def export_daily_report(
    root: Path,
    *,
    trading_day: str | None = None,
) -> dict[str, Any]:
    report = build_daily_report(root, trading_day=trading_day)
    day = report["trading_day"]
    output = (
        root / "release/o4_runtime_resume_session_reporting/actual/reports"
    )
    output.mkdir(parents=True, exist_ok=True)

    json_path = output / f"{day}_daily_report.json"
    csv_path = output / f"{day}_daily_summary.csv"

    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rows = [
        ("health_score", report["health"].get("score")),
        ("health_state", report["health"].get("state")),
        ("timeline_record_count", report["timeline_record_count"]),
        ("realized_pnl", report["performance"].get("realized_pnl")),
        ("win_rate", report["performance"].get("win_rate")),
        ("maximum_drawdown", report["performance"].get("maximum_drawdown")),
        ("paper_complete", report["paper_complete"]),
        ("live_complete", report["live_complete"]),
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)

    return {
        "report": report,
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
