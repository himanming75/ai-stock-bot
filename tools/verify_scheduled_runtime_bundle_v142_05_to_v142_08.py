import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/"release/v142_05_to_v142_08/actual/scheduled_runtime_bundle_result.json"
if not path.exists(): raise SystemExit("VERIFY=FAIL result file not found")
r=json.loads(path.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"safe":r.get("safe_mode_engaged") is False,
"network":r.get("network_requests_executed")==0,
"write":r.get("write_requests_executed")==0,
"paper":r.get("actual_paper_orders_submitted")==0,
"live":r.get("live_orders_submitted")==0,
"loop":r.get("continuous_loop_enabled") is False,
"state":r.get("state") in {"WAIT_AUTONOMOUS_PAPER_RUNTIME","AUTONOMOUS_RUNTIME_SCHEDULE_READY"}}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
