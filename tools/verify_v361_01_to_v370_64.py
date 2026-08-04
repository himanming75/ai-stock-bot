import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/"release/v361_01_to_v370_64/actual/latest_controlled_paper_execution_result.json").read_text(encoding="utf-8-sig"))
c={"stage":r.get("stage")=="V370.64","status":r.get("status")=="PASS","default_blocked":r.get("state")=="CONTROLLED_PAPER_EXECUTION_BLOCKED",
"network_unused":r.get("network_used") is False,"allow_network_false":r.get("allow_network") is False,"paper_endpoint_only":r.get("paper_endpoint_only") is True,
"paper_orders_zero":r.get("actual_paper_orders_submitted")==0,"live_orders_zero":r.get("actual_live_orders_submitted")==0,"live_disabled":r.get("live_submission_enabled") is False}
o={"verification_stage":"V370.64","verification_status":"PASS" if all(c.values()) else "FAIL","checks":c,"failed":[k for k,v in c.items() if not v]}
print(json.dumps(o,indent=2,sort_keys=True));raise SystemExit(0 if all(c.values()) else 1)
