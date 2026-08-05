from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


class CredentialHealthMonitor:
    def inspect(self, root: Path) -> dict[str, Any]:
        path = (
            root / "release/r3_secure_credential_storage/actual/"
                   "paper_vault_metadata.json"
        )
        metadata = {}
        if path.exists():
            metadata = json.loads(
                path.read_text(encoding="utf-8-sig")
            )

        checks = {
            "metadata_present": path.exists(),
            "paper_endpoint": (
                metadata.get("base_url")
                == "https://paper-api.alpaca.markets"
            ),
            "key_fingerprint_present": bool(
                metadata.get("key_fingerprint")
            ),
            "secret_fingerprint_present": bool(
                metadata.get("secret_fingerprint")
            ),
            "encrypted_payload_named": bool(
                metadata.get("encrypted_payload_file")
            ),
            "plaintext_absent": (
                "api_key" not in metadata
                and "secret_key" not in metadata
            ),
        }
        return {
            "stage": "CREDENTIAL_HEALTH",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "environment_credentials_read": False,
            "raw_credentials_printed": False,
            "raw_credentials_stored": False,
            "network_call_performed": False,
        }
