from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .release_token import validate_release_token


def run_release_token_gate(
    release_result: dict[str, Any],
    release_token: dict[str, Any],
    secret: str,
    consumed_release_token_ids: set[str],
) -> dict[str, Any]:
    evaluation = validate_release_token(
        release_token=release_token,
        release_result=release_result,
        secret=secret,
        consumed_release_token_ids=consumed_release_token_ids,
    )

    return {
        "stage": "V392.07A",
        "state": (
            "RELEASE_TOKEN_GATE_OPEN"
            if evaluation["approved"]
            else "RELEASE_TOKEN_GATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "release_token_gate_allowed": evaluation["approved"],
        "local_dispatch_release_allowed": evaluation["approved"],
        "single_use_enforced": True,
        "replay_protection_enabled": True,
        "queue_mutation_enabled": False,
        "dispatch_execution_allowed": False,
        "automatic_release_enabled": False,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_08A_LOCAL_DISPATCH_RELEASE_GATE",
    }
