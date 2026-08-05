from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .audit import RepositoryReleaseAuditor
from .credential_health import CredentialHealthMonitor
from .errors import ApiErrorClassifier
from .incident import IncidentReproductionBundle
from .preflight import ValidationPreflight
from .report import ValidationReportBuilder
from .retry import RateLimitDetector, RetryPolicy
from .schema import ResponseSchemaValidator


def run_validation_support(root: Path) -> dict[str, Any]:
    actual = root / "release/validation_support_mega_bundle/actual"
    actual.mkdir(parents=True, exist_ok=True)

    preflight = ValidationPreflight().evaluate(root)
    credentials = CredentialHealthMonitor().inspect(root)
    audit = RepositoryReleaseAuditor().audit(root)

    classifier = ApiErrorClassifier().classify(
        status_code=429,
        message="rate limit",
        headers={
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "fixture-reset",
        },
    )
    retry = RetryPolicy().plan(
        category=classifier["category"],
        attempt=1,
    )
    rate_limit = RateLimitDetector().detect(
        status_code=429,
        headers={
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "fixture-reset",
        },
    )
    account_schema = ResponseSchemaValidator().validate(
        schema_name="account",
        value={
            "id": "fixture-account",
            "status": "ACTIVE",
            "cash": "100000",
            "equity": "100000",
            "buying_power": "200000",
        },
    )

    sections = {
        "preflight": preflight,
        "credential_health": credentials,
        "repository_audit": {
            **audit,
            "failed": (
                []
                if audit["required_files_present"]
                else ["required_files_present"]
            ),
        },
        "schema_fixture": {
            **account_schema,
            "failed": (
                []
                if account_schema["valid"]
                else ["account_schema_valid"]
            ),
        },
    }
    report_builder = ValidationReportBuilder()
    report = report_builder.build(sections=sections)
    report_builder.write(
        actual / "validation_support_report.json",
        report,
    )

    incident = IncidentReproductionBundle().build(
        root=root,
        output=actual / "incident_reproduction_bundle",
        sources=[
            root / "release/p1_actual_environment_qualification/actual/"
                   "p1_actual_environment_result.json",
            root / "release/p1_actual_environment_qualification/actual/"
                   "p1_actual_environment_certificate.json",
            root / "release/r16_to_r20_realtime_paper_ops/actual/"
                   "r16_to_r20_result.json",
        ],
    )

    checks = {
        "preflight_ready": preflight["p2_preflight_ready"] is True,
        "credential_health_pass": credentials["status"] == "PASS",
        "required_release_files_present": (
            audit["required_files_present"] is True
        ),
        "error_classifier_ready": (
            classifier["category"] == "RATE_LIMIT"
        ),
        "retry_policy_safe": (
            retry["retry_allowed"] is True
            and retry["automatic_retry_enabled"] is False
        ),
        "rate_limit_detected": rate_limit["rate_limited"] is True,
        "schema_validator_pass": account_schema["valid"] is True,
        "report_created": report["overall_status"] == "PASS",
        "incident_bundle_created": incident["file_count"] >= 2,
        "credentials_excluded": incident["credentials_included"] is False,
    }

    result = {
        "stage": "VALIDATION_SUPPORT_AUTOMATION_MEGA_BUNDLE",
        "state": "VALIDATION_SUPPORT_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "preflight": preflight,
        "error_classifier_fixture": classifier,
        "retry_policy_fixture": retry,
        "rate_limit_fixture": rate_limit,
        "schema_fixture": account_schema,
        "credential_health": credentials,
        "repository_audit": audit,
        "validation_report": report,
        "incident_bundle": incident,
        "p2_p3_preflight": "READY",
        "api_error_classifier": "READY",
        "retry_backoff_policy": "READY_PREVIEW_ONLY",
        "rate_limit_detector": "READY",
        "response_schema_validator": "READY",
        "credential_health_monitor": "READY",
        "validation_report_generator": "READY",
        "failure_cause_summary": "READY",
        "git_release_audit": "READY",
        "incident_reproduction_bundle": "READY",
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "automatic_retry_enabled": False,
        "automatic_retry_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_action": "P2_ACTUAL_PAPER_BROKER_READ_VALIDATION",
    }
    (actual / "validation_support_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
