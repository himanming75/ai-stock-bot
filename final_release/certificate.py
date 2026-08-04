from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from final_release.io import digest

def build_certificate(
    integration: dict[str, Any],
    readiness: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    observed_at = datetime.now(timezone.utc).isoformat()
    release_id = digest({
        "version": policy.get("release_version"),
        "integration_id": integration.get("integration_id"),
        "base_commit": policy.get("base_commit"),
        "readiness": readiness,
    })[:24]
    body = {
        "certificate_type": "FINAL_COMPLETION_CERTIFICATE",
        "release_id": release_id,
        "release_version": policy.get("release_version"),
        "release_name": policy.get("release_name"),
        "base_commit": policy.get("base_commit"),
        "integration_id": integration.get("integration_id"),
        "issued_at": observed_at,
        "project_status": (
            "COMPLETE" if readiness.get("passed") else "REVIEW_REQUIRED"
        ),
        "paper_trading_ready": readiness.get("passed") is True,
        "live_trading_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "external_network_enabled": False,
        "manual_approval_required": True,
        "execution_authorized": False,
        "actual_orders_submitted": 0,
        "readiness": readiness,
    }
    body["certificate_sha256"] = digest(body)
    return body
