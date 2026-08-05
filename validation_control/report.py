from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .certificate import generate_paper_completion_certificate
from .status import collect_actual_validation_status


def build_validation_report(root: Path) -> dict[str, Any]:
    status = collect_actual_validation_status(root)
    certificate = generate_paper_completion_certificate(root)
    return {
        "stage": "ACTUAL_VALIDATION_REPORT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "paper_certificate": certificate,
        "live_actual_sequence": [
            "L2_ACTUAL_LIVE_READ",
            "L3_ACTUAL_MICRO_LIVE",
            "L4_ACTUAL_RECONCILIATION",
            "L5_ACTUAL_LIVE_RUNTIME",
            "L6_ACTUAL_LIVE_LONG_RUN",
            "PRODUCTION_RELEASE_REVIEW",
        ],
        "actual_paper_orders_submitted_by_report": 0,
        "actual_live_orders_submitted": 0,
    }
