from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from final_release.io import digest

def build_rollback_manifest(
    certificate: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "manifest_type": "ROLLBACK_MANIFEST",
        "release_id": certificate.get("release_id"),
        "release_version": certificate.get("release_version"),
        "rollback_target_commit": policy.get("base_commit"),
        "branch": policy.get("branch", "main"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "restore_strategy": "GIT_RESET_TO_BASE_COMMIT_AND_REVERIFY",
        "preserve_actual_ledgers": True,
        "preserve_user_configuration": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
    }
    body["rollback_manifest_sha256"] = digest(body)
    return body
