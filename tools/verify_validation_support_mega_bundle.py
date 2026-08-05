from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/validation_support_mega_bundle/actual/"
               "validation_support_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage") ==
        "VALIDATION_SUPPORT_AUTOMATION_MEGA_BUNDLE"
    ),
    "status": result.get("status") == "PASS",
    "qualified_state": (
        result.get("state") ==
        "VALIDATION_SUPPORT_OFFLINE_QUALIFIED"
    ),
    "preflight_ready": result.get("p2_p3_preflight") == "READY",
    "classifier_ready": (
        result.get("api_error_classifier") == "READY"
    ),
    "retry_preview_ready": (
        result.get("retry_backoff_policy")
        == "READY_PREVIEW_ONLY"
    ),
    "rate_limit_ready": (
        result.get("rate_limit_detector") == "READY"
    ),
    "schema_ready": (
        result.get("response_schema_validator") == "READY"
    ),
    "credential_health_ready": (
        result.get("credential_health_monitor") == "READY"
    ),
    "report_ready": (
        result.get("validation_report_generator") == "READY"
    ),
    "incident_ready": (
        result.get("incident_reproduction_bundle") == "READY"
    ),
    "network_unused": (
        result.get("actual_external_network_used") is False
    ),
    "broker_read_not_performed": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_write_not_performed": (
        result.get("actual_broker_write_performed") is False
    ),
    "automatic_retry_off": (
        result.get("automatic_retry_enabled") is False
    ),
    "automatic_retry_not_performed": (
        result.get("automatic_retry_performed") is False
    ),
    "orders_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "VALIDATION_SUPPORT_MEGA_BUNDLE",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
