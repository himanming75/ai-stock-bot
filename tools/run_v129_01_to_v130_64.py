from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from restricted_live_candidate.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"candidate_count":len(r.get("restricted_live_candidates",[])),
"eligible_count":r.get("restricted_gate",{}).get("eligible_count"),
"conflict_count":r.get("reconciliation",{}).get("conflict_count"),
"gateway_state":r.get("live_gateway",{}).get("gateway_state"),
"real_live_network_attempted":r.get("real_live_network_attempted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v129_01_to_v130_64/actual/restricted_live_candidate_result.json").resolve()))
