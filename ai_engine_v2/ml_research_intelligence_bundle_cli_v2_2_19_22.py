from pathlib import Path
from .ml_horizon_consensus_v2_2_19 import MLHorizonConsensusV2219
from .ml_uncertainty_v2_2_20 import MLUncertaintyV2220
from .ml_regime_segmentation_v2_2_21 import MLRegimeSegmentationV2221
from .ml_research_recommendation_v2_2_22 import MLResearchRecommendationV2222

def main():
    root=Path(r"C:\stock-bot")
    a=MLHorizonConsensusV2219(root).build()
    b=MLUncertaintyV2220(root).build()
    c=MLRegimeSegmentationV2221(root).build()
    d=MLResearchRecommendationV2222(root).build()
    print("=== V2.2.19-22 AI RESEARCH INTELLIGENCE BUNDLE ===")
    print("CONSENSUS_SYMBOLS:",a.get("symbol_count"))
    high=sum(1 for x in b.get("symbols",[]) if x.get("uncertainty_band")=="HIGH")
    print("HIGH_UNCERTAINTY_SYMBOLS:",high)
    print("REGIME_OUTCOMES:",c.get("total_outcomes"))
    print("REGIME_INTERPRETATION_READY:",c.get("interpretation_ready"))
    print("MODEL_HEALTH:",d.get("model_health"))
    print("RECOMMENDED_RESEARCH_ACTION:",d.get("recommended_research_action"))
    print("RESEARCH_COMPARISON_ALLOWED:",d.get("research_comparison_allowed"))
    print("AUTOMATIC_EXECUTION_CHANGE:",d.get("automatic_execution_change"))
    print("BROKER_NETWORK_USED:",d.get("broker_network_used"))
    print("ORDERS_SUBMITTED:",d.get("orders_submitted"))
    print("LIVE_TRADING:",d.get("live_trading"))
    return 0
if __name__=="__main__": raise SystemExit(main())
