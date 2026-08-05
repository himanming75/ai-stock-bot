from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = ROOT / "release/final_offline_release_candidate/actual"

result = json.loads(
    (actual / "final_offline_rc_audit_result.json").read_text(
        encoding="utf-8-sig"
    )
)
certificate = json.loads(
    (actual / "final_offline_rc_certificate.json").read_text(
        encoding="utf-8-sig"
    )
)
bundle = json.loads(
    (actual / "final_offline_rc_bundle.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "stage": (
        result.get("stage")
        == "FINAL_OFFLINE_RELEASE_CANDIDATE_AUDIT"
    ),
    "status": result.get("status") == "PASS",
    "rc_ready": result.get("offline_release_candidate_ready") is True,
    "certificate_eligible": certificate.get("eligible") is True,
    "required_stages_pass": (
        result.get("required_stage_audit", {})
        .get("all_required_stages_pass") is True
    ),
    "json_integrity_pass": (
        result.get("json_integrity_audit", {}).get("status") == "PASS"
    ),
    "safety_pass": (
        result.get("safety_invariant_audit", {}).get("status") == "PASS"
    ),
    "credential_scan_pass": (
        result.get("credential_leakage_audit", {}).get("status")
        == "PASS"
    ),
    "bundle_created": bundle.get("bundle_size_bytes", 0) > 0,
    "p3_not_completed": (
        result.get("p3_actual_paper_order_validation_completed")
        is False
    ),
    "production_still_blocked": (
        result.get("production_release_allowed") is False
    ),
    "live_still_blocked": (
        result.get("live_release_allowed") is False
    ),
    "network_unused": result.get("actual_external_network_used") is False,
    "broker_read_unused": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_performed") is False
    ),
    "orders_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "runtime_not_started": result.get("actual_runtime_started") is False,
    "service_not_installed": (
        result.get("actual_service_installed") is False
    ),
    "release_not_applied": (
        result.get("actual_release_applied") is False
    ),
}

verification = {
    "verification_stage": "FINAL_OFFLINE_RELEASE_CANDIDATE",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
