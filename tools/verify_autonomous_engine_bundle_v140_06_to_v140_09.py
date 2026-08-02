import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/v140_06_to_v140_09/actual/autonomous_engine_bundle_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result file not found")
r=json.loads(p.read_text());c={"status":r.get("status")=="PASS","safe":r.get("safe_mode_engaged") is False,"network":r.get("network_requests_executed")==0,"paper":r.get("actual_paper_orders_submitted")==0,"state":r.get("state") in {"WAIT_RUNTIME_CONTROL","AUTONOMOUS_ENGINE_READY"}}
f=[k for k,v in c.items() if not v]
print("VERIFY=PASS") if not f else (_ for _ in ()).throw(SystemExit("VERIFY=FAIL "+",".join(f)))
