from __future__ import annotations
from decimal import Decimal
from typing import Any


class StrategyExplanationEngine:
    def explain(
        self,
        *,
        scanner_row: dict[str, Any],
        regime: dict[str, Any],
        event_result: dict[str, Any],
        earnings: dict[str, Any],
    ) -> dict[str, Any]:
        indicators = scanner_row["indicators"]
        reasons = []
        warnings = []

        if Decimal(indicators["last_close"]) > Decimal(indicators["sma_20"]):
            reasons.append("PRICE_ABOVE_20_PERIOD_AVERAGE")
        if Decimal(indicators["momentum_5"]) > 0:
            reasons.append("POSITIVE_5_PERIOD_MOMENTUM")
        if Decimal(indicators["relative_volume"]) > Decimal("1"):
            reasons.append("ABOVE_AVERAGE_VOLUME")
        if regime["regime"] == "BULL_TREND":
            reasons.append("BULL_MARKET_REGIME")
        if Decimal(event_result["event_score"]) > Decimal("0.5"):
            reasons.append("POSITIVE_EVENT_BALANCE")

        if regime["regime"] in {"HIGH_VOLATILITY", "BEAR_TREND"}:
            warnings.append("DEFENSIVE_MARKET_REGIME")
        if earnings.get("block_new_position") is True:
            warnings.append("EARNINGS_IMMINENT")
        if Decimal(event_result["risk_penalty"]) > Decimal("0.25"):
            warnings.append("NEGATIVE_EVENT_RISK")

        return {
            "symbol": scanner_row["symbol"],
            "decision_score": scanner_row["total_score"],
            "reasons": reasons,
            "warnings": warnings,
            "human_summary": (
                f"{scanner_row['symbol']} score {scanner_row['total_score']} "
                f"in {regime['regime']} regime; "
                f"{len(reasons)} supporting reasons and "
                f"{len(warnings)} warnings."
            ),
            "llm_api_used": False,
        }
