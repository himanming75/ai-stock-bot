from __future__ import annotations
from pathlib import Path
from typing import Any
import json


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


class ValidationPreflight:
    def evaluate(self, root: Path) -> dict[str, Any]:
        p1 = read_json(
            root / "release/p1_actual_environment_qualification/actual/"
                   "p1_actual_environment_certificate.json"
        )
        r16 = read_json(
            root / "release/r16_to_r20_realtime_paper_ops/actual/"
                   "r16_to_r20_result.json"
        )
        vault = read_json(
            root / "release/r3_secure_credential_storage/actual/"
                   "paper_vault_metadata.json"
        )

        required = {
            "p1_certificate_present": bool(p1),
            "p1_validated": p1.get(
                "p1_actual_environment_validated"
            ) is True,
            "p2_read_allowed": p1.get(
                "p2_actual_broker_read_allowed"
            ) is True,
            "p3_order_blocked": p1.get(
                "p3_actual_paper_order_allowed"
            ) is False,
            "r16_preparation_pass": r16.get("status") == "PASS",
            "order_dispatch_blocked": (
                r16.get("actual_order_dispatch_performed") is False
            ),
            "paper_vault_metadata_present": bool(vault),
            "paper_endpoint_valid": (
                vault.get("base_url")
                == "https://paper-api.alpaca.markets"
            ),
            "plaintext_credentials_absent": (
                "api_key" not in vault and "secret_key" not in vault
            ),
        }
        return {
            "stage": "VALIDATION_SUPPORT_PREFLIGHT",
            "checks": required,
            "failed": [k for k, v in required.items() if not v],
            "p2_preflight_ready": all(required.values()),
            "p3_preflight_ready": False,
            "operator_confirmation_required": True,
            "network_call_performed": False,
            "order_submission_performed": False,
        }
