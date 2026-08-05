from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .status import collect_actual_validation_status


def generate_paper_completion_certificate(
    root: Path,
) -> dict[str, Any]:
    status = collect_actual_validation_status(root)
    checks = status["checks"]
    eligible = all([
        checks["p2_actual_validated"],
        checks["p3_actual_validated"],
        checks["p4_actual_validated"],
        checks["p5_actual_long_run_qualified"],
        checks["paper_complete"],
    ])

    certificate = {
        "stage": "PAPER_COMPLETION_CERTIFICATE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "eligible": eligible,
        "paper_complete": eligible,
        "checks": checks,
        "status": "PASS" if eligible else "BLOCKED",
        "production_live_allowed": False,
        "actual_live_orders_submitted": 0,
    }

    path = (
        root / "release/actual_validation_control_center/actual/"
               "paper_completion_certificate.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return certificate
