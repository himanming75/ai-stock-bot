from __future__ import annotations
from collections import defaultdict
from typing import Any

from .models import ReconciliationIssue


OPEN_STATUSES = {
    "OPEN",
    "NEW",
    "ACCEPTED",
    "PENDING_NEW",
    "PENDING",
    "QUEUED",
    "WORKING",
    "PARTIALLY_FILLED",
    "PARTIAL_FILL",
}


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dict_items(value: Any) -> list[dict]:
    if isinstance(value, dict):
        record_keys = {
            "status",
            "order_status",
            "orderStatus",
            "order_id",
            "orderId",
            "symbol",
            "quantity",
            "account_id",
            "broker",
        }
        if any(key in value for key in record_keys):
            return [value]

        result = []
        for item in value.values():
            result.extend(_dict_items(item))
        return result

    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            result.extend(_dict_items(item))
        return result

    return []


def _symbol_map(snapshot: dict) -> dict[str, list[dict]]:
    result = defaultdict(list)
    for item in _dict_items(
        snapshot.get("positions", [])
    ):
        symbol = str(
            item.get("symbol") or ""
        ).upper()
        if symbol:
            result[symbol].append(item)
    return result


def reconcile_positions(
    left: dict,
    right: dict,
    *,
    left_name: str,
    right_name: str,
    quantity_tolerance: float = 0.0001,
    price_tolerance: float = 0.01,
) -> list[dict]:
    issues = []
    left_map = _symbol_map(left)
    right_map = _symbol_map(right)
    symbols = sorted(
        set(left_map) | set(right_map)
    )

    for symbol in symbols:
        left_items = left_map.get(symbol, [])
        right_items = right_map.get(symbol, [])
        left_qty = sum(
            _float(item.get("quantity")) or 0
            for item in left_items
        )
        right_qty = sum(
            _float(item.get("quantity")) or 0
            for item in right_items
        )

        if not left_items or not right_items:
            issues.append(
                ReconciliationIssue(
                    issue_type=(
                        "POSITION_PRESENCE_MISMATCH"
                    ),
                    severity="WARNING",
                    symbol=symbol,
                    account_id=None,
                    broker_left=left_name,
                    broker_right=right_name,
                    left_value=left_qty,
                    right_value=right_qty,
                    difference=left_qty - right_qty,
                    message=(
                        f"{symbol} exists on only one broker."
                    ),
                ).to_dict()
            )
            continue

        quantity_difference = (
            left_qty - right_qty
        )
        if (
            abs(quantity_difference)
            > quantity_tolerance
        ):
            issues.append(
                ReconciliationIssue(
                    issue_type=(
                        "POSITION_QUANTITY_MISMATCH"
                    ),
                    severity="WARNING",
                    symbol=symbol,
                    account_id=None,
                    broker_left=left_name,
                    broker_right=right_name,
                    left_value=left_qty,
                    right_value=right_qty,
                    difference=quantity_difference,
                    message=(
                        f"{symbol} quantity differs."
                    ),
                ).to_dict()
            )

        left_prices = [
            _float(item.get("average_price"))
            for item in left_items
            if _float(
                item.get("average_price")
            ) is not None
        ]
        right_prices = [
            _float(item.get("average_price"))
            for item in right_items
            if _float(
                item.get("average_price")
            ) is not None
        ]
        if left_prices and right_prices:
            left_price = (
                sum(left_prices) / len(left_prices)
            )
            right_price = (
                sum(right_prices) / len(right_prices)
            )
            price_difference = (
                left_price - right_price
            )
            if (
                abs(price_difference)
                > price_tolerance
            ):
                issues.append(
                    ReconciliationIssue(
                        issue_type=(
                            "AVERAGE_PRICE_MISMATCH"
                        ),
                        severity="INFO",
                        symbol=symbol,
                        account_id=None,
                        broker_left=left_name,
                        broker_right=right_name,
                        left_value=left_price,
                        right_value=right_price,
                        difference=price_difference,
                        message=(
                            f"{symbol} average price differs."
                        ),
                    ).to_dict()
                )

    return issues


def reconcile_accounts(
    left: dict,
    right: dict,
    *,
    left_name: str,
    right_name: str,
) -> list[dict]:
    issues = []
    fields = (
        "cash",
        "buying_power",
        "equity",
        "market_value",
    )
    left_accounts = _dict_items(
        left.get("accounts", [])
    )
    right_accounts = _dict_items(
        right.get("accounts", [])
    )

    if not left_accounts or not right_accounts:
        issues.append(
            ReconciliationIssue(
                issue_type="ACCOUNT_SOURCE_MISSING",
                severity="ERROR",
                symbol=None,
                account_id=None,
                broker_left=left_name,
                broker_right=right_name,
                left_value=len(left_accounts),
                right_value=len(right_accounts),
                difference=None,
                message=(
                    "One broker has no normalized account."
                ),
            ).to_dict()
        )
        return issues

    left_account = left_accounts[0]
    right_account = right_accounts[0]
    for field in fields:
        left_value = _float(
            left_account.get(field)
        )
        right_value = _float(
            right_account.get(field)
        )
        if (
            left_value is None
            or right_value is None
        ):
            continue
        difference = (
            left_value - right_value
        )
        if abs(difference) > 0.01:
            issues.append(
                ReconciliationIssue(
                    issue_type=(
                        f"ACCOUNT_{field.upper()}_DIFFERENCE"
                    ),
                    severity="INFO",
                    symbol=None,
                    account_id=None,
                    broker_left=left_name,
                    broker_right=right_name,
                    left_value=left_value,
                    right_value=right_value,
                    difference=difference,
                    message=(
                        f"Account {field} differs."
                    ),
                ).to_dict()
            )
    return issues


def _order_status(item: dict) -> str:
    return str(
        item.get("status")
        or item.get("order_status")
        or item.get("orderStatus")
        or ""
    ).upper()


def _open_orders(snapshot: dict) -> list[dict]:
    result = []
    for item in _dict_items(
        snapshot.get("orders", [])
    ):
        if _order_status(item) in OPEN_STATUSES:
            result.append(item)
    return result


def reconcile_orders(
    left: dict,
    right: dict,
    *,
    left_name: str,
    right_name: str,
) -> list[dict]:
    """
    Compare only valid order dictionaries.

    Actual validation output can contain strings or nested dictionary maps.
    Primitive values are ignored instead of calling .get() on them.
    """
    issues = []
    left_open = _open_orders(left)
    right_open = _open_orders(right)

    if len(left_open) != len(right_open):
        issues.append(
            ReconciliationIssue(
                issue_type=(
                    "OPEN_ORDER_COUNT_MISMATCH"
                ),
                severity="INFO",
                symbol=None,
                account_id=None,
                broker_left=left_name,
                broker_right=right_name,
                left_value=len(left_open),
                right_value=len(right_open),
                difference=float(
                    len(left_open)
                    - len(right_open)
                ),
                message=(
                    "Open order counts differ."
                ),
                metadata={
                    "left_valid_order_records": len(
                        _dict_items(
                            left.get("orders", [])
                        )
                    ),
                    "right_valid_order_records": len(
                        _dict_items(
                            right.get("orders", [])
                        )
                    ),
                },
            ).to_dict()
        )

    return issues
