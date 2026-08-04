from __future__ import annotations
from typing import Any

def build_paper_approval(
    preflight: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    approved = (
        preflight.get("passed") is True
        and policy.get("paper_auto_approval_enabled") is True
    )
    return {
        "paper_auto_approval_enabled": (
            policy.get("paper_auto_approval_enabled") is True
        ),
        "paper_simulation_authorized": approved,
        "live_execution_authorized": False,
        "broker_submission_authorized": False,
        "manual_live_approval_required": True,
    }
