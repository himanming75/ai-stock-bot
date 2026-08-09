from __future__ import annotations

from decimal import Decimal


GENERIC_ETRADE_BRIDGE_MIN_CONFIDENCE = Decimal("0.60")
CANONICAL_PAPER_MIN_CONFIDENCE = Decimal("0.75")
CANONICAL_PAPER_MIN_REWARD_RISK = Decimal("1.0")


def semantic_gate_contract_v2_1_19_1():
    return {
        "generic_etrade_bridge":{
            "minimum_confidence":str(GENERIC_ETRADE_BRIDGE_MIN_CONFIDENCE),
            "minimum_reward_risk":None,
            "purpose":"GENERIC_BROKER_BRIDGE_SIGNAL_GATE",
            "canonical_paper_gate":False,
        },
        "canonical_paper":{
            "minimum_confidence":str(CANONICAL_PAPER_MIN_CONFIDENCE),
            "minimum_reward_risk":str(CANONICAL_PAPER_MIN_REWARD_RISK),
            "purpose":"CANONICAL_PAPER_CANDIDATE_QUALIFICATION",
            "canonical_paper_gate":True,
        },
        "semantic_equivalence":False,
        "zero_point_60_must_not_be_labeled_canonical_paper":True,
    }


def qualify_canonical_paper_metrics(confidence, reward_risk):
    confidence=Decimal(str(confidence))
    if reward_risk is None or str(reward_risk).strip()=="":
        return {
            "ready":False,
            "reasons":["CANONICAL_REWARD_RISK_MISSING"],
        }

    reward_risk=Decimal(str(reward_risk))
    reasons=[]

    if confidence < CANONICAL_PAPER_MIN_CONFIDENCE:
        reasons.append("CONFIDENCE_BELOW_CANONICAL_PAPER")

    if reward_risk < CANONICAL_PAPER_MIN_REWARD_RISK:
        reasons.append("REWARD_RISK_BELOW_CANONICAL_PAPER")

    return {
        "ready":len(reasons)==0,
        "reasons":reasons,
    }
