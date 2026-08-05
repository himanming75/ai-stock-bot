from __future__ import annotations
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
from typing import Any


class OperatorReportBuilder:
    def build(
        self,
        *,
        sections: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "stage": "OPERATIONS_V2_DAILY_REPORT",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
            "read_only": True,
            "broker_actions_available": False,
            "automatic_order_submission_enabled": False,
        }

    def export_json(self, path: Path, report: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def export_csv(
        self,
        path: Path,
        rows: list[dict[str, Any]],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
