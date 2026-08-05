from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = ROOT / "release/p2_actual_paper_broker_read/actual"

result = json.loads(
    (actual / "p2_actual_broker_read_result.json").read_text(
        encoding="utf-8-sig"
    )
)
certificate = json.loads(
    (actual / "p2_actual_broker_read_certificate.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "stage": (
        result.get("stage")
        == "P2_ACTUAL_PAPER_BROKER_READ_VALIDATION"
    ),
    "status": result.get("status") == "PASS",
    "validated": result.get("validated") is True,
    "certificate_pass": certificate.get("eligible") is True,
    "actual_network_used": (
        result.get("actual_external_network_used") is True
    ),
    "broker_read_performed": (
        result.get("actual_broker_read_performed") is True
    ),
    "four_read_requests": (
        result.get("actual_broker_read_request_count") == 4
    ),
    "broker_write_not_performed": (
        result.get("actual_broker_write_performed") is False
    ),
    "order_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "order_not_modified": (
        result.get("actual_order_modification_performed") is False
    ),
    "order_not_cancelled": (
        result.get("actual_order_cancellation_performed") is False
    ),
    "portfolio_not_modified": (
        result.get("actual_portfolio_modified") is False
    ),
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
    "live_endpoint_unused": result.get("live_endpoint_used") is False,
    "p3_order_still_blocked": (
        certificate.get("p3_actual_paper_order_allowed") is False
    ),
    "live_still_blocked": (
        certificate.get("live_order_submission_allowed") is False
    ),
}
verification = {
    "verification_stage": "P2_ACTUAL_PAPER_BROKER_READ",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
