import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v129_01_to_v130_64/actual/restricted_live_candidate_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V129.01-V130.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"RESTRICTED_AUTOMATIC_LIVE_CANDIDATE_READY",
"RESTRICTED_AUTOMATIC_LIVE_CANDIDATE_REVIEW_REQUIRED",
"RESTRICTED_LIVE_CANDIDATE_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"live_network_not_attempted":r.get("real_live_network_attempted",False) is False,
"live_write_disabled":r.get("live_network_write_enabled",False) is False,
"live_submission_disabled":r.get("live_submission_enabled",False) is False,
"manual_approval_incomplete":r.get("manual_approval_complete",False) is False,
"token_invalid":r.get("approval_token_valid",False) is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V130.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"live_account_snapshot":r.get("live_account_snapshot"),
"restricted_live_candidates":r.get("restricted_live_candidates"),
"reconciliation":r.get("reconciliation"),
"restricted_gate":r.get("restricted_gate"),
"live_gateway":r.get("live_gateway"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
