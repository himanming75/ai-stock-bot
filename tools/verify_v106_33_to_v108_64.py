import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v106_33_to_v108_64/actual/"
    "fast_track_paper_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V106.33-V108.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"FAST_TRACK_PAPER_EXECUTION_AND_ANALYTICS_COMPLETE",
"FAST_TRACK_PAPER_CYCLE_DUPLICATE_BLOCKED",
"FAST_TRACK_PAPER_SOURCE_REQUIRED"},
"hash_valid":len(result.get("certificate_sha256",""))==64,
"broker_orders_zero":result.get("actual_broker_orders_submitted",0)==0,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"live_execution_disabled":result.get("live_execution_authorized",False) is False,
"broker_submission_disabled":result.get("broker_submission_authorized",False) is False,
"broker_write_disabled":result.get("broker_write_enabled",False) is False,
"order_submission_disabled":result.get("order_submission_enabled",False) is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled",False) is False,
"credentials_unused":result.get("actual_credentials_used",False) is False,
"network_unused":result.get("actual_external_network_used",False) is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V108.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"cycle_id":result.get("cycle_id"),
"paper_order_count":result.get("paper_order_count"),
"filled_count":result.get("filled_count"),
"partial_fill_count":result.get("partial_fill_count"),
"not_filled_count":result.get("not_filled_count"),
"exit_count":result.get("exit_count"),
"daily_close":result.get("daily_close"),
"analytics":result.get("analytics"),
"checkpoint":result.get("checkpoint"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
