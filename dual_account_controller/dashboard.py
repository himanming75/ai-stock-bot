from __future__ import annotations


def build_controller_dashboard(
    *,
    controller_state: dict,
    profile_catalog: list[dict],
    etrade_key_issuance_pending: bool,
    etrade_actual_connection_validated: bool,
) -> dict:
    return {
        "active_profile": (
            controller_state[
                "active_profile"
            ]
        ),
        "profile_locked": (
            controller_state[
                "profile_locked"
            ]
        ),
        "global_kill_switch": (
            controller_state[
                "global_kill_switch"
            ]
        ),
        "account_kill_switches": (
            controller_state[
                "account_kill_switches"
            ]
        ),
        "sequence": (
            controller_state["sequence"]
        ),
        "available_profiles": [
            item["name"]
            for item in profile_catalog
        ],
        "etrade_key_issuance_pending": (
            etrade_key_issuance_pending
        ),
        "etrade_actual_connection_validated": (
            etrade_actual_connection_validated
        ),
        "broker_write_globally_enabled": False,
        "order_submission_enabled": False,
        "order_cancel_enabled": False,
    }
