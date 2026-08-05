from __future__ import annotations
from collections import defaultdict
from decimal import Decimal

from .models import UnifiedOrder, UnifiedPosition
from .status import canonical_order_status, is_open_order


def D(value) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def aggregate_positions(
    records: list[dict],
) -> list[UnifiedPosition]:
    grouped: dict[str, list[dict]] = defaultdict(list)

    for record in records:
        symbol = str(record.get("symbol") or "").upper()
        if symbol:
            grouped[symbol].append(record)

    result = []
    for symbol in sorted(grouped):
        items = grouped[symbol]
        total_quantity = sum(
            (D(item.get("quantity")) for item in items),
            Decimal("0"),
        )
        total_market_value = sum(
            (D(item.get("market_value")) for item in items),
            Decimal("0"),
        )
        total_unrealized_pl = sum(
            (D(item.get("unrealized_pl")) for item in items),
            Decimal("0"),
        )
        total_cost = sum(
            (
                D(item.get("quantity"))
                * D(item.get("average_price"))
                for item in items
            ),
            Decimal("0"),
        )
        weighted_average_price = (
            total_cost / total_quantity
            if total_quantity != 0
            else Decimal("0")
        )

        breakdown = tuple(
            {
                "broker": item.get("broker"),
                "account_id": item.get("account_id"),
                "quantity": str(D(item.get("quantity"))),
                "average_price": str(
                    D(item.get("average_price"))
                ),
                "market_value": str(
                    D(item.get("market_value"))
                ),
                "unrealized_pl": str(
                    D(item.get("unrealized_pl"))
                ),
            }
            for item in items
        )

        result.append(
            UnifiedPosition(
                symbol=symbol,
                total_quantity=total_quantity,
                weighted_average_price=(
                    weighted_average_price
                ),
                total_market_value=total_market_value,
                total_unrealized_pl=total_unrealized_pl,
                account_count=len(
                    {
                        str(item.get("account_id"))
                        for item in items
                    }
                ),
                account_breakdown=breakdown,
            )
        )
    return result


def normalize_orders(
    records: list[dict],
) -> list[UnifiedOrder]:
    result = []
    for item in records:
        status = str(item.get("status") or "UNKNOWN")
        result.append(
            UnifiedOrder(
                broker=str(
                    item.get("broker") or "ETRADE"
                ).upper(),
                account_id=str(
                    item.get("account_id") or ""
                ),
                order_id=str(
                    item.get("order_id") or ""
                ),
                symbol=str(
                    item.get("symbol") or ""
                ).upper(),
                side=str(
                    item.get("side") or "UNKNOWN"
                ).upper(),
                quantity=D(item.get("quantity")),
                filled_quantity=D(
                    item.get("filled_quantity")
                ),
                status=status.upper(),
                canonical_status=(
                    canonical_order_status(status)
                ),
                open_order=is_open_order(status),
            )
        )
    result.sort(
        key=lambda order: (
            order.open_order is False,
            order.symbol,
            order.account_id,
            order.order_id,
        )
    )
    return result


def order_statistics(
    orders: list[UnifiedOrder],
) -> dict:
    by_status: dict[str, int] = defaultdict(int)
    by_account: dict[str, int] = defaultdict(int)
    by_symbol: dict[str, int] = defaultdict(int)

    for order in orders:
        by_status[order.canonical_status] += 1
        by_account[order.account_id] += 1
        by_symbol[order.symbol] += 1

    return {
        "order_count": len(orders),
        "open_order_count": sum(
            1 for item in orders if item.open_order
        ),
        "filled_order_count": by_status["FILLED"],
        "cancelled_order_count": by_status["CANCELLED"],
        "rejected_order_count": by_status["REJECTED"],
        "unknown_order_count": by_status["UNKNOWN"],
        "by_status": dict(sorted(by_status.items())),
        "by_account": dict(sorted(by_account.items())),
        "by_symbol": dict(sorted(by_symbol.items())),
    }
