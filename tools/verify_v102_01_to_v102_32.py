import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v102_01_to_v102_32/actual/"
    "master_ai_orchestrator_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V102.01-V102.32",
    "status": result.get("status") == "PASS",
    "allowed_state": result.get("state") in {
        "MASTER_AI_ORCHESTRATOR_READY",
        "MASTER_AI_ORCHESTRATOR_REVIEW_REQUIRED",
    },
    "hash_valid": len(
        result.get("master_orchestrator_certificate_sha256", "")
    ) == 64,
    "registry_valid": isinstance(result.get("module_registry", []), list),
    "dependencies_valid": isinstance(result.get("dependency_graph", {}), dict),
    "workflow_valid": isinstance(result.get("workflow", {}), dict),
    "health_valid": isinstance(result.get("health", {}), dict),
    "safety_valid": isinstance(result.get("safety_lock", {}), dict),
    "recovery_valid": isinstance(result.get("recovery_plan", {}), dict),
    "checkpoint_valid": isinstance(result.get("checkpoint", {}), dict),
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
}
failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({
    "verification_stage": "V102.32",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "orchestration_id": result.get("orchestration_id"),
    "module_registry": result.get("module_registry"),
    "dependency_graph": result.get("dependency_graph"),
    "workflow": result.get("workflow"),
    "health": result.get("health"),
    "safety_lock": result.get("safety_lock"),
    "recovery_plan": result.get("recovery_plan"),
    "checkpoint": result.get("checkpoint"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
