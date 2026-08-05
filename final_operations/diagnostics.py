from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import shutil

from .io import read_json


def build_final_diagnostics(root: Path) -> dict[str, Any]:
    bundle_a = read_json(
        root / "release/bundle_a_r7_to_r10_runtime_core/actual/"
               "bundle_a_result.json"
    )
    bundle_b = read_json(
        root / "release/bundle_b_r11_to_r13_broker_multi_account/"
               "actual/bundle_b_result.json"
    )
    r1 = read_json(
        root / "release/r1_production_deployment_preparation/actual/"
               "r1_readiness_result.json"
    )
    r2 = read_json(
        root / "release/r2_windows_scheduler_service_preparation/"
               "actual/r2_readiness_result.json"
    )
    r3 = read_json(
        root / "release/r3_secure_credential_storage/actual/"
               "r3_vault_status.json"
    )
    r6 = read_json(
        root / "release/r6_runtime_session_manager/actual/"
               "last_session_preview.json"
    )

    disk = shutil.disk_usage(root)
    checks = {
        "bundle_a_pass": bundle_a.get("status") == "PASS",
        "bundle_b_pass": bundle_b.get("status") == "PASS",
        "r1_readiness_pass": r1.get("status") == "PASS",
        "r2_readiness_pass": r2.get("status") == "PASS",
        "paper_vault_valid": (
            r3.get("paper", {}).get("valid") is True
        ),
        "r6_session_preview_complete": (
            r6.get("state") == "PREVIEW_SESSION_COMPLETE"
        ),
        "free_disk_over_250mb": disk.free > 250 * 1024 * 1024,
        "bundle_a_network_off": (
            bundle_a.get("broker_network_enabled") is False
        ),
        "bundle_b_network_unused": (
            bundle_b.get("actual_network_used") is False
        ),
        "bundle_a_write_off": (
            bundle_a.get("broker_write_enabled") is False
        ),
        "bundle_b_write_unused": (
            bundle_b.get("actual_write_used") is False
        ),
        "bundle_a_orders_zero": (
            bundle_a.get("actual_paper_orders_submitted") == 0
            and bundle_a.get("actual_live_orders_submitted") == 0
        ),
        "bundle_b_orders_zero": (
            bundle_b.get("actual_paper_orders_submitted") == 0
            and bundle_b.get("actual_live_orders_submitted") == 0
        ),
    }

    return {
        "stage": "R14_FINAL_DIAGNOSTICS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "status": "PASS" if all(checks.values()) else "FAIL",
        "free_disk_bytes": disk.free,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
