import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V124.01-V126.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"CONTINUOUS_PAPER_SHADOW_OFFLINE_READY",
"CONTINUOUS_REAL_PAPER_SHADOW_READY",
"CONTINUOUS_REAL_PAPER_CYCLE_SUBMITTED",
"CONTINUOUS_PAPER_SHADOW_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"paper_only":r.get("paper_only") is True,
"live_disabled":r.get("live_trading_enabled",False) is False,
"live_submission_disabled":r.get("live_submission_enabled",False) is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V126.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),"mode":r.get("mode"),
"market_open":r.get("market_open"),"signals":r.get("signals"),
"paper_order_plans":r.get("paper_order_plans"),
"safety_gate":r.get("safety_gate"),
"live_shadow_records":r.get("live_shadow_records"),
"paper_submission_authorized":r.get("paper_submission_authorized"),
"actual_paper_orders_submitted":r.get("actual_paper_orders_submitted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"qualification":r.get("qualification"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
