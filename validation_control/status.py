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


def collect_actual_validation_status(root: Path) -> dict[str, Any]:
    p2 = _read(
        root / "release/p2_actual_paper_execution/actual/"
               "p2_actual_validation.json",
        {"validated": False, "status": "MISSING"},
    )
    p3 = _read(
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "p3_actual_validation.json",
        {"validated": False, "status": "MISSING"},
    )
    p4 = _read(
        root / "release/p4_autonomous_paper_runtime/actual/"
               "p4_actual_validation.json",
        {"validated": False, "status": "MISSING"},
    )
    p5 = _read(
        root / "release/p5_paper_long_run_qualification/actual/"
               "p5_actual_qualification.json",
        {
            "actual_paper_long_run_qualified": False,
            "paper_complete": False,
            "status": "MISSING",
        },
    )

    values = {
        "p2": {
            "validated": p2.get("validated") is True,
            "status": p2.get("status", "MISSING"),
        },
        "p3": {
            "validated": p3.get("validated") is True,
            "status": p3.get("status", "MISSING"),
        },
        "p4": {
            "validated": p4.get("validated") is True,
            "status": p4.get("status", "MISSING"),
        },
        "p5": {
            "validated": (
                p5.get("actual_paper_long_run_qualified") is True
            ),
            "paper_complete": p5.get("paper_complete") is True,
            "status": p5.get("status", "MISSING"),
        },
    }

    checks = {
        "p2_actual_validated": values["p2"]["validated"],
        "p3_actual_validated": values["p3"]["validated"],
        "p4_actual_validated": values["p4"]["validated"],
        "p5_actual_long_run_qualified": values["p5"]["validated"],
        "paper_complete": values["p5"]["paper_complete"],
    }

    if not checks["p2_actual_validated"]:
        next_action = "RUN_P2_P3_ACTUAL_VALIDATION_AFTER_PAPER_ORDER"
    elif not checks["p3_actual_validated"]:
        next_action = "COMPLETE_P3_FILL_AND_RECONCILIATION_VALIDATION"
    elif not checks["p4_actual_validated"]:
        next_action = "RUN_P4_ACTUAL_RUNTIME_AND_RECORD_VALIDATION"
    elif not checks["p5_actual_long_run_qualified"]:
        next_action = "RUN_P5_ACTUAL_LONG_RUN_QUALIFICATION"
    elif not checks["paper_complete"]:
        next_action = "GENERATE_PAPER_COMPLETION_CERTIFICATE"
    else:
        next_action = "PAPER_COMPLETE_BEGIN_L2_ACTUAL_LIVE_READ"

    return {
        "stage": "ACTUAL_VALIDATION_CONTROL_CENTER",
        "checks": checks,
        "values": values,
        "paper_complete": checks["paper_complete"],
        "next_action": next_action,
        "actual_paper_orders_submitted_by_status_check": 0,
        "actual_live_orders_submitted": 0,
    }
