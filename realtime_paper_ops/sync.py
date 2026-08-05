from __future__ import annotations
from decimal import Decimal
from typing import Any


class AccountPositionSyncPreview:
    def reconcile(
        self,
        *,
        local_account: dict[str, Any],
        broker_account_fixture: dict[str, Any],
        local_positions: list[dict[str, Any]],
        broker_positions_fixture: list[dict[str, Any]],
    ) -> dict[str, Any]:
        account_diffs = []
        for key in ("cash", "equity", "buying_power"):
            local = Decimal(str(local_account.get(key, "0")))
            broker = Decimal(str(broker_account_fixture.get(key, "0")))
            if local != broker:
                account_diffs.append({
                    "field": key,
                    "local": str(local),
                    "broker": str(broker),
                    "difference": str(broker - local),
                })

        local_map = {
            row["symbol"]: Decimal(str(row.get("qty", "0")))
            for row in local_positions
        }
        broker_map = {
            row["symbol"]: Decimal(str(row.get("qty", "0")))
            for row in broker_positions_fixture
        }
        position_diffs = []
        for symbol in sorted(set(local_map) | set(broker_map)):
            local = local_map.get(symbol, Decimal("0"))
            broker = broker_map.get(symbol, Decimal("0"))
            if local != broker:
                position_diffs.append({
                    "symbol": symbol,
                    "local_qty": str(local),
                    "broker_qty": str(broker),
                    "difference": str(broker - local),
                })

        return {
            "stage": "R18_ACCOUNT_POSITION_SYNC_PREVIEW",
            "account_differences": account_diffs,
            "position_differences": position_diffs,
            "account_in_sync": not account_diffs,
            "positions_in_sync": not position_diffs,
            "actual_broker_read_performed": False,
            "actual_local_state_modified": False,
            "automatic_reconciliation_enabled": False,
            "operator_review_required": bool(account_diffs or position_diffs),
        }
