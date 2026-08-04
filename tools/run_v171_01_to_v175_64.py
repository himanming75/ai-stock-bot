from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from controlled_micro_live.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r["stage"],"state":r["state"],"status":r["status"],
"candidate_present":bool(r["candidate"]),
"qualification_passed":r["readiness_gate"]["checks"]["qualification_passed"],
"approval_approved":r["readiness_gate"]["checks"]["approval_approved"],
"kill_switch_clear":r["readiness_gate"]["checks"]["kill_switch_clear"],
"token_valid":r["readiness_gate"]["checks"]["approval_token_valid"],
"dry_run_ready":r["dry_run_ready"],
"execution_authorized":r["execution_authorized"],
"actual_live_orders_submitted":0,
"next_phase":r["next_phase"],
},indent=2,sort_keys=True))
