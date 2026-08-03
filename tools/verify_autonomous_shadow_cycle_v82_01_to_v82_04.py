import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/v82_01_to_v82_04/actual/autonomous_shadow_cycle_result.json"
if not p.exists(): raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"shadow":r.get("shadow_only") is True,
"readonly":r.get("read_only") is True,
"single":r.get("single_cycle_only") is True,
"loop":r.get("continuous_loop_enabled") is False,
"broker":r.get("broker_write_enabled") is False,
"orders":r.get("order_submission_enabled") is False,
"network":r.get("network_requests_executed")==0,
"writes":r.get("write_requests_executed")==0,
"state":r.get("state") in {"AUTONOMOUS_SHADOW_CYCLE_READY","WAIT_SHADOW_FOUNDATION","AUTONOMOUS_SHADOW_CYCLE_COMPLETE"}}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
