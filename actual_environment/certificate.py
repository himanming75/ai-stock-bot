from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


def build_certificate(
    result: dict[str, Any],
) -> dict[str, Any]:
    eligible = (
        result.get("qualified") is True
        and result.get("status") == "PASS"
    )
    return {
        "certificate_stage": "P1_ACTUAL_ENVIRONMENT",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "eligible": eligible,
        "status": "PASS" if eligible else "BLOCKED",
        "p1_actual_environment_validated": eligible,
        "p2_actual_broker_read_allowed": eligible,
        "p3_actual_paper_order_allowed": False,
        "live_validation_allowed": False,
        "live_order_submission_allowed": False,
        "actual_network_used_during_p1": False,
        "actual_orders_submitted_during_p1": 0,
        "failed": result.get("failed", []),
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
