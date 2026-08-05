from __future__ import annotations
from decimal import Decimal
from typing import Any


class PerformanceAttribution:
    def calculate(
        self,
        *,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        by_symbol: dict[str, Decimal] = {}
        by_sector: dict[str, Decimal] = {}
        by_strategy: dict[str, Decimal] = {}
        total = Decimal("0")

        for record in records:
            pnl = Decimal(str(record["pnl"]))
            total += pnl
            by_symbol[record["symbol"]] = by_symbol.get(
                record["symbol"], Decimal("0")
            ) + pnl
            by_sector[record["sector"]] = by_sector.get(
                record["sector"], Decimal("0")
            ) + pnl
            by_strategy[record["strategy_id"]] = by_strategy.get(
                record["strategy_id"], Decimal("0")
            ) + pnl

        def serialize(values):
            return [
                {
                    "key": key,
                    "pnl": str(value.quantize(Decimal("0.01"))),
                    "contribution_pct": str(
                        (value / total * Decimal("100")).quantize(
                            Decimal("0.01")
                        )
                        if total != 0 else Decimal("0")
                    ),
                }
                for key, value in sorted(
                    values.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ]

        return {
            "total_pnl": str(total.quantize(Decimal("0.01"))),
            "by_symbol": serialize(by_symbol),
            "by_sector": serialize(by_sector),
            "by_strategy": serialize(by_strategy),
        }
