from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = ROOT / "release/r1_production_deployment_preparation/actual"
result = json.loads(
    (actual / "r1_readiness_result.json").read_text(
        encoding="utf-8-sig"
    )
)
certificate = json.loads(
    (actual / "production_release_certificate.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "stage": result.get("stage") == "R1",
    "status": result.get("status") == "PASS",
    "prepared_state": (
        result.get("state") ==
        "PRODUCTION_DEPLOYMENT_PREPARATION_READY"
    ),
    "manifest_present": (
        result.get("release_manifest", {}).get("file_count", 0) > 0
    ),
    "config_audit_valid": (
        result.get("configuration_audit", {}).get("valid") is True
    ),
    "retention_valid": (
        result.get("retention_policy", {}).get("valid") is True
    ),
    "automatic_restore_off": (
        result.get("restore_plan", {}).get(
            "automatic_restore_enabled"
        ) is False
    ),
    "start_on_boot_off": result.get("start_on_boot_enabled") is False,
    "auto_replay_off": (
        result.get("automatic_order_replay_enabled") is False
    ),
    "auto_restart_off": (
        result.get("automatic_broker_restart_enabled") is False
    ),
    "production_release_blocked": (
        result.get("production_release_allowed") is False
        and certificate.get("eligible") is False
    ),
    "live_network_off": result.get("live_network_enabled") is False,
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "R1_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
