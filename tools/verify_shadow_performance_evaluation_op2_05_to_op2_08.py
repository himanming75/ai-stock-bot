import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op2_05_to_op2_08/actual/shadow_performance_evaluation_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"safe":r.get("safe_mode_engaged") is False,
"network":r.get("network_requests_executed")==0,
"write":r.get("write_requests_executed")==0,
"paper":r.get("actual_paper_orders_submitted")==0,
"live":r.get("live_orders_submitted")==0,
"shadow":r.get("shadow_only") is True,
"submission":r.get("order_submission_enabled") is False,
"state":r.get("state") in {"WAIT_SHADOW_DECISION","SHADOW_PERFORMANCE_EVALUATION_READY"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
