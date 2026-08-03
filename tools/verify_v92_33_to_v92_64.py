import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"release/v92_33_to_v92_64/actual/enterprise_risk_center_result.json"
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V92.33-V92.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"ENTERPRISE_RISK_SOURCE_REQUIRED",
"ENTERPRISE_RISK_CENTER_APPROVED",
"ENTERPRISE_RISK_CENTER_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("risk_certificate_sha256",""))==64
    if result.get("state")!="ENTERPRISE_RISK_SOURCE_REQUIRED"
    else True
),
"metrics_valid":isinstance(result.get("risk_metrics",{}),dict),
"stress_valid":isinstance(result.get("stress_scenarios",[]),list),
"guards_valid":isinstance(result.get("guards",{}),dict),
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V92.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"risk_approved":result.get("risk_approved"),
"risk_metrics":result.get("risk_metrics"),
"failed_risk_checks":result.get("failed_risk_checks",[]),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
