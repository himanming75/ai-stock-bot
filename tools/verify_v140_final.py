import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v140_final/actual/v140_final_release_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage")=="V140.00",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"V140_FINAL_AUTONOMOUS_RELEASE_COMPLETE",
"V140_FINAL_AUTONOMOUS_RELEASE_REVIEW_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"live_not_ready":r.get("live_trading_ready") is False,
"live_not_authorized":r.get("live_execution_authorized") is False,
"live_network_disabled":r.get("live_network_enabled") is False,
"live_submission_disabled":r.get("live_submission_enabled") is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V140.00",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"development_complete":r.get("development_complete"),
"paper_trading_ready":r.get("paper_trading_ready"),
"autonomous_paper_orchestrator_ready":r.get("autonomous_paper_orchestrator_ready"),
"web_controller_ready_for_development":r.get("web_controller_ready_for_development"),
"live_trading_ready":r.get("live_trading_ready"),
"source_summary":r.get("source_summary"),
"safety_gate":r.get("safety_gate"),
"release_certificate":r.get("release_certificate"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
