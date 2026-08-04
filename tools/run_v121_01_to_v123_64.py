from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_paper_operations.engine import evaluate
p=argparse.ArgumentParser()
p.add_argument("--real-network",action="store_true")
p.add_argument("--submit-paper-order",action="store_true")
a=p.parse_args()
if a.submit_paper_order and not a.real_network:
    raise SystemExit("--submit-paper-order requires --real-network")
r=evaluate(ROOT,a.real_network,a.submit_paper_order)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"mode":r.get("mode"),"account_equity":r.get("account_snapshot",{}).get("equity"),
"position_count":len(r.get("position_snapshot",[])),
"order_count":len(r.get("order_snapshot",[])),
"market_open":r.get("clock_snapshot",{}).get("is_open"),
"submission_authorized":r.get("submission_gate",{}).get("authorized"),
"actual_paper_orders_submitted":r.get("actual_paper_orders_submitted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"qualification_passed":r.get("qualification",{}).get("passed"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json").resolve()))
