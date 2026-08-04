import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v117_01_to_v119_64/actual/"
    "live_safety_system_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V117.01-V119.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"LIVE_SAFETY_SYSTEM_READY",
"LIVE_SAFETY_SYSTEM_EMERGENCY_BLOCKED",
"LIVE_SAFETY_SYSTEM_SOURCE_REQUIRED"},
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
"emergency_cancel_not_executed":result.get(
    "emergency_cancel_requests_executed",0
)==0,
"emergency_flatten_not_executed":result.get(
    "emergency_flatten_requests_executed",0
)==0,
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
"verification_stage":"V119.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"safety_assessment_id":result.get("safety_assessment_id"),
"safety_passed":result.get("safety_passed"),
"kill_switch":result.get("kill_switch"),
"loss_limits":result.get("loss_limits"),
"exposure":result.get("exposure"),
"anomaly_detection":result.get("anomaly_detection"),
"emergency_action":result.get("emergency_action"),
"resume_gate":result.get("resume_gate"),
"safety_certificate":result.get("safety_certificate"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
