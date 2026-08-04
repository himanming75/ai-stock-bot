import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v111_01_to_v113_64/actual/"
    "live_broker_readonly_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V111.01-V113.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"LIVE_BROKER_READ_ONLY_INFRASTRUCTURE_READY",
"LIVE_BROKER_READ_ONLY_REVIEW_REQUIRED",
"LIVE_BROKER_READ_ONLY_SOURCE_REQUIRED"},
"hash_valid":len(result.get("certificate_sha256",""))==64,
"read_only":result.get("read_only") is True,
"real_network_not_attempted":result.get(
    "real_network_connection_attempted",False
) is False,
"real_snapshot_not_fetched":result.get(
    "real_broker_snapshot_fetched",False
) is False,
"credentials_not_loaded":result.get("credentials_loaded",False) is False,
"credentials_unused":result.get("actual_credentials_used") is False,
"network_unused":result.get("actual_external_network_used") is False,
"network_requests_zero":result.get("network_requests_executed",0)==0,
"write_requests_zero":result.get("write_requests_executed",0)==0,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"live_execution_disabled":result.get("live_execution_authorized",False) is False,
"broker_submission_disabled":result.get(
    "broker_submission_authorized",False
) is False,
"broker_write_disabled":result.get("broker_write_enabled",False) is False,
"order_submission_disabled":result.get(
    "order_submission_enabled",False
) is False,
"live_disabled":result.get("live_trading_enabled",False) is False,
"network_disabled":result.get("external_network_enabled",False) is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V113.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"snapshot_id":result.get("snapshot_id"),
"selected_adapter":result.get("selected_adapter"),
"supported_adapters":result.get("supported_adapters"),
"capabilities":result.get("capabilities"),
"credential_inspection":result.get("credential_inspection"),
"adapter_health":result.get("adapter_health"),
"account_snapshot":result.get("account_snapshot"),
"position_snapshot":result.get("position_snapshot"),
"order_snapshot":result.get("order_snapshot"),
"reconciliation":result.get("reconciliation"),
"drift":result.get("drift"),
"safe_boundary":result.get("safe_boundary"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
