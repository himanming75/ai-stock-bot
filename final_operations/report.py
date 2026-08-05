from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import read_json


def build_final_operations_report(root: Path) -> dict[str, Any]:
    diagnostics = read_json(
        root / "release/bundle_c_r14_to_r15_final_operations/actual/"
               "final_diagnostics.json"
    )
    release_gate = read_json(
        root / "release/bundle_c_r14_to_r15_final_operations/actual/"
               "final_release_gate.json"
    )
    bundle_a = read_json(
        root / "release/bundle_a_r7_to_r10_runtime_core/actual/"
               "bundle_a_result.json"
    )
    bundle_b = read_json(
        root / "release/bundle_b_r11_to_r13_broker_multi_account/"
               "actual/bundle_b_result.json"
    )

    return {
        "stage": "BUNDLE_C_R14_TO_R15",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state": "FINAL_OPERATIONS_PREPARED",
        "status": (
            "PASS"
            if diagnostics.get("status") == "PASS"
            else "FAIL"
        ),
        "r14_final_operations_integration": "READY",
        "r15_production_candidate_gate": "READY",
        "bundle_a_state": bundle_a.get("state", ""),
        "bundle_b_state": bundle_b.get("state", ""),
        "production_candidate_ready": release_gate.get(
            "production_candidate_ready", False
        ),
        "production_release_allowed": release_gate.get(
            "production_release_allowed", False
        ),
        "release_state": release_gate.get("release_state", "BLOCKED"),
        "remaining_actual_validations": [
            item
            for item, passed in release_gate.get("checks", {}).items()
            if not passed
        ],
        "actual_release_performed": False,
        "windows_task_registration_performed": False,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_action": (
            "RUN_P2_TO_P5_ACTUAL_PAPER_VALIDATION"
        ),
    }
