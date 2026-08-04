import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v105_01_to_v105_32/actual/"
    "final_system_integration_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V105.01-V105.32",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"FINAL_SYSTEM_INTEGRATION_READY",
"FINAL_SYSTEM_INTEGRATION_REVIEW_REQUIRED"},
"hash_valid":len(
    result.get("final_integration_certificate_sha256","")
)==64,
"registry_valid":isinstance(result.get("module_registry",[]),list),
"pipeline_valid":isinstance(result.get("pipeline",{}),dict),
"safety_valid":isinstance(result.get("safety",{}),dict),
"readiness_valid":isinstance(result.get("readiness",{}),dict),
"dashboard_valid":isinstance(result.get("dashboard_snapshot",{}),dict),
"checkpoint_valid":isinstance(result.get("checkpoint",{}),dict),
"production_release_not_created":result.get("production_release_created") is False,
"approval_not_granted":result.get("approval_granted") is False,
"execution_not_authorized":result.get("execution_authorized") is False,
"manual_approval_required":result.get("manual_approval_required") is True,
"credentials_unused":result.get("actual_credentials_used") is False,
"network_unused":result.get("actual_external_network_used") is False,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
"background_service_not_running":result.get("background_service_running") is False,
"windows_task_disabled":result.get("windows_task_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V105.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"integration_id":result.get("integration_id"),
"readiness":result.get("readiness"),
"pipeline":result.get("pipeline"),
"safety":result.get("safety"),
"checkpoint":result.get("checkpoint"),
"final_release_eligible":result.get("final_release_eligible"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
