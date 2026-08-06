from __future__ import annotations


def build_decision_explanation(
    *,
    symbol: str,
    action: str,
    confidence: str,
    strategy_id: str,
    regime: str,
    factors: dict[str, str],
    safety_state: str,
) -> dict:
    ordered_factors = [
        {
            "name": key,
            "value": factors[key],
        }
        for key in sorted(factors)
    ]

    if safety_state.upper() != "NORMAL":
        final_action = "WAIT"
        reason = f"SAFETY_OVERRIDE:{safety_state.upper()}"
    else:
        final_action = action.upper()
        reason = (
            f"{strategy_id.upper()}_DECISION_IN_"
            f"{regime.upper()}"
        )

    return {
        "symbol": symbol,
        "requested_action": action.upper(),
        "final_action": final_action,
        "confidence": str(confidence),
        "strategy_id": strategy_id,
        "regime": regime,
        "safety_state": safety_state,
        "reason": reason,
        "factors": ordered_factors,
        "human_summary": (
            f"{final_action} {symbol}: {reason}; "
            f"confidence={confidence}"
        ),
    }
