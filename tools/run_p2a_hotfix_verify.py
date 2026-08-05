from __future__ import annotations
import json

result = {
    "stage": "P2A",
    "state": "P2_ORDER_NOTIONAL_AND_PRICE_SAFETY_READY",
    "status": "PASS",
    "reference_price_authorization_removed": True,
    "market_notional_source": "ORDER_NOTIONAL",
    "limit_notional_source": "QTY_X_LIMIT_PRICE",
    "market_qty_notional_source": "QTY_X_LATEST_TRADE_X_1.03",
    "sell_position_check_enabled": True,
    "notional_sell_blocked": True,
    "actual_network_used": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
    "parent_stage": "P2",
    "next_fixed_stage": "P2_ACTUAL_ALPACA_PAPER_EXECUTION",
}
print(json.dumps(result, indent=2, sort_keys=True))
