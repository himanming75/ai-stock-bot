from __future__ import annotations
from datetime import datetime, timezone
import csv
import html
import json
from pathlib import Path
from typing import Any


class ReportBuilder:
    def build(
        self,
        *,
        period: str,
        sections: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "stage": "AUTO_REPORT_SYSTEM",
            "period": period.upper(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
            "read_only": True,
            "external_delivery_performed": False,
        }

    def write_json(self, path: Path, report: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def write_html(self, path: Path, report: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for section, value in report["sections"].items():
            rows.append(
                f"<section><h2>{html.escape(section)}</h2>"
                f"<pre>{html.escape(json.dumps(value, indent=2, sort_keys=True))}</pre>"
                "</section>"
            )
        body = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AI Stock Bot {html.escape(report["period"])} Report</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;color:#17202a}}
header{{border-bottom:2px solid #273746;margin-bottom:24px}}
section{{page-break-inside:avoid;margin-bottom:24px}}
pre{{background:#f4f6f7;padding:14px;white-space:pre-wrap}}
@media print{{body{{margin:12mm}}}}
</style>
</head>
<body>
<header>
<h1>AI Stock Bot {html.escape(report["period"])} Report</h1>
<p>Generated: {html.escape(report["generated_at"])}</p>
<p>Read-only offline report</p>
</header>
{''.join(rows)}
</body>
</html>
"""
        path.write_text(body, encoding="utf-8")

    def write_csv(
        self,
        path: Path,
        rows: list[dict[str, Any]],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
