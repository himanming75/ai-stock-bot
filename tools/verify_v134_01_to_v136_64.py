import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V134.01-V136.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"DYNAMIC_LIVE_RISK_ENGINE_READY",
"DYNAMIC_LIVE_RISK_REVIEW_REQUIRED",
"DYNAMIC_LIVE_RISK_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"execution_not_authorized":r.get("execution_authorized",False) is False,
"live_network_disabled":r.get("live_network_enabled",False) is False,
"live_submission_disabled":r.get("live_submission_enabled",False) is False,
"network_not_attempted":r.get("real_live_network_attempted",False) is False,
"submission_not_attempted":r.get("real_live_submission_attempted",False) is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V136.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"candidate":r.get("candidate"),
"dynamic_sizing":r.get("dynamic_sizing"),
"risk_budget":r.get("risk_budget"),
"exposure_control":r.get("exposure_control"),
"loss_limits":r.get("loss_limits"),
"concentration_control":r.get("concentration_control"),
"risk_gate":r.get("risk_gate"),
"risk_certificate":r.get("risk_certificate"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
