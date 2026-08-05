from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def evaluate_runtime_bridge_gate(
    root: Path,
    *,
    broker_mode: str,
) -> dict[str, Any]:
    mode = broker_mode.lower()

    paper_certificate = _read(
        root / "release/actual_validation_control_center/actual/"
               "paper_completion_certificate.json"
    )
    production_certificate = _read(
        root / "release/r1_production_deployment_preparation/actual/"
               "production_release_certificate.json"
    )

    checks = {
        "mode_valid": mode in {"paper", "live"},
        "paper_mode_allowed_for_preview": mode == "paper",
        "live_requires_paper_completion": (
            mode != "live"
            or (
                paper_certificate.get("eligible") is True
                and paper_certificate.get("paper_complete") is True
            )
        ),
        "live_requires_production_release": (
            mode != "live"
            or (
                production_certificate.get("eligible") is True
                and production_certificate.get(
                    "production_release_allowed"
                ) is True
            )
        ),
    }

    preview_allowed = (
        checks["mode_valid"]
        and (
            checks["paper_mode_allowed_for_preview"]
            or (
                checks["live_requires_paper_completion"]
                and checks["live_requires_production_release"]
            )
        )
    )

    return {
        "stage": "R5_RUNTIME_BRIDGE_GATE",
        "broker_mode": mode,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "preview_allowed": preview_allowed,
        "actual_runtime_activation_performed": False,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
    }
