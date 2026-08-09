from .common import safe_status, SAFETY_CONTRACTS

STRATEGY_PROPOSALS={
 "EXIT_RULE_CANDIDATE","RISK_LIMIT_CANDIDATE","EXECUTION_FRICTION_CANDIDATE",
 "ENTRY_FILTER_CANDIDATE","REGIME_FILTER_CANDIDATE","READINESS_BLOCKER_CANDIDATE",
 "STRATEGY_REVIEW_CANDIDATE",
}

def build_shadow_challenger(improvement):
    candidates=improvement.get("candidates") or []
    eligible=[c for c in candidates if c.get("proposal_type") in STRATEGY_PROPOSALS]
    if not eligible:
        return safe_status(
            "V3.19_SHADOW_CHALLENGER_ENGINE",
            "WAITING_FOR_ELIGIBLE_CHALLENGER",
            challenger_count=0,
            challengers=[],
            champion={"strategy_id":"CURRENT_CHAMPION","immutable":True},
            contracts=dict(SAFETY_CONTRACTS),
        )
    challengers=[]
    for i,c in enumerate(eligible,1):
        challengers.append({
            "challenger_id":f"CHALLENGER-{i:03d}",
            "source_candidate_id":c.get("candidate_id"),
            "proposal_type":c.get("proposal_type"),
            "change_target":c.get("change_target"),
            "mode":"SHADOW_ONLY",
            "execution_enabled":False,
            "observation_count":0,
        })
    return safe_status(
        "V3.19_SHADOW_CHALLENGER_ENGINE","PASS_SHADOW_INFRASTRUCTURE_READY",
        challenger_count=len(challengers),challengers=challengers,
        champion={"strategy_id":"CURRENT_CHAMPION","immutable":True},
        contracts=dict(SAFETY_CONTRACTS),
    )
