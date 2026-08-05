from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any


class DatasetBuilder:
    def build(
        self,
        *,
        symbols: list[str],
        feature_rows: list[dict[str, Decimal]],
        labels: list[Decimal],
        feature_names: list[str],
    ) -> dict[str, Any]:
        if not (
            len(symbols) == len(feature_rows) == len(labels)
        ):
            raise ValueError("DATASET_LENGTH_MISMATCH")

        rows = []
        for symbol, features, label in zip(
            symbols, feature_rows, labels
        ):
            rows.append({
                "symbol": symbol,
                "features": {
                    key: str(features.get(key, Decimal("0")))
                    for key in feature_names
                },
                "label": str(label),
            })

        raw = json.dumps(rows, sort_keys=True, separators=(",", ":"))
        return {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(rows),
            "feature_count": len(feature_names),
            "feature_names": feature_names,
            "rows": rows,
            "dataset_fingerprint": hashlib.sha256(
                raw.encode("utf-8")
            ).hexdigest(),
            "actual_model_training_performed": False,
        }
