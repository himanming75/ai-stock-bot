from __future__ import annotations

from decimal import Decimal

from .models import DecisionPolicy


class DecisionPolicyGate:
    def evaluate_symbol(self, item: dict, policy: DecisionPolicy, risk_mode: str) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        blockers: list[str] = list(item.get("blockers", []))
        score = Decimal(str(item.get("composite_score", "0")))
        confidence = Decimal(str(item.get("confidence", "0")))
        bias = str(item.get("trade_bias", "BLOCKED")).upper()

        if score < policy.minimum_score:
            blockers.append("SCORE_BELOW_SELECTION_THRESHOLD")
        else:
            reasons.append("SCORE_THRESHOLD_PASS")

        if confidence < policy.minimum_confidence:
            blockers.append("CONFIDENCE_BELOW_SELECTION_THRESHOLD")
        else:
            reasons.append("CONFIDENCE_THRESHOLD_PASS")

        if bias in policy.blocked_biases:
            blockers.append(f"BIAS_{bias}_NOT_SELECTABLE")
        elif bias == "LONG":
            reasons.append("LONG_BIAS")
        elif bias == "NEUTRAL" and policy.neutral_selection_allowed:
            reasons.append("NEUTRAL_BIAS_ALLOWED")
        else:
            blockers.append("TRADE_BIAS_NOT_ALLOWED")

        if risk_mode == "RISK_OFF":
            blockers.append("MARKET_RISK_OFF")
        elif risk_mode == "RISK_ON":
            reasons.append("MARKET_RISK_ON")
        else:
            reasons.append("MARKET_NEUTRAL")

        return sorted(set(reasons)), sorted(set(blockers))
