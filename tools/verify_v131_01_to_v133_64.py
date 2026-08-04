import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v131_01_to_v133_64/actual/controlled_micro_live_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V131.01-V133.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW_COMPLETE",
"CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW_REQUIRED",
"CONTROLLED_MICRO_LIVE_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"two_step_approval_required":r.get("two_step_manual_approval_required",True) is True,
"approvals_not_granted":r.get("first_approval_granted",False) is False and r.get("second_approval_granted",False) is False,
"live_token_not_issued":r.get("live_approval_token_issued",False) is False,
"live_network_disabled":r.get("live_network_enabled",False) is False,
"live_submission_disabled":r.get("live_submission_enabled",False) is False,
"network_not_attempted":r.get("real_live_network_attempted",False) is False,
"submission_not_attempted":r.get("real_live_submission_attempted",False) is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V133.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"candidate":r.get("candidate"),
"manual_approval_request":r.get("manual_approval_request"),
"approval_token_status":r.get("approval_token_status"),
"kill_switch":r.get("kill_switch"),
"live_order_payload_review":r.get("live_order_payload_review"),
"execution_simulation":r.get("execution_simulation"),
"execution_review":r.get("execution_review"),
"review_certificate":r.get("review_certificate"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
