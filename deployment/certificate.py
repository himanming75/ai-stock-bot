from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .gates import evaluate_production_gates


def generate_release_certificate(root: Path) -> dict[str, Any]:
    gates = evaluate_production_gates(root)
    eligible = gates["production_release_allowed"]
    value = {
        "stage": "PRODUCTION_RELEASE_CERTIFICATE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "eligible": eligible,
        "production_release_allowed": eligible,
        "gates": gates,
        "status": "PASS" if eligible else "BLOCKED",
        "automatic_activation_enabled": False,
        "actual_live_orders_submitted": 0,
    }
    path = (
        root / "release/r1_production_deployment_preparation/actual/"
               "production_release_certificate.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
