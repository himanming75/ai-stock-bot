from __future__ import annotations


def build_portal_snapshot(
    *,
    run_id: str,
    generated_at: str,
    sources: list[dict],
    snapshots: dict[str, dict],
    issues: list[dict],
    errors: list[dict],
) -> dict:
    broker_cards = []
    total_accounts = 0
    total_positions = 0
    total_orders = 0

    source_map = {
        item["broker"]: item
        for item in sources
    }

    for broker, snapshot in sorted(
        snapshots.items()
    ):
        accounts = snapshot.get("accounts", [])
        positions = snapshot.get("positions", [])
        orders = snapshot.get("orders", [])
        source = source_map.get(broker, {})
        broker_cards.append({
            "broker": broker,
            "status": (
                "CONNECTED"
                if source.get("available")
                else "UNAVAILABLE"
            ),
            "freshness": source.get("freshness"),
            "account_count": len(accounts),
            "position_count": len(positions),
            "order_count": len(orders),
            "read_only": True,
            "write_enabled": False,
        })
        total_accounts += len(accounts)
        total_positions += len(positions)
        total_orders += len(orders)

    return {
        "run_id": run_id,
        "generated_at": generated_at,
        "mode": "READ_ONLY",
        "overall_status": (
            "HEALTHY"
            if not errors
            else "DEGRADED"
        ),
        "broker_cards": broker_cards,
        "totals": {
            "brokers": len(broker_cards),
            "accounts": total_accounts,
            "positions": total_positions,
            "orders": total_orders,
            "reconciliation_issues": len(issues),
            "errors": len(errors),
        },
        "issues": issues,
        "errors": errors,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "order_cancel_enabled": False,
    }
