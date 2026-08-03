
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner_result.json"
if not p.exists(): raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS","paper":r.get("paper_only") is True,
"supervised":r.get("operator_supervision_required") is True,
"loop":r.get("continuous_loop_enabled") is False,
"broker":r.get("broker_write_enabled") is False,
"orders":r.get("order_submission_enabled") is False,
"network":r.get("network_requests_executed")==0,
"orders_sent":r.get("actual_paper_orders_submitted")==0,
"recovery":r.get("recovery_snapshot_written") is True,
"dashboard":r.get("dashboard_state_written") is True,
"state":r.get("state") in {"SUPERVISED_RUNNER_READY","SUPERVISED_RUNNER_COMPLETE","SUPERVISED_RUNNER_LOCK_CLEARED"}}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
