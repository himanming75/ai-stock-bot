from pathlib import Path
from .ml_model_health_v2_2_16 import MLModelHealthGateV2216
from .ml_retraining_trigger_v2_2_17 import MLRetrainingTriggerPlannerV2217
from .ml_candidate_evaluation_snapshot_v2_2_18 import MLCandidateEvaluationSnapshotV2218

def main():
    root=Path(r"C:\stock-bot")
    a=MLModelHealthGateV2216(root).evaluate()
    b=MLRetrainingTriggerPlannerV2217(root).evaluate()
    c=MLCandidateEvaluationSnapshotV2218(root).build()
    print("=== V2.2.16-18 AI MODEL HEALTH BUNDLE ===")
    print("V2.2.16 MODEL_HEALTH:",a.get("model_health"))
    print("V2.2.16 RESEARCH_ACTION:",a.get("research_action"))
    print("V2.2.16 BLOCK_REASONS:",a.get("block_reasons"))
    print("V2.2.17 RETRAINING_RECOMMENDED:",b.get("retraining_recommended"))
    print("V2.2.18 CANDIDATE_RESEARCH_READY:",c.get("candidate_research_ready"))
    print("EXECUTION_SELECTOR_MODIFIED:",c.get("execution_selector_modified"))
    print("BROKER_NETWORK_USED:",c.get("broker_network_used"))
    print("ORDERS_SUBMITTED:",c.get("orders_submitted"))
    print("LIVE_TRADING:",c.get("live_trading"))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
