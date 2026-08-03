from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from dashboard_analytics_v3.analytics import collect
from dashboard_analytics_v3.io import write_json
def main():
 data=collect(ROOT)
 out=ROOT/"release/v90_01_to_v90_32/actual/dashboard_analytics_v3_state.json"
 write_json(out,data)
 summary={
  "stage":data["stage"],"state":data["state"],"status":data["status"],
  "strategy_count":len(data["strategy_rows"]),"allocation_count":len(data["allocations"]),
  "alert_count":len(data["alerts"]),"remaining_validation_days":data["validation_progress"]["remaining_days"],
  "paper_only":data["paper_only"]
 }
 print(json.dumps(summary,indent=2,sort_keys=True)); print(f"STATE_FILE={out.resolve()}")
 return 0
if __name__=="__main__": raise SystemExit(main())
