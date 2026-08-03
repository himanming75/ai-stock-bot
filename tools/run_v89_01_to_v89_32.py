from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from v89_engine.engine import run
from v89_engine.io import write_json
def main():
 p=argparse.ArgumentParser(); p.add_argument("--input",default=""); a=p.parse_args()
 result=run(ROOT,a.input)
 out=ROOT/"release/v89_01_to_v89_32/actual/v89_result.json"; write_json(out,result)
 summary={k:result.get(k) for k in ("stage","stage_range","state","status","bar_count","historical_input","paper_only","next_phase")}
 summary["candidate_files"]=result.get("discovery",{}).get("candidate_count",0)
 summary["remaining_validation_days"]=result.get("final_validation",{}).get("remaining_days")
 summary["champion"]=result.get("champion",{}).get("strategy") if result.get("champion") else None
 print(json.dumps(summary,indent=2,sort_keys=True)); print(f"RESULT_FILE={out.resolve()}")
 return 0
if __name__=="__main__": raise SystemExit(main())
