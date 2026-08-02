import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/"release/v140_02_to_v140_05/actual/runtime_control_bundle_result.json"
if not p.exists(): raise SystemExit("VERIFY=FAIL result file not found")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status_pass":r.get("status")=="PASS",
"safe_false":r.get("safe_mode_engaged") is False,
"network_zero":r.get("network_requests_executed")==0,
"write_zero":r.get("write_requests_executed")==0,
"paper_zero":r.get("actual_paper_orders_submitted")==0,
"live_zero":r.get("live_orders_submitted")==0,
"state_valid":r.get("state") in {"WAIT_RUNTIME_READY","RUNTIME_CONTROL_READY"}}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
