from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any

from .diagnostics import build_diagnostic_report
from .timeline import build_timeline


def export_audit(root: Path, output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    timeline = build_timeline(root)
    diagnostics = build_diagnostic_report(root)

    json_path = output_root / "o3_audit_export.json"
    csv_path = output_root / "o3_timeline_export.csv"

    json_path.write_text(
        json.dumps({
            "diagnostics": diagnostics,
            "timeline": timeline,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    fields = [
        "observed_at",
        "source",
        "event",
        "level",
        "state",
        "status",
        "symbol",
        "client_order_id",
    ]
    with csv_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for value in timeline:
            writer.writerow({
                "observed_at": value.get("observed_at", ""),
                "source": value.get("_source", ""),
                "event": value.get("event", ""),
                "level": value.get("level", ""),
                "state": value.get("state", ""),
                "status": value.get("status", ""),
                "symbol": value.get("symbol", ""),
                "client_order_id": value.get("client_order_id", ""),
            })

    return {
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "timeline_record_count": len(timeline),
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
