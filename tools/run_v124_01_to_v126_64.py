from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from continuous_paper_shadow.engine import evaluate
p=argparse.ArgumentParser()
p.add_argument("--real-network",action="store_true")
p.add_argument("--submit-paper",action="store_true")
a=p.parse_args()
r=evaluate(ROOT,a.real_network,a.submit_paper)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"mode":r.get("mode"),"market_open":r.get("market_open"),
"signal_count":len(r.get("signals",[])),"plan_count":len(r.get("paper_order_plans",[])),
"paper_submission_authorized":r.get("paper_submission_authorized"),
"actual_paper_orders_submitted":r.get("actual_paper_orders_submitted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"qualification_passed":r.get("qualification",{}).get("passed"),
"completed_sessions":r.get("qualification",{}).get("completed_sessions"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json").resolve()))
