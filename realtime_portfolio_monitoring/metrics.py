from __future__ import annotations

from decimal import Decimal

from .models import (
    HUNDRED,
    ZERO,
    decimal_text,
    decimal_value,
    safe_ratio,
)


def build_position_metrics(
    positions: list[dict],
    equity: Decimal,
) -> tuple[list[dict], dict]:
    records = []
    gross_long = ZERO
    gross_short = ZERO
    total_market_value = ZERO
    total_cost_basis = ZERO
    total_unrealized_pl = ZERO
    total_today_pl = ZERO

    for position in positions:
        qty = decimal_value(position.get("qty"))
        market_value = decimal_value(
            position.get("market_value")
        )
        cost_basis = decimal_value(
            position.get("cost_basis")
        )
        unrealized_pl = decimal_value(
            position.get("unrealized_pl")
        )
        unrealized_plpc = decimal_value(
            position.get("unrealized_plpc")
        )
        unrealized_intraday_pl = decimal_value(
            position.get("unrealized_intraday_pl")
        )
        current_price = decimal_value(
            position.get("current_price")
        )
        avg_entry_price = decimal_value(
            position.get("avg_entry_price")
        )

        side = (
            "long"
            if qty > ZERO
            else "short"
            if qty < ZERO
            else "flat"
        )

        if market_value >= ZERO:
            gross_long += market_value
        else:
            gross_short += abs(market_value)

        total_market_value += market_value
        total_cost_basis += cost_basis
        total_unrealized_pl += unrealized_pl
        total_today_pl += unrealized_intraday_pl

        weight = (
            safe_ratio(abs(market_value), equity)
            * HUNDRED
        )

        records.append(
            {
                "symbol": str(
                    position.get("symbol", "")
                ),
                "side": side,
                "qty": decimal_text(qty),
                "market_value": decimal_text(
                    market_value
                ),
                "cost_basis": decimal_text(
                    cost_basis
                ),
                "avg_entry_price": decimal_text(
                    avg_entry_price
                ),
                "current_price": decimal_text(
                    current_price
                ),
                "unrealized_pl": decimal_text(
                    unrealized_pl
                ),
                "unrealized_pl_percent": decimal_text(
                    unrealized_plpc * HUNDRED
                ),
                "today_unrealized_pl": decimal_text(
                    unrealized_intraday_pl
                ),
                "portfolio_weight_percent": (
                    decimal_text(weight)
                ),
            }
        )

    gross_exposure = gross_long + gross_short
    net_exposure = gross_long - gross_short

    summary = {
        "position_count": len(records),
        "gross_long_exposure": decimal_text(
            gross_long
        ),
        "gross_short_exposure": decimal_text(
            gross_short
        ),
        "gross_exposure": decimal_text(
            gross_exposure
        ),
        "net_exposure": decimal_text(
            net_exposure
        ),
        "gross_exposure_percent": decimal_text(
            safe_ratio(gross_exposure, equity)
            * HUNDRED
        ),
        "net_exposure_percent": decimal_text(
            safe_ratio(net_exposure, equity)
            * HUNDRED
        ),
        "total_market_value": decimal_text(
            total_market_value
        ),
        "total_cost_basis": decimal_text(
            total_cost_basis
        ),
        "total_unrealized_pl": decimal_text(
            total_unrealized_pl
        ),
        "total_today_unrealized_pl": decimal_text(
            total_today_pl
        ),
    }
    return records, summary


def build_realized_metrics(
    orders: list[dict],
) -> dict:
    filled_orders = [
        order
        for order in orders
        if str(order.get("status", "")).lower()
        == "filled"
    ]
    buy_notional = ZERO
    sell_notional = ZERO
    buy_count = 0
    sell_count = 0

    for order in filled_orders:
        qty = decimal_value(
            order.get("filled_qty")
        )
        price = decimal_value(
            order.get("filled_avg_price")
        )
        notional = qty * price
        side = str(
            order.get("side", "")
        ).lower()

        if side == "buy":
            buy_count += 1
            buy_notional += notional
        elif side == "sell":
            sell_count += 1
            sell_notional += notional

    return {
        "filled_order_count": len(filled_orders),
        "filled_buy_count": buy_count,
        "filled_sell_count": sell_count,
        "filled_buy_notional": decimal_text(
            buy_notional
        ),
        "filled_sell_notional": decimal_text(
            sell_notional
        ),
        "net_filled_cash_flow": decimal_text(
            sell_notional - buy_notional
        ),
        "realized_pl_note": (
            "Broker activity-level realized PnL is not "
            "available from the order list alone. "
            "Net filled cash flow is recorded separately."
        ),
    }
