from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_explainability_pro.engine import explain
from ai_explainability_pro.io import write_json

def main():
    result=explain(ROOT)
    out=ROOT/"release/v92_01_to_v92_32/actual/ai_explainability_pro_result.json"
    write_json(out,result)

    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "strategy_id":result.get("strategy_id"),
        "parameters":result.get("parameters"),
        "decision":result.get("decision"),
        "confidence_score":result.get("confidence",{}).get("score"),
        "confidence_level":result.get("confidence",{}).get("level"),
        "selection_reason_count":len(result.get("selection_reasons",[])),
        "risk_factor_count":len(result.get("risk_factors",[])),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
