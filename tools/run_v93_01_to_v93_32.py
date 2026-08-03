from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from market_regime_engine.engine import evaluate
from market_regime_engine.io import write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="")
    args=parser.parse_args()

    result=evaluate(ROOT,args.input)
    out=ROOT/"release/v93_01_to_v93_32/actual/market_regime_result.json"
    write_json(out,result)

    regime=result.get("regime",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "bar_count":result.get("bar_count"),
        "primary_regime":regime.get("primary_regime"),
        "volatility_regime":regime.get("volatility_regime"),
        "risk_mode":regime.get("risk_mode"),
        "confidence_score":regime.get("confidence_score"),
        "recommended_strategies":result.get("recommended_strategies",[]),
        "effective_position_multiplier":result.get("effective_position_multiplier"),
        "failed_checks":result.get("failed_checks",[]),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
