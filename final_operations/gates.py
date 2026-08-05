from __future__ import annotations
from pathlib import Path
from typing import Any

from .io import read_json


def evaluate_final_release_gate(root: Path) -> dict[str, Any]:
    bundle_a = read_json(
        root / "release/bundle_a_r7_to_r10_runtime_core/actual/"
               "bundle_a_result.json"
    )
    bundle_b = read_json(
        root / "release/bundle_b_r11_to_r13_broker_multi_account/"
               "actual/bundle_b_result.json"
    )
    diagnostics = read_json(
        root / "release/bundle_c_r14_to_r15_final_operations/actual/"
               "final_diagnostics.json"
    )
    paper_certificate = read_json(
        root / "release/actual_validation_control_center/actual/"
               "paper_completion_certificate.json"
    )
    production_certificate = read_json(
        root / "release/r1_production_deployment_preparation/actual/"
               "production_release_certificate.json"
    )

    checks = {
        "bundle_a_complete": bundle_a.get("status") == "PASS",
        "bundle_b_complete": bundle_b.get("status") == "PASS",
        "final_diagnostics_pass": diagnostics.get("status") == "PASS",
        "paper_completion_certificate": (
            paper_certificate.get("eligible") is True
            and paper_certificate.get("paper_complete") is True
        ),
        "production_release_certificate": (
            production_certificate.get("eligible") is True
            and production_certificate.get(
                "production_release_allowed"
            ) is True
        ),
    }

    release_allowed = all(checks.values())
    return {
        "stage": "R15_FINAL_RELEASE_GATE",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "production_candidate_ready": (
            checks["bundle_a_complete"]
            and checks["bundle_b_complete"]
            and checks["final_diagnostics_pass"]
        ),
        "production_release_allowed": release_allowed,
        "release_state": (
            "APPROVED" if release_allowed else "BLOCKED"
        ),
        "automatic_activation_enabled": False,
        "windows_task_registration_allowed": False,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
    }
