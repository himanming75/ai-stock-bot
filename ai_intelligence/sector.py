from __future__ import annotations
from decimal import Decimal
from typing import Any


class SectorRotationAnalyzer:
    def rank(
        self,
        sector_returns: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows = []
        for sector, values in sector_returns.items():
            return_5 = Decimal(str(values.get("return_5", "0")))
            return_20 = Decimal(str(values.get("return_20", "0")))
            breadth = Decimal(str(values.get("breadth", "0.5")))
            score = (
                return_5 * Decimal("3")
                + return_20 * Decimal("2")
                + breadth * Decimal("0.5")
            )
            normalized = max(
                Decimal("0"),
                min(Decimal("1"), Decimal("0.5") + score),
            )
            rows.append({
                "sector": sector,
                "score": str(normalized.quantize(Decimal("0.0001"))),
                "return_5": str(return_5),
                "return_20": str(return_20),
                "breadth": str(breadth),
            })
        return sorted(
            rows,
            key=lambda item: (Decimal(item["score"]), item["sector"]),
            reverse=True,
        )
