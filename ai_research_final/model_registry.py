from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class ModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root

    def register_metadata(
        self,
        *,
        model_name: str,
        model_version: str,
        algorithm: str,
        feature_fingerprint: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "model_name": model_name,
            "model_version": model_version,
            "algorithm": algorithm,
            "feature_fingerprint": feature_fingerprint,
            "metrics": metrics,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        record = {
            **payload,
            "model_fingerprint": fingerprint,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "model_binary_present": False,
            "actual_model_training_performed": False,
            "actual_model_activation_performed": False,
        }
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{model_name}_{model_version}.json"
        path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return record

    def rollback_preview(
        self,
        *,
        current_version: str,
        target_version: str,
    ) -> dict[str, Any]:
        return {
            "current_version": current_version,
            "target_version": target_version,
            "rollback_allowed": bool(target_version),
            "actual_rollback_performed": False,
            "operator_approval_required": True,
        }
