from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.integrated_engine_v3_30 import build_integrated_ai_engine_v2

candidate={
    "candidate_id":"SYNTHETIC-CANDIDATE",
    "proposal_type":"EXIT_RULE_CANDIDATE",
    "change_target":"Exit rules",
}
obs=[
    {
        "challenger_id":"CHALLENGER-001",
        "champion_pnl":1.0,
        "challenger_pnl":1.5,
        "champion_drawdown":1.0,
        "challenger_drawdown":0.7,
    }
    for _ in range(25)
]
analytics={
    "historical":{"numeric_trade_count":30},
    "strategy_improvement_candidates":{"candidates":[candidate]},
    "market_regime_analysis":{
        "evidence_trade_count":30,
        "coverage":{"direction_coverage":1.0,"volatility_coverage":1.0},
    },
}
result=build_integrated_ai_engine_v2(analytics,{},obs)
summary={
    "development_status":result["development_status"],
    "promotion_gate_status":result["stages"]["V3.21"]["status"],
    "promotion_eligible":result["stages"]["V3.21"]["promotion_eligible"],
    "live_trading_status":result["live_trading_status"],
    "automatic_promotion_status":result["automatic_promotion_status"],
    "synthetic_is_not_profitability_validation":result["contracts"]["synthetic_fixture_validates_software_not_profitability"],
}
print(json.dumps(summary,indent=2))
if summary["development_status"]!="COMPLETE": raise SystemExit(2)
if not summary["promotion_eligible"]: raise SystemExit(3)
if summary["live_trading_status"]!="LOCKED": raise SystemExit(4)
if summary["automatic_promotion_status"]!="LOCKED": raise SystemExit(5)
print("SYNTHETIC INTEGRATION TEST: PASS")
