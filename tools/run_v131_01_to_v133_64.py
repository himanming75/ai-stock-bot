from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from controlled_micro_live.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"candidate_present":bool(r.get("candidate")),
"approval_state":(
    "WAITING_FOR_TWO_STEP_APPROVAL"
    if r.get("manual_approval_request") else "NO_CANDIDATE"
),
"live_approval_token_issued":r.get("live_approval_token_issued"),
"kill_switch_state":r.get("kill_switch",{}).get("state"),
"simulation_status":r.get("execution_simulation",{}).get("simulated_status"),
"review_passed":r.get("execution_review",{}).get("passed"),
"real_live_network_attempted":r.get("real_live_network_attempted"),
"real_live_submission_attempted":r.get("real_live_submission_attempted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v131_01_to_v133_64/actual/controlled_micro_live_result.json").resolve()))
