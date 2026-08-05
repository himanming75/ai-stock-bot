from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import FusionInput


@dataclass(frozen=True)
class QualityResult:
    confidence: Decimal
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]


class DataQualityGate:
    def __init__(
        self,
        *,
        stale_warning_seconds: int = 900,
        stale_block_seconds: int = 3600,
        minimum_confidence: Decimal = Decimal("0.55"),
    ) -> None:
        self.stale_warning_seconds = stale_warning_seconds
        self.stale_block_seconds = stale_block_seconds
        self.minimum_confidence = minimum_confidence

    def evaluate(self, item: FusionInput) -> QualityResult:
        warnings: list[str] = []
        blockers: list[str] = []
        confidence = max(Decimal("0"), min(Decimal("1"), item.source_confidence))

        if item.source_age_seconds > self.stale_block_seconds:
            blockers.append("SOURCE_DATA_TOO_STALE")
        elif item.source_age_seconds > self.stale_warning_seconds:
            warnings.append("SOURCE_DATA_STALE")
            confidence *= Decimal("0.80")

        if item.source_confidence < self.minimum_confidence:
            blockers.append("SOURCE_CONFIDENCE_TOO_LOW")

        if item.spread_bps < 0:
            blockers.append("INVALID_NEGATIVE_SPREAD")
        if item.realized_volatility < 0:
            blockers.append("INVALID_NEGATIVE_VOLATILITY")
        if item.volume_ratio < 0:
            blockers.append("INVALID_NEGATIVE_VOLUME")
        if item.liquidity_score < Decimal("0.35"):
            warnings.append("LOW_LIQUIDITY")
            confidence *= Decimal("0.85")
        if item.spread_bps > Decimal("35"):
            warnings.append("WIDE_SPREAD")
            confidence *= Decimal("0.85")
        if item.event_risk > Decimal("0.85"):
            warnings.append("ELEVATED_EVENT_RISK")
            confidence *= Decimal("0.90")

        return QualityResult(
            confidence=max(Decimal("0"), min(Decimal("1"), confidence)),
            warnings=tuple(sorted(set(warnings))),
            blockers=tuple(sorted(set(blockers))),
        )
