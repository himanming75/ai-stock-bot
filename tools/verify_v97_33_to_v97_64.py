import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT
    / "release/v97_33_to_v97_64/actual/"
    "paper_broker_snapshot_reconciliation_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V97.33-V97.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"PAPER_BROKER_READ_MODEL_SOURCE_REQUIRED",
"PAPER_BROKER_SNAPSHOT_RECONCILIATION_PASS",
"PAPER_BROKER_SNAPSHOT_RECONCILIATION_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("paper_broker_snapshot_certificate_sha256",""))==64
    if result.get("state")!="PAPER_BROKER_READ_MODEL_SOURCE_REQUIRED"
    else True
),
"account_reconciliation_valid":isinstance(
    result.get("account_reconciliation",{}),dict
),
"position_reconciliation_valid":isinstance(
    result.get("position_reconciliation",{}),dict
),
"freshness_valid":isinstance(
    result.get("snapshot_freshness",{}),dict
),
"integrity_valid":isinstance(result.get("integrity",{}),dict),
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
"verification_stage":"V97.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"source_adapter_name":result.get("source_adapter_name"),
"account_reconciliation":result.get("account_reconciliation"),
"position_reconciliation":result.get("position_reconciliation"),
"snapshot_freshness":result.get("snapshot_freshness"),
"integrity":result.get("integrity"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
