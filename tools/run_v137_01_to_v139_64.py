from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from autonomous_orchestrator.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"market_open":r.get("market",{}).get("market_open"),
"signal_count":len(r.get("signals",[])),
"candidate_count":len(r.get("selected_candidates",[])),
"plan_count":len(r.get("paper_order_plans",[])),
"risk_gate_passed":r.get("risk_gate_passed"),
"duplicate_cycle":r.get("duplicate_cycle"),
"actual_paper_orders_submitted":r.get("actual_paper_orders_submitted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"autonomous_cycle_complete":r.get("autonomous_cycle_complete"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v137_01_to_v139_64/actual/autonomous_orchestrator_result.json").resolve()))
