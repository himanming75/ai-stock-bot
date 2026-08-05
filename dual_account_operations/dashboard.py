from __future__ import annotations


def build_dashboard(
    *,
    active_profile: str,
    accounts: list[dict],
    policy_profile: dict,
    global_kill_switch: bool,
) -> dict:
    rows = []
    account_policy = {
        item["account_key"]: item
        for item in policy_profile["account_policies"]
    }

    for account in accounts:
        key = account["account_key"]
        policy = account_policy.get(
            key,
            {
                "read_allowed": False,
                "write_allowed": False,
                "strategy_execution_allowed": False,
                "kill_switch_required": True,
            },
        )

        connection_ready = bool(
            account.get(
                "actual_connection_validated",
                False,
            )
        )
        key_pending = bool(
            account.get(
                "key_issuance_pending",
                False,
            )
        )
        health = str(
            account.get(
                "health_status",
                "UNKNOWN",
            )
        ).upper()

        effective_read = (
            policy["read_allowed"]
            and not global_kill_switch
            and (
                account["environment"] != "PRODUCTION"
                or connection_ready
            )
        )
        effective_write = (
            policy["write_allowed"]
            and not global_kill_switch
            and account["environment"] == "PAPER"
        )

        rows.append({
            "account_key": key,
            "alias": account["alias"],
            "broker": account["broker"],
            "environment": account["environment"],
            "role": account["role"],
            "health_status": health,
            "actual_connection_validated": connection_ready,
            "key_issuance_pending": key_pending,
            "configured_read_allowed": (
                policy["read_allowed"]
            ),
            "configured_write_allowed": (
                policy["write_allowed"]
            ),
            "effective_read_allowed": effective_read,
            "effective_write_allowed": effective_write,
            "strategy_execution_allowed": (
                policy[
                    "strategy_execution_allowed"
                ]
            ),
            "kill_switch_required": (
                policy["kill_switch_required"]
            ),
            "equity": str(
                account.get("equity", "0")
            ),
            "cash": str(
                account.get("cash", "0")
            ),
            "unrealized_pl": str(
                account.get("unrealized_pl", "0")
            ),
        })

    return {
        "active_profile": active_profile,
        "global_kill_switch": global_kill_switch,
        "account_count": len(rows),
        "accounts": rows,
        "paper_account_count": sum(
            1
            for item in rows
            if item["environment"] == "PAPER"
        ),
        "actual_account_count": sum(
            1
            for item in rows
            if item["environment"] == "PRODUCTION"
        ),
        "effective_read_account_count": sum(
            1
            for item in rows
            if item["effective_read_allowed"]
        ),
        "effective_write_account_count": sum(
            1
            for item in rows
            if item["effective_write_allowed"]
        ),
        "broker_write_globally_enabled": False,
    }
