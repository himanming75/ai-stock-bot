import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v120_final/actual/v120_final_release_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"stage":r.get("stage_range")=="V120_FINAL",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {"V120_FINAL_PRODUCTION_RELEASE_COMPLETE","V120_FINAL_PRODUCTION_RELEASE_REVIEW_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"integration_valid":isinstance(r.get("integration"),dict),
"safety_valid":isinstance(r.get("safety"),dict),
"integrity_valid":isinstance(r.get("integrity"),dict),
"acceptance_valid":isinstance(r.get("acceptance"),dict),
"approval_not_granted":r.get("approval_granted") is False,
"live_execution_disabled":r.get("live_execution_authorized") is False,
"broker_submission_disabled":r.get("broker_submission_authorized") is False,
"credentials_unused":r.get("actual_credentials_used") is False,
"network_unused":r.get("actual_external_network_used") is False,
"orders_zero":r.get("actual_orders_submitted")==0,
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"order_submission_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V120.00",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),"release_id":r.get("release_id"),
"development_complete":r.get("development_complete"),
"production_release_created":r.get("production_release_created"),
"paper_trading_ready":r.get("paper_trading_ready"),
"live_trading_ready":r.get("live_trading_ready"),
"integration":r.get("integration"),"safety":r.get("safety"),
"integrity":r.get("integrity"),"acceptance":r.get("acceptance"),
"bundle":r.get("bundle"),"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
