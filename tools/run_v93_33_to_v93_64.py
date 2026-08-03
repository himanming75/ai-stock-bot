from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from multi_timeframe_regime.engine import evaluate
from multi_timeframe_regime.io import write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="")
    args=parser.parse_args()
    result=evaluate(ROOT,args.input)
    out=ROOT/"release/v93_33_to_v93_64/actual/multi_timeframe_regime_result.json"
    write_json(out,result)
    consensus=result.get("consensus",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "source_bar_count":result.get("source_bar_count"),
        "frame_count":result.get("frame_count"),
        "primary_regime":consensus.get("primary_regime"),
        "volatility_regime":consensus.get("volatility_regime"),
        "risk_mode":consensus.get("risk_mode"),
        "alignment_pct":consensus.get("alignment_pct"),
        "conflict_detected":consensus.get("conflict_detected"),
        "recommended_strategies":result.get("recommended_strategies",[]),
        "effective_position_multiplier":result.get("effective_position_multiplier"),
        "failed_checks":result.get("failed_checks",[]),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__": raise SystemExit(main())
