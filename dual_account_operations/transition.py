from __future__ import annotations
from .profiles import PolicyProfileCatalog


SAFE_DIRECT_TRANSITIONS = {
    ("ALL_STOP", "PAPER_TEST"),
    ("ALL_STOP", "ETRADE_READ_ONLY"),
    ("ALL_STOP", "DUAL_MONITOR"),
    ("ALL_STOP", "MAINTENANCE"),
    ("PAPER_TEST", "ALL_STOP"),
    ("ETRADE_READ_ONLY", "ALL_STOP"),
    ("DUAL_MONITOR", "ALL_STOP"),
    ("MAINTENANCE", "ALL_STOP"),
    ("PAPER_TEST", "DUAL_MONITOR"),
    ("ETRADE_READ_ONLY", "DUAL_MONITOR"),
    ("DUAL_MONITOR", "PAPER_TEST"),
    ("DUAL_MONITOR", "ETRADE_READ_ONLY"),
}


def validate_transition(
    current_profile: str,
    target_profile: str,
    *,
    operator_ack: bool,
    etrade_actual_connection_validated: bool,
) -> dict:
    catalog = PolicyProfileCatalog()
    current = catalog.get(current_profile)
    target = catalog.get(target_profile)

    if current.name == target.name:
        return {
            "status": "PASS",
            "allowed": True,
            "reason": "NO_CHANGE",
        }

    if (
        current.name,
        target.name,
    ) not in SAFE_DIRECT_TRANSITIONS:
        return {
            "status": "BLOCKED",
            "allowed": False,
            "reason": "UNSAFE_DIRECT_TRANSITION",
        }

    if target.operator_ack_required and not operator_ack:
        return {
            "status": "BLOCKED",
            "allowed": False,
            "reason": "OPERATOR_ACK_REQUIRED",
        }

    requires_etrade = any(
        item.account_key == "ETRADE_PRIMARY"
        and item.read_allowed
        for item in target.account_policies
    )
    if (
        requires_etrade
        and not etrade_actual_connection_validated
    ):
        return {
            "status": "BLOCKED",
            "allowed": False,
            "reason": (
                "ETRADE_ACTUAL_CONNECTION_NOT_VALIDATED"
            ),
        }

    return {
        "status": "PASS",
        "allowed": True,
        "reason": "TRANSITION_APPROVED",
    }
