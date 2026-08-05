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


def evaluate_session_gate(root: Path, broker_mode: str) -> dict[str, Any]:
    mode = broker_mode.lower()
    paper = _read(
        root / "release/actual_validation_control_center/actual/"
               "paper_completion_certificate.json"
    )
    production = _read(
        root / "release/r1_production_deployment_preparation/actual/"
               "production_release_certificate.json"
    )

    checks = {
        "mode_valid": mode in {"paper", "live"},
        "paper_preview_allowed": mode == "paper",
        "live_requires_paper_complete": (
            mode != "live"
            or (
                paper.get("eligible") is True
                and paper.get("paper_complete") is True
            )
        ),
        "live_requires_production_release": (
            mode != "live"
            or (
                production.get("eligible") is True
                and production.get("production_release_allowed") is True
            )
        ),
    }
    allowed = checks["mode_valid"] and (
        checks["paper_preview_allowed"]
        or (
            checks["live_requires_paper_complete"]
            and checks["live_requires_production_release"]
        )
    )
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "session_preview_allowed": allowed,
        "actual_broker_session_allowed": False,
    }
