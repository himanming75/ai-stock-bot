from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ai_portfolio_manager.engine import evaluate

def main():
    result=evaluate(ROOT)
    allocation=result.get("allocation",{})
    risk=result.get("risk",{})
    champion=result.get("champion") or {}
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "portfolio_id":result.get("portfolio_id"),
        "candidate_count":result.get("candidate_count",0),
        "champion_strategy":champion.get("strategy_id"),
        "allocated_strategy_count":allocation.get("allocated_strategy_count",0),
        "cash_weight_pct":allocation.get("cash_weight_pct"),
        "largest_strategy_weight_pct":risk.get("largest_strategy_weight_pct"),
        "weighted_drawdown_pct":risk.get("weighted_drawdown_pct"),
        "risk_passed":risk.get("passed"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={(ROOT/'release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json').resolve()}")
    return 0

if __name__=="__main__": raise SystemExit(main())
