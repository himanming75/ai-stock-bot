from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from restricted_live_automation.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
 "stage":r["stage"],"state":r["state"],"status":r["status"],
 "candidate_present":bool(r["candidate"]),
 "qualification_state":r["qualification_state"],
 "micro_live_state":r["micro_live_state"],
 "gate_passed":r["restricted_gate"]["passed"],
 "execution_authorized":r["execution_authorized"],
 "automatic_submission_enabled":r["automatic_submission_enabled"],
 "actual_live_orders_submitted":0,
 "next_phase":r["next_phase"]
},indent=2,sort_keys=True))
