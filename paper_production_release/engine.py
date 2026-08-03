from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_production_release.discovery import discover_layout
from paper_production_release.environment import validate_environment
from paper_production_release.integrity import build_integrity_manifest
from paper_production_release.io import (
    digest_payload,
    write_json,
)
from paper_production_release.prerequisites import evaluate_prerequisites


def current_commit(root: Path) -> str:
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        value = "UNKNOWN"
    return value


def build_release(root: Path) -> dict[str, Any]:
    observed_at = datetime.now(timezone.utc).isoformat()
    layout = discover_layout(root)
    environment = validate_environment(root)
    prerequisites = evaluate_prerequisites(root)
    integrity = build_integrity_manifest(root)

    technical_checks = {
        "layout_valid": layout["layout_valid"],
        "environment_valid": environment["passed"],
        "integrity_valid": integrity["integrity_passed"],
        "orchestrator_ready": prerequisites["checks"][
            "orchestrator_ready"
        ],
        "robustness_validated": prerequisites["checks"][
            "robustness_validated"
        ],
        "multi_asset_certified": prerequisites["checks"][
            "multi_asset_certified"
        ],
        "web_ui_ready": prerequisites["checks"]["web_ui_ready"],
    }
    technical_ready = all(technical_checks.values())
    full_ready = technical_ready and prerequisites["ready"]

    if full_ready:
        state = "PAPER_AUTOMATED_TRADING_PRODUCTION_READY"
        next_phase = "V89_OPTIONAL_BROKER_READ_ONLY"
    elif technical_ready and prerequisites["time_based_pending"]:
        state = "PAPER_PRODUCTION_RELEASE_PENDING_PREREQUISITES"
        next_phase = "COMPLETE_TIME_BASED_PAPER_VALIDATION"
    else:
        state = "PAPER_PRODUCTION_RELEASE_BLOCKED"
        next_phase = "RESOLVE_RELEASE_BLOCKERS"

    status = "PASS" if technical_ready else "BLOCKED"

    certificate_body = {
        "stage": "V88.24",
        "stage_range": "V88.17-V88.24",
        "state": state,
        "status": status,
        "observed_at": observed_at,
        "commit": current_commit(root),
        "technical_ready": technical_ready,
        "production_ready": full_ready,
        "technical_checks": technical_checks,
        "blocking_prerequisites": prerequisites[
            "blocking_prerequisites"
        ],
        "time_based_pending": prerequisites["time_based_pending"],
        "system_based_pending": prerequisites["system_based_pending"],
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
    certificate = {
        **certificate_body,
        "certificate_sha256": digest_payload(certificate_body),
    }

    result = {
        **certificate_body,
        "implementation_type": "PAPER_PRODUCTION_RELEASE_GATE",
        "layout": layout,
        "environment": environment,
        "prerequisites": prerequisites,
        "integrity": integrity,
        "certificate": certificate,
        "backup_supported": True,
        "rollback_supported": True,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "automatic_broker_execution_enabled": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "next_phase": next_phase,
    }

    actual = root / "release/v88_17_to_v88_24/actual"
    write_json(actual / "paper_production_release_result.json", result)
    write_json(actual / "paper_production_release_certificate.json", certificate)
    write_json(actual / "paper_release_integrity_manifest.json", integrity)
    write_json(actual / "paper_release_environment_report.json", environment)
    write_json(actual / "paper_release_prerequisites.json", prerequisites)
    write_json(actual / "paper_production_release_dashboard_state.json", {
        "paper_production_release_state": state,
        "status": status,
        "technical_ready": technical_ready,
        "production_ready": full_ready,
        "blocking_prerequisites": prerequisites[
            "blocking_prerequisites"
        ],
        "observed_at": observed_at,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return result
