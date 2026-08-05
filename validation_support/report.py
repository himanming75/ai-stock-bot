from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


class ValidationReportBuilder:
    def build(
        self,
        *,
        sections: dict[str, Any],
    ) -> dict[str, Any]:
        failures = []
        for section, value in sections.items():
            for failure in value.get("failed", []):
                failures.append({
                    "section": section,
                    "failure": failure,
                })

        return {
            "stage": "VALIDATION_SUPPORT_REPORT",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": "PASS" if not failures else "FAIL",
            "failure_count": len(failures),
            "failure_summary": failures,
            "sections": sections,
            "operator_next_action": (
                "RUN_P2_READ_ONLY_VALIDATION"
                if not failures
                else "FIX_REPORTED_FAILURES"
            ),
            "network_call_performed": False,
            "order_submission_performed": False,
        }

    def write(self, path: Path, report: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
