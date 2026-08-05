from __future__ import annotations


def build_manual_repair_plan(drift_types: list[str]) -> dict:
    actions = [
        "ACTIVATE_LIVE_KILL_SWITCH",
        "BLOCK_NEW_LIVE_ORDERS",
        "REFETCH_ACCOUNT_ORDERS_POSITIONS",
        "VERIFY_FILL_LEDGER_AND_IDEMPOTENCY",
    ]
    if "order" in drift_types:
        actions.append("REVIEW_ORDER_STATE_AND_CANCEL_IF_SAFE")
    if "position" in drift_types:
        actions.append("RECONCILE_POSITION_QUANTITY")
    if "cash" in drift_types:
        actions.append("RECONCILE_CASH_AND_BUYING_POWER")
    actions.append("REQUIRE_OPERATOR_APPROVAL_BEFORE_RESUME")

    return {
        "drift_types": drift_types,
        "actions": actions,
        "automatic_repair_enabled": False,
        "automatic_order_replay_enabled": False,
        "automatic_position_mutation_enabled": False,
    }
