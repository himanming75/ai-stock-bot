from __future__ import annotations
from typing import Any

def acceptance_test(
    readiness: dict[str, Any],
    integrity: dict[str, Any],
    certificate: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "readiness_passed": readiness.get("passed") is True,
        "integrity_passed": integrity.get("passed") is True,
        "certificate_valid": len(
            str(certificate.get("certificate_sha256", ""))
        ) == 64,
        "manifest_valid": len(
            str(manifest.get("manifest_sha256", ""))
        ) == 64,
        "release_ids_match": (
            certificate.get("release_id") == manifest.get("release_id")
        ),
        "paper_only": certificate.get("paper_trading_ready") is True,
        "live_disabled": certificate.get("live_trading_enabled") is False,
        "broker_write_disabled": (
            certificate.get("broker_write_enabled") is False
        ),
        "orders_disabled": (
            certificate.get("order_submission_enabled") is False
        ),
        "manual_approval_required": (
            certificate.get("manual_approval_required") is True
        ),
        "orders_zero": certificate.get("actual_orders_submitted") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
    }
