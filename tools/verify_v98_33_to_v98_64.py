import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"release/v98_33_to_v98_64/actual/backtest_batch_result.json"
if not path.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(path.read_text())
checks={
"stage":r.get("stage_range")=="V98.33-V98.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"BACKTEST_BATCH_SOURCE_REQUIRED",
"BACKTEST_BATCH_REGRESSION_READY",
"BACKTEST_BATCH_REGRESSION_REVIEW_REQUIRED"},
"hash_valid":len(r.get("batch_regression_certificate_sha256",""))==64 if r.get("state")!="BACKTEST_BATCH_SOURCE_REQUIRED" else True,
"results_valid":isinstance(r.get("results",[]),list),
"champion_valid":isinstance(r.get("champion",{}),dict) if r.get("champion") is not None else True,
"credentials_unused":r.get("actual_credentials_used") is False,
"network_unused":r.get("actual_external_network_used") is False,
"orders_zero":r.get("actual_orders_submitted")==0,
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V98.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"batch_id":r.get("batch_id"),
"job_count":r.get("job_count"),
"completed_count":r.get("completed_count"),
"failed_count":r.get("failed_count"),
"regression_pass_count":r.get("regression_pass_count"),
"regression_fail_count":r.get("regression_fail_count"),
"champion":r.get("champion"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
