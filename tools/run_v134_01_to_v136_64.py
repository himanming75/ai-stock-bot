from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from dynamic_live_risk.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"candidate_present":bool(r.get("candidate")),
"final_quantity":r.get("dynamic_sizing",{}).get("final_quantity"),
"final_notional":r.get("dynamic_sizing",{}).get("final_notional"),
"risk_budget_passed":r.get("risk_budget",{}).get("budget_passed"),
"exposure_passed":r.get("exposure_control",{}).get("passed"),
"loss_limits_passed":r.get("loss_limits",{}).get("passed"),
"concentration_passed":r.get("concentration_control",{}).get("passed"),
"risk_gate_passed":r.get("risk_gate",{}).get("passed"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json").resolve()))
