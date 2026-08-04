from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from live_approval.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r["stage"],"state":r["state"],"status":r["status"],
"qualification_passed":r["qualification_passed"],
"candidate_present":bool(r["selected_candidate"]),
"approval_decision":r["approval_request"].get("decision"),
"live_read_only_enabled":r["live_read_only_enabled"],
"actual_live_network_attempted":r["actual_live_network_attempted"],
"execution_authorized":r["execution_authorized"],
"actual_live_orders_submitted":0,
"next_phase":r["next_phase"],
},indent=2,sort_keys=True))
