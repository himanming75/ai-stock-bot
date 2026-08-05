from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
LIVE_ENDPOINT = "https://api.alpaca.markets"


def fingerprint(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _required_files(root: Path) -> dict[str, bool]:
    paths = {
        "git_repository": root / ".git",
        "paper_vault_payload": (
            root / "release/r3_secure_credential_storage/actual/"
                   "paper_credentials.dpapi"
        ),
        "paper_vault_metadata": (
            root / "release/r3_secure_credential_storage/actual/"
                   "paper_vault_metadata.json"
        ),
        "credential_import_script": (
            root / "IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1"
        ),
        "actual_validation_module": (
            root / "broker_integration/actual_validation.py"
        ),
        "r16_r20_result": (
            root / "release/r16_to_r20_realtime_paper_ops/actual/"
                   "r16_to_r20_result.json"
        ),
        "kill_switch_state": (
            root / "release/operations_bundle/actual/"
                   "l1_safety_preparation_result.json"
        ),
    }
    return {key: path.exists() for key, path in paths.items()}


def qualify(root: Path) -> dict[str, Any]:
    metadata_path = (
        root / "release/r3_secure_credential_storage/actual/"
               "paper_vault_metadata.json"
    )
    metadata = read_json(metadata_path)
    r16_r20 = read_json(
        root / "release/r16_to_r20_realtime_paper_ops/actual/"
               "r16_to_r20_result.json"
    )
    l1_safety = read_json(
        root / "release/operations_bundle/actual/"
               "l1_safety_preparation_result.json"
    )

    api_key = os.environ.get("APCA_API_KEY_ID", "")
    api_secret = os.environ.get("APCA_API_SECRET_KEY", "")
    base_url = os.environ.get("APCA_API_BASE_URL", "")
    live_key = os.environ.get("APCA_LIVE_API_KEY_ID", "")
    live_secret = os.environ.get("APCA_LIVE_API_SECRET_KEY", "")
    live_base_url = os.environ.get("APCA_LIVE_API_BASE_URL", "")

    required_files = _required_files(root)
    disk = shutil.disk_usage(root)
    python_version = sys.version_info

    checks = {
        "windows_environment": platform.system() == "Windows",
        "python_supported": python_version >= (3, 11),
        "virtual_environment_active": (
            sys.prefix != getattr(sys, "base_prefix", sys.prefix)
            or ".venv" in str(sys.executable).lower()
        ),
        "required_files_present": all(required_files.values()),
        "paper_vault_schema_valid": (
            metadata.get("schema_version") in {1, 2}
        ),
        "paper_vault_encrypted": (
            metadata.get("encryption_provider")
            in {
                "WINDOWS_DPAPI_CURRENT_USER",
                "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING",
            }
        ),
        "paper_metadata_endpoint_valid": (
            metadata.get("base_url") == PAPER_ENDPOINT
        ),
        "credential_environment_loaded": bool(api_key and api_secret),
        "paper_environment_endpoint_valid": base_url == PAPER_ENDPOINT,
        "paper_endpoint_not_live": base_url != LIVE_ENDPOINT,
        "key_fingerprint_matches": (
            bool(api_key)
            and fingerprint(api_key)
            == metadata.get("key_fingerprint")
        ),
        "secret_fingerprint_matches": (
            bool(api_secret)
            and fingerprint(api_secret)
            == metadata.get("secret_fingerprint")
        ),
        "live_environment_absent": not (
            live_key or live_secret or live_base_url
        ),
        "r16_r20_preparation_pass": r16_r20.get("status") == "PASS",
        "r16_dispatch_blocked": (
            r16_r20.get("actual_order_dispatch_performed") is False
            and r16_r20.get("automatic_order_submission_enabled") is False
        ),
        "l1_live_activation_blocked": (
            l1_safety.get("live_activation_allowed") is False
            and l1_safety.get("live_write_enabled") is False
            and l1_safety.get("live_network_enabled") is False
        ),
        "free_disk_over_500mb": disk.free > 500 * 1024 * 1024,
    }

    failed = [key for key, value in checks.items() if not value]
    qualified = not failed

    return {
        "stage": "P1_ACTUAL_ENVIRONMENT_QUALIFICATION",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "qualified": qualified,
        "status": "PASS" if qualified else "FAIL",
        "checks": checks,
        "failed": failed,
        "required_files": required_files,
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "python_executable": str(sys.executable),
            "virtual_environment_detected": checks[
                "virtual_environment_active"
            ],
            "paper_base_url": base_url,
            "paper_key_fingerprint": fingerprint(api_key),
            "paper_secret_fingerprint": fingerprint(api_secret),
            "raw_credentials_printed": False,
            "raw_credentials_stored": False,
            "free_disk_bytes": disk.free,
        },
        "p1_actual_environment_validated": qualified,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_action": (
            "P2_ACTUAL_PAPER_BROKER_READ_VALIDATION"
            if qualified
            else "FIX_P1_FAILED_CHECKS"
        ),
    }
