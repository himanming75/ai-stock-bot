import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v114_01_to_v116_64/actual/"
    "broker_safe_execution_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V114.01-V116.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"BROKER_INTEGRATION_SAFE_EXECUTION_BOUNDARY_READY",
"BROKER_INTEGRATION_SAFE_EXECUTION_REVIEW_REQUIRED",
"BROKER_SAFE_EXECUTION_SOURCE_REQUIRED"},
"hash_valid":len(result.get("certificate_sha256",""))==64,
"manual_approval_required":result.get(
    "manual_approval_required",True
) is True,
"approval_not_granted":result.get("approval_granted",False) is False,
"approval_token_not_issued":result.get(
    "approval_token_issued",False
) is False,
"live_execution_disabled":result.get(
    "live_execution_authorized",False
) is False,
"broker_submission_disabled":result.get(
    "broker_submission_authorized",False
) is False,
"real_submission_not_attempted":result.get(
    "real_broker_submission_attempted",False
) is False,
"real_sync_not_performed":result.get(
    "real_broker_sync_performed",False
) is False,
"credentials_unused":result.get("actual_credentials_used",False) is False,
"network_unused":result.get(
    "actual_external_network_used",False
) is False,
"network_requests_zero":result.get("network_requests_executed",0)==0,
"write_requests_zero":result.get("write_requests_executed",0)==0,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled",False) is False,
"order_submission_disabled":result.get(
    "order_submission_enabled",False
) is False,
"live_disabled":result.get("live_trading_enabled",False) is False,
"network_disabled":result.get("external_network_enabled",False) is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V116.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"execution_package_id":result.get("execution_package_id"),
"selected_adapter":result.get("selected_adapter"),
"order_intents":result.get("order_intents"),
"validation":result.get("validation"),
"manual_approval_package":result.get("manual_approval_package"),
"translated_payloads":result.get("translated_payloads"),
"execution_queue":result.get("execution_queue"),
"safe_gateway":result.get("safe_gateway"),
"fill_sync":result.get("fill_sync"),
"position_sync":result.get("position_sync"),
"cancel_replace":result.get("cancel_replace"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
