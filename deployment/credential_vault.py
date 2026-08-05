from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
LIVE_ENDPOINT = "https://api.alpaca.markets"
PROVIDERS = {
    "WINDOWS_DPAPI_CURRENT_USER",
    "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING",
}


def fingerprint(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def validate_vault_metadata(
    *,
    mode: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    normalized = mode.strip().lower()
    expected_endpoint = (
        PAPER_ENDPOINT if normalized == "paper" else LIVE_ENDPOINT
    )
    checks = {
        "mode_valid": normalized in {"paper", "live"},
        "schema_version": metadata.get("schema_version") in {1, 2},
        "encryption_provider": (
            metadata.get("encryption_provider") in PROVIDERS
        ),
        "endpoint_matches_mode": (
            metadata.get("base_url") == expected_endpoint
        ),
        "key_fingerprint_present": bool(
            metadata.get("key_fingerprint")
        ),
        "secret_fingerprint_present": bool(
            metadata.get("secret_fingerprint")
        ),
        "plaintext_credentials_absent": (
            "api_key" not in metadata
            and "secret_key" not in metadata
        ),
        "encrypted_payload_present": bool(
            metadata.get("encrypted_payload_file")
        ),
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "valid": all(checks.values()),
        "mode": normalized,
    }


def build_rotation_record(
    *,
    mode: str,
    old_key_fingerprint: str,
    new_key_fingerprint: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "stage": "R3_CREDENTIAL_ROTATION",
        "mode": mode.lower(),
        "rotated_at": datetime.now(timezone.utc).isoformat(),
        "old_key_fingerprint": old_key_fingerprint,
        "new_key_fingerprint": new_key_fingerprint,
        "reason": reason,
        "raw_credentials_recorded": False,
    }


def read_vault_status(root: Path) -> dict[str, Any]:
    actual = (
        root / "release/r3_secure_credential_storage/actual"
    )
    modes = {}
    for mode in ("paper", "live"):
        metadata_path = actual / f"{mode}_vault_metadata.json"
        payload_path = actual / f"{mode}_credentials.dpapi"
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(
                    metadata_path.read_text(encoding="utf-8-sig")
                )
            except Exception:
                metadata = {"read_error": True}
        modes[mode] = {
            "metadata_present": metadata_path.exists(),
            "encrypted_payload_present": payload_path.exists(),
            "valid": (
                validate_vault_metadata(
                    mode=mode,
                    metadata=metadata,
                )["valid"]
                if metadata
                else False
            ),
            "schema_version": metadata.get("schema_version"),
            "encryption_provider": metadata.get(
                "encryption_provider", ""
            ),
            "key_fingerprint": metadata.get(
                "key_fingerprint", ""
            ),
            "secret_fingerprint": metadata.get(
                "secret_fingerprint", ""
            ),
        }

    return {
        "stage": "R3_VAULT_STATUS",
        "paper": modes["paper"],
        "live": modes["live"],
        "paper_live_separated": True,
        "plaintext_secret_files_expected": False,
        "network_used": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
