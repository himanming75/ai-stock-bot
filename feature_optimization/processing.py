from __future__ import annotations
from decimal import Decimal
from typing import Any


class FeatureNormalizer:
    def min_max(
        self,
        rows: list[dict[str, Decimal]],
    ) -> list[dict[str, Decimal]]:
        if not rows:
            return []
        keys = sorted(rows[0])
        minimums = {key: min(row[key] for row in rows) for key in keys}
        maximums = {key: max(row[key] for row in rows) for key in keys}

        normalized = []
        for row in rows:
            converted = {}
            for key in keys:
                denominator = maximums[key] - minimums[key]
                converted[key] = (
                    Decimal("0")
                    if denominator == 0
                    else (row[key] - minimums[key]) / denominator
                )
            normalized.append(converted)
        return normalized


class CorrelationFilter:
    def select(
        self,
        *,
        correlations: dict[str, dict[str, Decimal]],
        threshold: Decimal,
    ) -> dict[str, Any]:
        selected = []
        dropped = []
        for feature in sorted(correlations):
            conflict = None
            for kept in selected:
                value = abs(
                    correlations.get(feature, {}).get(
                        kept,
                        correlations.get(kept, {}).get(
                            feature, Decimal("0")
                        ),
                    )
                )
                if value >= threshold:
                    conflict = kept
                    break
            if conflict is None:
                selected.append(feature)
            else:
                dropped.append({
                    "feature": feature,
                    "correlated_with": conflict,
                })
        return {
            "selected": selected,
            "dropped": dropped,
            "threshold": str(threshold),
        }


class FeatureSelector:
    def rank(
        self,
        *,
        importance: dict[str, Decimal],
        selected_features: list[str],
        maximum_features: int,
    ) -> list[dict[str, Any]]:
        rows = [
            {
                "feature": feature,
                "importance": str(
                    importance.get(feature, Decimal("0")).quantize(
                        Decimal("0.0001")
                    )
                ),
            }
            for feature in selected_features
        ]
        rows.sort(
            key=lambda row: (
                Decimal(row["importance"]),
                row["feature"],
            ),
            reverse=True,
        )
        return rows[:maximum_features]
