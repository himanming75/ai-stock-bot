from __future__ import annotations
from collections import defaultdict


VALID_ACTIONS = {"BUY", "SELL", "HOLD"}


def arbitrate(votes: list[dict], fallback_action: str, fallback_confidence: float) -> dict:
    scores: dict[str, float] = defaultdict(float)
    details: list[dict] = []

    for vote in votes:
        action = str(vote.get("action", "HOLD")).upper()
        if action not in VALID_ACTIONS:
            continue
        confidence = max(0.0, min(1.0, float(vote.get("confidence", 0.0))))
        weight = max(0.0, float(vote.get("weight", 1.0)))
        contribution = confidence * weight
        scores[action] += contribution
        details.append({
            "strategy": str(vote.get("strategy", "UNKNOWN")),
            "action": action,
            "confidence": round(confidence, 6),
            "weight": round(weight, 6),
            "contribution": round(contribution, 6),
        })

    if not scores:
        action = fallback_action if fallback_action in VALID_ACTIONS else "HOLD"
        confidence = max(0.0, min(1.0, fallback_confidence))
        return {
            "action": action,
            "confidence": round(confidence, 6),
            "vote_scores": {action: round(confidence, 6)},
            "votes": [],
            "conflict": False,
        }

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    action, top = ranked[0]
    total = sum(scores.values())
    confidence = top / total if total else 0.0
    nonzero_actions = [name for name, score in scores.items() if score > 0]

    return {
        "action": action,
        "confidence": round(confidence, 6),
        "vote_scores": {k: round(v, 6) for k, v in sorted(scores.items())},
        "votes": details,
        "conflict": len(nonzero_actions) > 1,
    }
