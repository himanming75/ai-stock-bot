from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .credential_vault import validate_vault_metadata


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def evaluate_credential_bootstrap_gate(
    root: Path,
    *,
    mode: str,
) -> dict[str, Any]:
    normalized = mode.lower()
    actual = (
        root / "release/r3_secure_credential_storage/actual"
    )
    metadata = _read(
        actual / f"{normalized}_vault_metadata.json"
    )
    payload = actual / f"{normalized}_credentials.dpapi"

    validation = (
        validate_vault_metadata(
            mode=normalized,
            metadata=metadata,
        )
        if metadata
        else {
            "valid": False,
            "checks": {},
            "failed": ["metadata_missing"],
        }
    )

    r1_certificate_path = (
        root / "release/r1_production_deployment_preparation/"
               "actual/production_release_certificate.json"
    )
    r1 = _read(r1_certificate_path)

    checks = {
        "vault_metadata_valid": validation["valid"],
        "encrypted_payload_present": payload.exists(),
        "mode_valid": normalized in {"paper", "live"},
        "paper_bootstrap_allowed_without_r1": (
            normalized == "paper"
        ),
        "live_requires_r1_release": (
            normalized != "live"
            or (
                r1.get("eligible") is True
                and r1.get("production_release_allowed") is True
            )
        ),
    }

    allowed = all([
        checks["vault_metadata_valid"],
        checks["encrypted_payload_present"],
        checks["mode_valid"],
        (
            checks["paper_bootstrap_allowed_without_r1"]
            if normalized == "paper"
            else checks["live_requires_r1_release"]
        ),
    ])

    return {
        "stage": "R3_CREDENTIAL_BOOTSTRAP_GATE",
        "mode": normalized,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "bootstrap_allowed": allowed,
        "automatic_broker_start_enabled": False,
        "automatic_order_submission_enabled": False,
    }
