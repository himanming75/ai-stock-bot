import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v104_33_to_v104_64/actual/"
    "continuous_service_runtime_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V104.33-V104.64",
    "status": result.get("status") == "PASS",
    "state": result.get("state") == "CONTINUOUS_SERVICE_RUNTIME_READY",
    "hash_valid": len(
        result.get("continuous_runtime_certificate_sha256", "")
    ) == 64,
    "ticks_valid": result.get("tick_count", 0) >= 1,
    "heartbeats_valid": result.get("heartbeat_count", 0)
        == result.get("tick_count", -1),
    "checkpoint_valid": isinstance(result.get("checkpoint", {}), dict),
    "recovery_valid": isinstance(result.get("recovery", {}), dict),
    "shutdown_valid": isinstance(result.get("shutdown", {}), dict),
    "runtime_started": result.get("runtime_started") is True,
    "runtime_stopped_cleanly": result.get("runtime_stopped_cleanly") is True,
    "background_service_not_running": (
        result.get("background_service_running") is False
    ),
    "approval_not_granted": result.get("approval_granted") is False,
    "execution_not_authorized": result.get("execution_authorized") is False,
    "manual_approval_required": result.get("manual_approval_required") is True,
    "credentials_unused": result.get("actual_credentials_used") is False,
    "network_unused": result.get("actual_external_network_used") is False,
    "orders_zero": result.get("actual_orders_submitted") == 0,
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "orders_disabled": result.get("order_submission_enabled") is False,
    "live_disabled": result.get("live_trading_enabled") is False,
    "network_disabled": result.get("external_network_enabled") is False,
    "unbounded_loop_disabled": result.get("unbounded_loop_enabled") is False,
    "windows_task_disabled": result.get("windows_task_enabled") is False,
}
failed = [name for name, passed in checks.items() if not passed]

print(json.dumps({
    "verification_stage": "V104.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "runtime_id": result.get("runtime_id"),
    "source_engine_state": result.get("source_engine_state"),
    "tick_count": result.get("tick_count"),
    "heartbeat_count": result.get("heartbeat_count"),
    "checkpoint": result.get("checkpoint"),
    "recovery": result.get("recovery"),
    "shutdown": result.get("shutdown"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))

raise SystemExit(0 if not failed else 1)
