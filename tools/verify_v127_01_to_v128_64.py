import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v127_01_to_v128_64/actual/micro_live_readiness_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V127.01-V128.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"MICRO_LIVE_MANUAL_APPROVAL_READINESS_READY",
"MICRO_LIVE_READINESS_REVIEW_REQUIRED",
"MICRO_LIVE_READINESS_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"approval_token_not_issued":r.get("approval_token_issued",False) is False,
"live_network_disabled":r.get("live_network_enabled",False) is False,
"live_submission_disabled":r.get("live_submission_enabled",False) is False,
"live_network_not_attempted":r.get("real_live_network_attempted",False) is False,
"live_submission_not_attempted":r.get("real_live_submission_attempted",False) is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V128.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"live_order_candidates":r.get("live_order_candidates"),
"micro_live_limits":r.get("micro_live_limits"),
"manual_approval_request":r.get("manual_approval_request"),
"manual_approval_status":r.get("manual_approval_status"),
"approval_token_status":r.get("approval_token_status"),
"live_gateway":r.get("live_gateway"),
"paper_vs_live_shadow_comparison":r.get("paper_vs_live_shadow_comparison"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
