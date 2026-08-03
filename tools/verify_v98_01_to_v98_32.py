import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT / "release/v98_01_to_v98_32/actual/"
    "automated_backtest_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V98.01-V98.32",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"AUTOMATED_BACKTEST_SOURCE_REQUIRED",
"AUTOMATED_BACKTEST_FRAMEWORK_READY",
"AUTOMATED_BACKTEST_FRAMEWORK_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("automated_backtest_certificate_sha256",""))==64
    if result.get("state")!="AUTOMATED_BACKTEST_SOURCE_REQUIRED"
    else True
),
"results_valid":isinstance(result.get("results",[]),list),
"aggregation_valid":isinstance(result.get("aggregation",{}),dict),
"credentials_unused":result.get("actual_credentials_used") is False,
"network_unused":result.get("actual_external_network_used") is False,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
aggregation=result.get("aggregation",{})
top=aggregation.get("top_result") or {}
print(json.dumps({
"verification_stage":"V98.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"run_id":result.get("run_id"),
"job_count":result.get("job_count"),
"cache_hit_count":result.get("cache_hit_count"),
"aggregation":{
    "completed_count":aggregation.get("completed_count"),
    "skipped_count":aggregation.get("skipped_count"),
    "failed_count":aggregation.get("failed_count"),
    "top_strategy":top.get("strategy_id"),
    "top_symbol":top.get("symbol"),
    "top_return_pct":top.get("total_return_pct"),
    "top_drawdown_pct":top.get("maximum_drawdown_pct"),
},
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
