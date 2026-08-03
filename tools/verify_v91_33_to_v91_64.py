import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"release/v91_33_to_v91_64/actual/parameter_optimization_result.json"
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V91.33-V91.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"PARAMETER_OPTIMIZATION_HISTORICAL_DATA_REQUIRED",
"PARAMETER_OPTIMIZATION_STABLE_CANDIDATE_READY",
"PARAMETER_OPTIMIZATION_REVIEW_REQUIRED",
},
"results_valid":isinstance(result.get("top_results",[]),list),
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
stable=result.get("best_stable_candidate")
candidate=result.get("best_candidate")
print(json.dumps({
"verification_stage":"V91.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"evaluated_combination_count":result.get("evaluated_combination_count",0),
"stable_combination_count":result.get("stable_combination_count",0),
"best_stable_strategy":stable.get("strategy_id") if stable else None,
"best_candidate_strategy":candidate.get("strategy_id") if candidate else None,
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
