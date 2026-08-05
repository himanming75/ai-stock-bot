from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class ConfigurationSchemaValidator:
    REQUIRED = {
        "schema_version",
        "environment",
        "broker_mode",
        "network_enabled",
        "write_enabled",
        "automatic_order_submission_enabled",
    }

    def validate(self, value: dict[str, Any]) -> dict[str, Any]:
        missing = sorted(self.REQUIRED - set(value))
        type_errors = []

        if "schema_version" in value and not isinstance(
            value["schema_version"], int
        ):
            type_errors.append("schema_version:EXPECTED_INT")

        for key in (
            "network_enabled",
            "write_enabled",
            "automatic_order_submission_enabled",
        ):
            if key in value and not isinstance(value[key], bool):
                type_errors.append(f"{key}:EXPECTED_BOOL")

        safety_errors = []
        if value.get("broker_mode") == "live":
            safety_errors.append("LIVE_MODE_REJECTED")
        if value.get("network_enabled") is True:
            safety_errors.append("NETWORK_MUST_REMAIN_DISABLED")
        if value.get("write_enabled") is True:
            safety_errors.append("WRITE_MUST_REMAIN_DISABLED")
        if value.get("automatic_order_submission_enabled") is True:
            safety_errors.append("AUTOMATIC_ORDER_SUBMISSION_REJECTED")

        return {
            "valid": not missing and not type_errors and not safety_errors,
            "missing_fields": missing,
            "type_errors": type_errors,
            "safety_errors": safety_errors,
        }


class ConfigurationVersionManager:
    def fingerprint(self, value: dict[str, Any]) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def create_record(
        self,
        *,
        name: str,
        value: dict[str, Any],
        previous_fingerprint: str = "",
    ) -> dict[str, Any]:
        current = self.fingerprint(value)
        return {
            "name": name,
            "schema_version": value.get("schema_version"),
            "fingerprint": current,
            "previous_fingerprint": previous_fingerprint,
            "changed": current != previous_fingerprint,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "actual_configuration_applied": False,
            "operator_approval_required": True,
        }
