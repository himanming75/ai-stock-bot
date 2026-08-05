from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .token_gate import validate_token


def run_token_gate(
    authorization_result: dict[str, Any],
    proposal: dict[str, Any],
    token: dict[str, Any],
    secret: str,
    consumed_token_ids: set[str],
) -> dict[str, Any]:
    evaluation = validate_token(
        token=token,
        authorization_result=authorization_result,
        proposal=proposal,
        secret=secret,
        consumed_token_ids=consumed_token_ids,
    )

    return {
        "stage": "V392.02A",
        "state": (
            "AUTHORIZATION_TOKEN_GATE_OPEN"
            if evaluation["approved"]
            else "AUTHORIZATION_TOKEN_GATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "authorization_result": authorization_result,
        "proposal": proposal,
        "token_id": evaluation["token_id"],
        "evaluation": evaluation,
        "token_gate_allowed": evaluation["approved"],
        "dispatch_preparation_allowed": evaluation["approved"],
        "single_use_enforced": True,
        "replay_protection_enabled": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_03A_DISPATCH_PREPARATION_GATE",
    }
