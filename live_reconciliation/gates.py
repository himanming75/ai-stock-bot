from __future__ import annotations
import json
from pathlib import Path


def _read(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_l4_gates(root: Path) -> dict:
    l1 = _read(
        root / "release/l1_live_safety_boundary/actual/l1_result.json",
        {"status": "MISSING"},
    )
    l2 = _read(
        root / "release/l2_live_read_only_preparation/actual/"
               "l2_offline_qualification.json",
        {"status": "MISSING"},
    )
    l3 = _read(
        root / "release/l3_live_micro_execution_preparation/actual/"
               "l3_offline_qualification.json",
        {"status": "MISSING"},
    )
    paper = l1.get("paper_completion", {})

    checks = {
        "l1_pass": l1.get("status") == "PASS",
        "l2_preparation_pass": l2.get("status") == "PASS",
        "l3_preparation_pass": l3.get("status") == "PASS",
        "paper_complete": paper.get("paper_complete") is True,
        "paper_certificate_present": (
            paper.get("certificate_present") is True
        ),
        "l2_actual_complete": (
            l2.get("actual_live_read_performed") is True
        ),
        "l3_actual_complete": (
            l3.get("actual_live_orders_submitted", 0) > 0
        ),
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "actual_live_reconciliation_allowed": all(checks.values()),
    }
