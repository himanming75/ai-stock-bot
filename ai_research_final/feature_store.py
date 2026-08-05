from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class FeatureStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def register(
        self,
        *,
        feature_set_name: str,
        schema_version: int,
        features: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "feature_set_name": feature_set_name,
            "schema_version": schema_version,
            "features": sorted(features),
            "metadata": metadata,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        record = {
            **payload,
            "fingerprint": fingerprint,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "actual_training_data_written": False,
        }
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{feature_set_name}_v{schema_version}.json"
        path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return record
