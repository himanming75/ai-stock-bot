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


def evaluate_profile_activation_gate(
    root: Path,
    *,
    broker_mode: str,
) -> dict[str, Any]:
    mode = broker_mode.lower()
    r1 = _read(
        root / "release/r1_production_deployment_preparation/actual/"
               "production_release_certificate.json"
    )
    paper = _read(
        root / "release/actual_validation_control_center/actual/"
               "paper_completion_certificate.json"
    )

    checks = {
        "mode_valid": mode in {"paper", "live"},
        "paper_mode_selected": mode == "paper",
        "paper_certificate_present_for_live": (
            mode != "live"
            or (
                paper.get("eligible") is True
                and paper.get("paper_complete") is True
            )
        ),
        "r1_release_present_for_live": (
            mode != "live"
            or (
                r1.get("eligible") is True
                and r1.get("production_release_allowed") is True
            )
        ),
    }

    allowed = (
        checks["mode_valid"]
        and (
            checks["paper_mode_selected"]
            or (
                checks["paper_certificate_present_for_live"]
                and checks["r1_release_present_for_live"]
            )
        )
    )

    return {
        "stage": "R4_PROFILE_ACTIVATION_GATE",
        "broker_mode": mode,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "activation_preview_allowed": allowed,
        "actual_activation_performed": False,
        "automatic_order_submission_enabled": False,
    }
