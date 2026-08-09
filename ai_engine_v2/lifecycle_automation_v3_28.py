from .common import safe_status

def build_lifecycle(shadow,evaluation,gate,promotion):
    if not shadow.get("challengers"):
        state="WAITING_FOR_CHALLENGER"
    elif evaluation.get("comparison_count",0)<20:
        state="SHADOW_OBSERVATION"
    elif gate.get("promotion_eligible"):
        state="WAITING_FOR_MANUAL_PROMOTION_REVIEW"
    else:
        state="CHALLENGER_REJECTED_OR_CONTINUE_OBSERVATION"
    return safe_status("V3.28_STRATEGY_LIFECYCLE_AUTOMATION","PASS",
        lifecycle_state=state,automatic_transition_performed=False,
        automatic_strategy_change=False)
