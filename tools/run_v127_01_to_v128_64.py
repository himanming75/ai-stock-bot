from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from micro_live_readiness.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"candidate_count":len(r.get("live_order_candidates",[])),
"eligible_count":r.get("micro_live_limits",{}).get("eligible_count"),
"approval_state":r.get("manual_approval_status",{}).get("state"),
"approval_token_issued":r.get("approval_token_issued"),
"gateway_state":r.get("live_gateway",{}).get("gateway_state"),
"real_live_network_attempted":r.get("real_live_network_attempted"),
"real_live_submission_attempted":r.get("real_live_submission_attempted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v127_01_to_v128_64/actual/micro_live_readiness_result.json").resolve()))
