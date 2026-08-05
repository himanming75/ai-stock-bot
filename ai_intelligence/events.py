from __future__ import annotations
from decimal import Decimal
from typing import Any


SEVERITY = {
    "LOW": Decimal("0.10"),
    "MEDIUM": Decimal("0.30"),
    "HIGH": Decimal("0.60"),
    "CRITICAL": Decimal("0.85"),
}


class EventScoringFramework:
    def score(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        if not events:
            return {
                "event_score": "0.5000",
                "risk_penalty": "0.0000",
                "event_count": 0,
                "events": [],
                "external_news_api_used": False,
            }

        positive = Decimal("0")
        negative = Decimal("0")
        normalized = []
        for event in events:
            sentiment = Decimal(str(event.get("sentiment", "0")))
            severity = SEVERITY.get(
                str(event.get("severity", "LOW")).upper(),
                Decimal("0.10"),
            )
            weighted = sentiment * severity
            if weighted >= 0:
                positive += weighted
            else:
                negative += abs(weighted)
            normalized.append({
                "event_type": event.get("event_type", "UNKNOWN"),
                "severity": event.get("severity", "LOW"),
                "sentiment": str(sentiment),
                "weighted_score": str(weighted.quantize(Decimal("0.0001"))),
                "source_mode": event.get("source_mode", "OFFLINE_FIXTURE"),
            })

        event_score = max(
            Decimal("0"),
            min(Decimal("1"), Decimal("0.5") + positive - negative),
        )
        penalty = min(Decimal("1"), negative)
        return {
            "event_score": str(event_score.quantize(Decimal("0.0001"))),
            "risk_penalty": str(penalty.quantize(Decimal("0.0001"))),
            "event_count": len(normalized),
            "events": normalized,
            "external_news_api_used": False,
        }


class EarningsEventFramework:
    def evaluate(
        self,
        *,
        days_until_earnings: int | None,
        surprise_history: Decimal,
    ) -> dict[str, Any]:
        if days_until_earnings is None:
            return {
                "earnings_risk": "NONE",
                "score": "0.5000",
                "block_new_position": False,
            }
        if days_until_earnings <= 1:
            return {
                "earnings_risk": "IMMINENT",
                "score": "0.1500",
                "block_new_position": True,
            }
        score = max(
            Decimal("0"),
            min(Decimal("1"), Decimal("0.5") + surprise_history),
        )
        return {
            "earnings_risk": "UPCOMING" if days_until_earnings <= 7 else "DISTANT",
            "score": str(score.quantize(Decimal("0.0001"))),
            "block_new_position": False,
        }
