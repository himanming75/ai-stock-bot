from __future__ import annotations
from decimal import Decimal
from .models import D, ZERO, clamp, text

DIRECTION = {"BUY": Decimal("1"), "SELL": Decimal("-1"), "HOLD": ZERO}

def fuse_symbol(
    symbol_decision: dict,
    strategy_results: list[dict],
    policy: dict,
    risk_context: dict,
) -> dict:
    symbol = symbol_decision.get("symbol")
    rows = [
        row for row in strategy_results
        if row.get("symbol") == symbol and row.get("status") == "PASS"
    ]
    if not rows:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT_INPUT",
            "decision": "HOLD",
            "raw_score": "0",
            "confidence": "0",
            "agreement_percent": "0",
            "risk_penalty": "0",
            "final_score": "0",
            "reasons": ["NO_USABLE_STRATEGY_RESULTS"],
        }

    buy = sum(1 for row in rows if row.get("signal") == "BUY")
    sell = sum(1 for row in rows if row.get("signal") == "SELL")
    hold = sum(1 for row in rows if row.get("signal") == "HOLD")
    directional = buy + sell
    agreement = (
        Decimal(max(buy, sell)) / Decimal(directional) * Decimal("100")
        if directional else ZERO
    )

    raw = D(symbol_decision.get("combined_score"))
    magnitude = clamp(abs(raw) * D(policy.get("score_scale", "4")))
    agreement_weight = D(policy.get("agreement_weight", "0.55"))
    magnitude_weight = D(policy.get("magnitude_weight", "0.45"))
    confidence = clamp(
        agreement * agreement_weight + magnitude * magnitude_weight
    )

    risk_level = str(risk_context.get("risk_level", "UNKNOWN"))
    penalty_map = policy.get("risk_penalty", {})
    risk_penalty = D(penalty_map.get(risk_level, penalty_map.get("UNKNOWN", "35")))
    final_score = max(ZERO, confidence - risk_penalty)

    min_confidence = D(policy.get("minimum_confidence", "55"))
    min_agreement = D(policy.get("minimum_agreement_percent", "60"))
    base_signal = symbol_decision.get("signal", "HOLD")

    reasons = []
    decision = base_signal
    if base_signal not in {"BUY", "SELL"}:
        decision = "HOLD"
        reasons.append("STRATEGY_FUSION_HOLD")
    if agreement < min_agreement:
        decision = "HOLD"
        reasons.append("AGREEMENT_BELOW_THRESHOLD")
    if final_score < min_confidence:
        decision = "HOLD"
        reasons.append("CONFIDENCE_BELOW_THRESHOLD")
    if risk_level not in set(policy.get("allowed_risk_levels", ["NORMAL"])):
        decision = "HOLD"
        reasons.append(f"RISK_LEVEL_NOT_ALLOWED:{risk_level}")

    return {
        "symbol": symbol,
        "status": "PASS",
        "decision": decision,
        "base_signal": base_signal,
        "raw_score": text(raw),
        "confidence": text(confidence),
        "agreement_percent": text(agreement),
        "risk_penalty": text(risk_penalty),
        "final_score": text(final_score),
        "strategy_counts": {
            "buy": buy,
            "sell": sell,
            "hold": hold,
            "total": len(rows),
        },
        "reasons": reasons or ["ALL_THRESHOLDS_PASSED"],
        "order_ticket_created": False,
        "order_submission_enabled": False,
    }
