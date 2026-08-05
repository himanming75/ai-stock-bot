from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = (
    ROOT / "release/p1_actual_environment_qualification/actual"
)
result = json.loads(
    (actual / "p1_actual_environment_result.json").read_text(
        encoding="utf-8-sig"
    )
)
certificate = json.loads(
    (actual / "p1_actual_environment_certificate.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "stage": (
        result.get("stage") ==
        "P1_ACTUAL_ENVIRONMENT_QUALIFICATION"
    ),
    "status": result.get("status") == "PASS",
    "qualified": result.get("qualified") is True,
    "p1_validated": (
        result.get("p1_actual_environment_validated") is True
    ),
    "certificate_eligible": certificate.get("eligible") is True,
    "p2_read_allowed": (
        certificate.get("p2_actual_broker_read_allowed") is True
    ),
    "p3_order_still_blocked": (
        certificate.get("p3_actual_paper_order_allowed") is False
    ),
    "live_blocked": (
        certificate.get("live_order_submission_allowed") is False
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
    "verification_stage": "P1_ACTUAL_ENVIRONMENT",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
