import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"stage":r.get("stage_range")=="V121.01-V123.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"ALPACA_PAPER_OFFLINE_VALIDATION_READY",
"REAL_ALPACA_PAPER_READ_ONLY_READY",
"REAL_ALPACA_PAPER_ORDER_SUBMITTED",
"ALPACA_PAPER_OPERATIONS_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"paper_only":r.get("paper_only") is True,
"live_disabled":r.get("live_trading_enabled") is False,
"live_submission_disabled":r.get("live_submission_enabled") is False,
"live_base_url_unused":r.get("live_base_url_used") is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V123.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),"mode":r.get("mode"),
"credential_status":r.get("credential_status"),
"account_snapshot":r.get("account_snapshot"),
"position_snapshot":r.get("position_snapshot"),
"order_snapshot":r.get("order_snapshot"),
"clock_snapshot":r.get("clock_snapshot"),
"order_validation":r.get("order_validation"),
"submission_gate":r.get("submission_gate"),
"qualification":r.get("qualification"),
"actual_paper_orders_submitted":r.get("actual_paper_orders_submitted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
