import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op5_17_to_op5_20/actual/promotion_approval_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"paper":r.get("paper_only") is True,
"read_only":r.get("read_only") is True,
"broker":r.get("broker_write_enabled") is False,
"submission":r.get("order_submission_enabled") is False,
"network":r.get("network_requests_executed")==0,
"writes":r.get("write_requests_executed")==0,
"orders":r.get("actual_paper_orders_submitted")==0,
"manifest":r.get("approval_manifest_written") is True,
"gate":r.get("certification_gate_written") is True,
"dashboard":r.get("dashboard_state_written") is True,
"state":r.get("state") in {
"WAIT_PROMOTION_READY",
"WAIT_EXPLICIT_APPROVAL",
"PAPER_PILOT_CERTIFICATION_READY",
"PROMOTION_APPROVAL_BLOCKED"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
