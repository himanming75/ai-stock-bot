from __future__ import annotations


def build_rollback_plan(*, client_order_id: str, broker_order_id: str = "") -> dict:
    return {
        "client_order_id": client_order_id,
        "broker_order_id": broker_order_id,
        "automatic_rollback_enabled": False,
        "automatic_order_replay_enabled": False,
        "actions": [
            "ACTIVATE_LIVE_KILL_SWITCH",
            "FETCH_ORDER_STATE",
            "CANCEL_IF_CANCELABLE",
            "RECONCILE_POSITION_AND_CASH",
            "REQUIRE_OPERATOR_REVIEW",
        ],
    }
