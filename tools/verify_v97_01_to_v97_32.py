import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT
    / "release/v97_01_to_v97_32/actual/"
    "paper_broker_adapter_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V97.01-V97.32",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"PAPER_BROKER_ADAPTER_SOURCE_REQUIRED",
"PAPER_BROKER_ADAPTER_READY",
"PAPER_BROKER_ADAPTER_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("paper_broker_adapter_certificate_sha256",""))==64
    if result.get("state")!="PAPER_BROKER_ADAPTER_SOURCE_REQUIRED"
    else True
),
"capabilities_valid":isinstance(
    result.get("adapter_capabilities",{}),dict
),
"health_valid":isinstance(result.get("adapter_health",{}),dict),
"boundary_valid":isinstance(
    result.get("safe_api_boundary",{}),dict
),
"read_only_adapter":result.get("read_only_adapter") is True,
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
print(json.dumps({
"verification_stage":"V97.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"adapter_name":result.get("adapter_name"),
"adapter_capabilities":result.get("adapter_capabilities"),
"adapter_health":result.get("adapter_health"),
"safe_api_boundary":result.get("safe_api_boundary"),
"account_snapshot":result.get("account_snapshot"),
"position_count":len(result.get("positions_snapshot",[])),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
