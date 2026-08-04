from __future__ import annotations
from .confidence import calculate as calculate_confidence
from .explanation import reasons
from .features import build
from .models import Decision, MarketInput
from .regime import classify
from .risk import level as risk_level
from .scoring import calculate as calculate_score
from .self_review import review
from .validation import validate


def decide(payload: dict) -> Decision:
    value = MarketInput.from_dict(payload)
    errors = validate(value)
    if errors:
        raise ValueError(",".join(errors))

    features = build(value)
    regime = classify(value)
    score = calculate_score(features)
    confidence = calculate_confidence(score, regime, features)

    if score >= 0.18 and confidence >= 55:
        action = "BUY"
    elif score <= -0.18 and confidence >= 55:
        action = "SELL"
    else:
        action = "HOLD"

    return Decision(
        symbol=value.symbol,
        action=action,
        confidence=confidence,
        regime=regime,
        score=score,
        risk_level=risk_level(value, regime),
        reasons=tuple(reasons(value, features, regime)),
        self_review=tuple(review(action, confidence, regime, value)),
    )
