from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def _read(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {**default, "read_error": True}


def evaluate_production_gates(root: Path) -> dict[str, Any]:
    paper = _read(
        root / "release/actual_validation_control_center/actual/"
               "paper_completion_certificate.json",
        {"eligible": False, "paper_complete": False},
    )
    l2 = _read(
        root / "release/l2_live_read_only_preparation/actual/"
               "l2_actual_qualification.json",
        {"actual_live_read_performed": False},
    )
    l3 = _read(
        root / "release/l3_live_micro_execution_preparation/actual/"
               "l3_actual_qualification.json",
        {"actual_live_orders_submitted": 0},
    )
    l4 = _read(
        root / "release/l4_live_reconciliation_preparation/actual/"
               "l4_actual_qualification.json",
        {"actual_live_reconciliation_performed": False},
    )
    l5 = _read(
        root / "release/l5_live_autonomous_runtime_preparation/actual/"
               "l5_actual_qualification.json",
        {"actual_live_runtime_qualified": False},
    )
    l6 = _read(
        root / "release/l6_live_long_run_qualification_preparation/actual/"
               "l6_actual_qualification.json",
        {
            "actual_live_long_run_qualified": False,
            "live_complete": False,
        },
    )

    checks = {
        "paper_completion_certificate": (
            paper.get("eligible") is True
            and paper.get("paper_complete") is True
        ),
        "l2_actual_live_read": (
            l2.get("actual_live_read_performed") is True
        ),
        "l3_actual_micro_live": (
            l3.get("actual_live_orders_submitted", 0) > 0
        ),
        "l4_actual_reconciliation": (
            l4.get("actual_live_reconciliation_performed") is True
        ),
        "l5_actual_runtime": (
            l5.get("actual_live_runtime_qualified") is True
        ),
        "l6_actual_long_run": (
            l6.get("actual_live_long_run_qualified") is True
            and l6.get("live_complete") is True
        ),
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "production_release_allowed": all(checks.values()),
    }
