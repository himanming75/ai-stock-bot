import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v105_33_to_v105_64/actual/"
    "production_readiness_final_release_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V105.33-V105.64",
    "status": result.get("status") == "PASS",
    "allowed_state": result.get("state") in {
        "PRODUCTION_READINESS_FINAL_RELEASE_COMPLETE",
        "PRODUCTION_READINESS_FINAL_RELEASE_REVIEW_REQUIRED",
    },
    "hash_valid": len(
        result.get("final_release_result_sha256", "")
    ) == 64,
    "release_id_valid": len(str(result.get("release_id", ""))) == 24,
    "readiness_valid": isinstance(result.get("readiness", {}), dict),
    "certificate_valid": isinstance(result.get("certificate", {}), dict),
    "manifest_valid": isinstance(result.get("manifest", {}), dict),
    "integrity_valid": isinstance(result.get("integrity", {}), dict),
    "acceptance_valid": isinstance(result.get("acceptance", {}), dict),
    "bundle_valid": isinstance(result.get("bundle", {}), dict),
    "rollback_valid": isinstance(result.get("rollback", {}), dict),
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
    "background_service_not_running": (
        result.get("background_service_running") is False
    ),
    "windows_task_disabled": result.get("windows_task_enabled") is False,
}
failed = [name for name, passed in checks.items() if not passed]

print(json.dumps({
    "verification_stage": "V105.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "release_id": result.get("release_id"),
    "release_version": result.get("release_version"),
    "project_complete": result.get("project_complete"),
    "production_release_created": result.get("production_release_created"),
    "paper_trading_ready": result.get("paper_trading_ready"),
    "live_trading_ready": result.get("live_trading_ready"),
    "readiness": result.get("readiness"),
    "integrity": result.get("integrity"),
    "acceptance": result.get("acceptance"),
    "bundle": result.get("bundle"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))

raise SystemExit(0 if not failed else 1)
