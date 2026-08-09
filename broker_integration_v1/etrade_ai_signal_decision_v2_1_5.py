from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategyRecommendation:
    symbol: str
    action: str
    confidence: Decimal
    quantity: Decimal
    strategy_id: str
    reason: str = ""


@dataclass(frozen=True)
class SignalDecisionPolicy:
    minimum_confidence: Decimal = Decimal("0.60")
    allowed_actions: tuple = ("BUY","SELL","HOLD")

    def validate(self):
        if self.minimum_confidence < 0 or self.minimum_confidence > 1:
            raise ValueError("minimum_confidence must be between 0 and 1.")
        return self


def normalize_strategy_recommendation(payload):
    if not isinstance(payload,dict):
        raise TypeError("Strategy recommendation payload must be a dict.")

    symbol=str(payload.get("symbol") or "").upper().strip()
    action=str(payload.get("action") or "").upper().strip()
    strategy_id=str(payload.get("strategy_id") or "").strip()
    reason=str(payload.get("reason") or "")

    if not symbol:
        raise ValueError("symbol is required.")
    if action not in {"BUY","SELL","HOLD"}:
        raise ValueError("action must be BUY, SELL, or HOLD.")
    if not strategy_id:
        raise ValueError("strategy_id is required.")

    confidence=Decimal(str(payload.get("confidence","0")))
    quantity=Decimal(str(payload.get("quantity","0")))

    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1.")
    if action in {"BUY","SELL"} and quantity <= 0:
        raise ValueError("BUY/SELL quantity must be positive.")
    if action=="HOLD":
        quantity=Decimal("0")

    return StrategyRecommendation(
        symbol=symbol,
        action=action,
        confidence=confidence,
        quantity=quantity,
        strategy_id=strategy_id,
        reason=reason,
    )


def decide_signal(recommendation,policy=None):
    policy=(policy or SignalDecisionPolicy()).validate()

    if recommendation.action not in policy.allowed_actions:
        return {
            "decision":"BLOCK",
            "reason":"ACTION_NOT_ALLOWED",
            "order_eligible":False,
        }

    if recommendation.action=="HOLD":
        return {
            "decision":"HOLD",
            "reason":"STRATEGY_HOLD",
            "order_eligible":False,
        }

    if recommendation.confidence < policy.minimum_confidence:
        return {
            "decision":"HOLD",
            "reason":"CONFIDENCE_BELOW_THRESHOLD",
            "order_eligible":False,
        }

    return {
        "decision":recommendation.action,
        "reason":"PASS_SIGNAL_DECISION_GATE",
        "order_eligible":True,
    }
