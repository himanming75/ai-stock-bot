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


def evaluate_windows_activation_gate(root: Path) -> dict[str, Any]:
    r1 = _read(
        root / "release/r1_production_deployment_preparation/actual/"
               "production_release_certificate.json",
        {
            "eligible": False,
            "production_release_allowed": False,
        },
    )

    checks = {
        "r1_release_certificate_present": (
            r1.get("stage") == "PRODUCTION_RELEASE_CERTIFICATE"
        ),
        "r1_release_eligible": r1.get("eligible") is True,
        "production_release_allowed": (
            r1.get("production_release_allowed") is True
        ),
    }

    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "windows_task_activation_allowed": all(checks.values()),
        "windows_service_activation_allowed": False,
        "automatic_activation_enabled": False,
    }
