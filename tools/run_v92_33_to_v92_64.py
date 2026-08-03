from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from enterprise_risk_center.engine import evaluate
from enterprise_risk_center.io import write_json

def main():
    result=evaluate(ROOT)
    out=ROOT/"release/v92_33_to_v92_64/actual/enterprise_risk_center_result.json"
    write_json(out,result)

    metrics=result.get("risk_metrics",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "strategy_id":result.get("strategy_id"),
        "risk_approved":result.get("risk_approved"),
        "historical_var_pct":metrics.get("historical_var_pct"),
        "expected_shortfall_pct":metrics.get("expected_shortfall_pct"),
        "annualized_volatility_pct":metrics.get("annualized_volatility_pct"),
        "maximum_drawdown_pct":metrics.get("maximum_drawdown_pct"),
        "failed_risk_checks":result.get("failed_risk_checks",[]),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
