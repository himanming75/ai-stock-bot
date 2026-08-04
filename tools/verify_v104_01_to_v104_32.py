import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v104_01_to_v104_32/actual/"
    "continuous_autonomous_engine_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V104.01-V104.32",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"CONTINUOUS_AUTONOMOUS_ENGINE_WAITING_FOR_MANUAL_APPROVAL",
"CONTINUOUS_AUTONOMOUS_ENGINE_HOLD",
"CONTINUOUS_AUTONOMOUS_ENGINE_READY",
"CONTINUOUS_AUTONOMOUS_ENGINE_IDLE",
"CONTINUOUS_AUTONOMOUS_ENGINE_SOURCE_REQUIRED",
"CONTINUOUS_AUTONOMOUS_ENGINE_RECOVERY_REQUIRED",
"CONTINUOUS_AUTONOMOUS_ENGINE_GATE_BLOCKED"},
"hash_valid":len(
    result.get("continuous_engine_certificate_sha256","")
)==64,
"source_validation_valid":isinstance(
    result.get("source_validation",{}),dict
),
"selected_session_valid":isinstance(
    result.get("selected_session",{}),dict
),
"gates_valid":isinstance(result.get("iteration_gates",{}),dict),
"phases_valid":isinstance(result.get("phases",[]),list),
"checkpoint_valid":isinstance(result.get("checkpoint",{}),dict),
"recovery_valid":isinstance(result.get("recovery",{}),dict),
"service_not_started":result.get("continuous_service_started") is False,
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
"continuous_loop_disabled":result.get("continuous_loop_enabled") is False,
"windows_task_disabled":result.get("windows_task_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V104.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"engine_id":result.get("engine_id"),
"engine_action":result.get("engine_action"),
"selected_session":result.get("selected_session"),
"completed_phase_count":result.get("completed_phase_count"),
"failed_phases":result.get("failed_phases"),
"iteration_gates":result.get("iteration_gates"),
"checkpoint":result.get("checkpoint"),
"recovery":result.get("recovery"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
